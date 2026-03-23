import asyncio
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LLMConfig, DefaultMarkdownGenerator, BrowserConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter
from crawl4ai.content_filter_strategy import LLMContentFilter, PruningContentFilter, RelevantContentFilter
from langchain_core.documents import Document
from backend.param.crawl import CrawlRequest
from backend.rag.storage.milvus_storage import MilvusStorage
from backend.rag.storage.lightrag_storage import LightRAGStorage
from backend.config.embedding import get_embedding_model
from backend.rag.chunks.chunks import ChunkResult, TextChunker
from backend.rag.chunks.models import ChunkConfig, ChunkStrategy, DocumentContent
from backend.config.log import get_logger
from backend.config.redis import get_redis_client
import subprocess
import sys


# 获取logger实例
logger = get_logger("crawl_service")

# 定义爬虫状态常量
CRAWL_STATUS_PROCESSING = "processing"
CRAWL_STATUS_COMPLETED = "completed"
CRAWL_STATUS_ERROR = "error"

async def initialize_collection_and_store(request: CrawlRequest):
    milvus_storage = MilvusStorage(
        embedding_function=get_embedding_model(),
        collection_name=request.collection_id,
    )

    lightrag_storage = LightRAGStorage(workspace=request.collection_id)
    
    
    # 初始化爬虫状态
    await init_crawl_status(request.collection_id)
    
    # 为对应的知识库添加文档记录
    from backend.service.knowledge_library import add_document
    from backend.param.knowledge_library import AddDocumentRequest
    from backend.config.database import DatabaseFactory
    from backend.model.knowledge_library import KnowledgeLibrary
    
    try:
        # 根据collection_id查找知识库
        db = DatabaseFactory.create_session()
        library = db.query(KnowledgeLibrary).filter(
            KnowledgeLibrary.collection_id == request.collection_id,
            KnowledgeLibrary.is_active == True
        ).first()
        
        if library:
            # 创建文档记录
            doc_request = AddDocumentRequest(
                library_id=library.id,
                name=request.title or "爬虫文档",
                type="link",  # 爬虫类型为链接
                url=request.url
            )
            
            # 添加文档到知识库
            await add_document(doc_request, library.user_id)
            logger.info(f"成功为知识库 {library.title} 添加文档记录: {request.title or '爬虫文档'}")
        else:
            logger.warning(f"未找到collection_id为 {request.collection_id} 的知识库")
            
    except Exception as e:
        logger.error(f"添加文档记录失败: {str(e)}")
    finally:
        if db:
            db.close()
    
    try:
        await crawl_doc(request.url, request.prefix, request.if_llm, request.model_id, request.provider, request.base_url, request.api_key, milvus_storage, lightrag_storage, request.collection_id)
        # await test_crawl_doc(request.url, request.prefix, request.if_llm, request.model_id, request.provider, request.base_url, request.api_key)
        # 爬虫完成，更新状态为已完成
        await update_crawl_status(request.collection_id, CRAWL_STATUS_COMPLETED)
    except Exception as e:
        # 爬虫异常，更新状态为错误
        await update_crawl_status(request.collection_id, CRAWL_STATUS_ERROR, str(e))
        raise


async def init_crawl_status(collection_id: str):
    """初始化爬虫状态"""
    redis_client = await get_redis_client()
    status_data = {
        "status": CRAWL_STATUS_PROCESSING,
        "count": 0,
        "message": "爬虫任务开始",
        "start_time": datetime.now().isoformat(),
        "last_update": datetime.now().isoformat()
    }
    await redis_client.set(f"crawl_status:{collection_id}", json.dumps(status_data))
    logger.info(f"初始化爬虫状态: {collection_id}")


async def update_crawl_status(collection_id: str, status: str, message: str = None, count: int = None):
    """更新爬虫状态"""
    redis_client = await get_redis_client()
    
    # 获取当前状态
    current_status = await redis_client.get(f"crawl_status:{collection_id}")
    if current_status:
        status_data = json.loads(current_status)
    else:
        status_data = {
            "status": status,
            "count": 0,
            "message": message or "",
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat()
        }
    
    # 更新状态数据
    status_data["status"] = status
    status_data["last_update"] = datetime.now().isoformat()
    
    if message:
        status_data["message"] = message
    
    if count is not None:
        status_data["count"] = count
    
    await redis_client.set(f"crawl_status:{collection_id}", json.dumps(status_data))
    logger.info(f"更新爬虫状态: {collection_id} - {status}")


async def increment_crawl_count(collection_id: str):
    """增加爬虫计数"""
    redis_client = await get_redis_client()
    
    current_status = await redis_client.get(f"crawl_status:{collection_id}")
    if current_status:
        status_data = json.loads(current_status)
        status_data["count"] = status_data.get("count", 0) + 1
        status_data["last_update"] = datetime.now().isoformat()
        await redis_client.set(f"crawl_status:{collection_id}", json.dumps(status_data))


async def get_crawl_status(collection_id: str) -> dict:
    """
    获取爬虫状态
    
    Args:
        collection_id: 集合ID
        
    Returns:
        dict: 爬虫状态信息，包含status, count, message, start_time, last_update字段
              如果不存在该集合的状态，返回空字典
    """
    redis_client = await get_redis_client()
    
    status_data = await redis_client.get(f"crawl_status:{collection_id}")
    if status_data:
        return json.loads(status_data)
    else:
        return {}


async def get_all_crawl_status() -> dict:
    """
    获取所有爬虫状态
    
    Returns:
        dict: 所有爬虫状态，key为集合ID，value为状态信息
    """
    redis_client = await get_redis_client()
    
    # 获取所有以crawl_status:开头的key
    keys = await redis_client.keys("crawl_status:*")
    
    status_dict = {}
    for key in keys:
        # 提取集合ID
        collection_id = key.replace("crawl_status:", "")
        status_data = await redis_client.get(key)
        if status_data:
            status_dict[collection_id] = json.loads(status_data)
    
    return status_dict

async def test_crawl_doc(site: str, prefix: str, if_llm: bool, model_id: str, provider: str, base_url: str, api_token: str):
    content_filter: RelevantContentFilter
    if if_llm:
        content_filter = LLMContentFilter(
                llm_config = LLMConfig(provider=f"{provider}/{model_id}",api_token=api_token,base_url=base_url), #or use environment variable
                instruction="""
                Focus on extracting the core educational content.
                Include:
                - Key concepts and explanations
                - Important code examples
                - Essential technical details
                Exclude:
                - Navigation elements
                - Sidebars
                - Footer content
                Format the output as clean markdown with proper code blocks and headers.
                """,
                chunk_token_threshold=4096,  # Adjust based on your needs
                verbose=True # 生产时关掉
        )
    else:
        content_filter = PruningContentFilter(
                    threshold=0.4,
                    threshold_type="fixed"
                )
    md_generator = DefaultMarkdownGenerator(
        content_filter=content_filter,
        options={"ignore_links": True,"ignore_images": True}
    )

    browser_conf = BrowserConfig(
        browser_type="chromium",
        headless=True,
        text_mode=True
    )

    prefix_filter = URLPatternFilter(
    patterns=[f"{prefix}*"]
    )
    filter_chain = FilterChain([prefix_filter])

    # Basic configuration
    bfsstrategy = BFSDeepCrawlStrategy(
        max_depth=4,               # Crawl initial page + 2 levels deep
        include_external=False,    # Stay within the same domain
        max_pages=200,              # Maximum number of pages to crawl (optional)
        # filter_chain=filter_chain
    )

        # Basic configuration
    dfsstrategy = DFSDeepCrawlStrategy(
        max_depth=8,               # Crawl initial page + 2 levels deep
        include_external=False,    # Stay within the same domain
        max_pages=200,              # Maximum number of pages to crawl (optional)
        #score_threshold=0.5,       # Minimum score for URLs to be crawled (optional)
    )

    # Configure a 2-level deep crawl
    config = CrawlerRunConfig(
        deep_crawl_strategy=bfsstrategy,
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True, #上线时关闭
        stream=True,
        markdown_generator=md_generator,
    )

    async with AsyncWebCrawler(config=browser_conf) as crawler:
            async for result in await crawler.arun(site, config=config):
                print(f"URL: {result.url}")
                # print(result.markdown.fit_markdown) 
                # handle_md(result.markdown.fit_markdown, type="print", path=f"{result}.md")
    print("测试完成")


async def crawl_doc(site: str, prefix: str, if_llm: bool, model_id: str, provider: str, base_url: str, api_token: str, milvus_storage: MilvusStorage, lightrag_storage: LightRAGStorage, collection_id: str):
    """
    爬取文档并处理。使用线程包装器解决 Windows uvicorn --reload 兼容性问题。
    """
    # 先在独立线程中运行爬虫，收集所有结果
    logger.info(f"开始爬取: {site}")
    
    crawl_results = await asyncio.get_event_loop().run_in_executor(
        None,
        _crawl_in_thread,
        site, prefix, if_llm, model_id, provider, base_url, api_token
    )
    
    logger.info(f"爬取完成，共获取 {len(crawl_results)} 个结果")
    
    # 在主事件循环中处理结果
    for result_data in crawl_results:
        try:
            url = result_data.get("url", "unknown")
            markdown_content = result_data.get("markdown")
            
            if not markdown_content:
                logger.warning(f"URL {url} 的markdown内容为空，跳过处理")
                continue
            
            await handle_md(md_content=markdown_content, type="light_and_milvus", param=[milvus_storage, lightrag_storage], collection_id=collection_id, document_name=url)
            logger.info(f"成功处理: {url}")
            
        except Exception as e:
            error_msg = f"处理URL时发生错误: {str(e)}"
            logger.error(error_msg)
            logger.info("跳过此URL，继续处理下一个...")
            await update_crawl_status(collection_id, CRAWL_STATUS_ERROR, error_msg)
            continue
    
    logger.info("爬虫运行完成")


def _crawl_in_thread(site: str, prefix: str, if_llm: bool, model_id: str, provider: str, base_url: str, api_token: str) -> list:
    """
    在独立线程中运行 Playwright 爬虫。
    Windows 上必须在独立线程中使用 ProactorEventLoop 才能创建子进程。
    """
    results = []
    
    def run_crawler():
        # 设置 Windows ProactorEventLoop
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(_async_crawl(site, prefix, if_llm, model_id, provider, base_url, api_token, results))
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_crawler)
    thread.start()
    thread.join()
    
    return results


async def _async_crawl(site: str, prefix: str, if_llm: bool, model_id: str, provider: str, base_url: str, api_token: str, results: list):
    """
    实际执行爬取的异步函数，在独立线程的事件循环中运行。
    """
    content_filter: RelevantContentFilter
    if if_llm:
        content_filter = LLMContentFilter(
                llm_config = LLMConfig(provider=f"{provider}/{model_id}",api_token=api_token,base_url=base_url),
                instruction="""
                Focus on extracting the core educational content.
                Include:
                - Key concepts and explanations
                - Important code examples
                - Essential technical details
                Exclude:
                - Navigation elements
                - Sidebars
                - Footer content
                Format the output as clean markdown with proper code blocks and headers.
                """,
                chunk_token_threshold=4096,
                verbose=True
        )
    else:
        content_filter = PruningContentFilter(
                    threshold=0.4,
                    threshold_type="fixed"
                )
    md_generator = DefaultMarkdownGenerator(
        content_filter=content_filter,
        options={"ignore_links": True,"ignore_images": True}
    )

    browser_conf = BrowserConfig(
        browser_type="chromium",
        headless=True,
        text_mode=True
    )

    prefix_filter = URLPatternFilter(
        patterns=[f"{prefix}*"]
    )
    filter_chain = FilterChain([prefix_filter])

    bfsstrategy = BFSDeepCrawlStrategy(
        max_depth=4,
        include_external=False,
        max_pages=200,
        filter_chain=filter_chain
    )

    config = CrawlerRunConfig(
        deep_crawl_strategy=bfsstrategy,
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True,
        stream=True,
        markdown_generator=md_generator,
    )

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        try:
            async for result in await crawler.arun(site, config=config):
                try:
                    if result.markdown is None:
                        continue
                    if not hasattr(result.markdown, 'fit_markdown') or result.markdown.fit_markdown is None:
                        continue
                    if not result.markdown.fit_markdown.strip():
                        continue
                    
                    # 收集结果，稍后在主线程中处理
                    results.append({
                        "url": result.url,
                        "markdown": result.markdown.fit_markdown
                    })
                except Exception as e:
                    print(f"处理URL {result.url} 时发生错误: {str(e)}")
                    continue
        except Exception as e:
            print(f"爬虫运行时发生错误: {str(e)}")


async def handle_md(md_content, type="print", param=None, collection_id: str = None, document_name: str = None):
    # 最大分块字符数 (保守估计: 1 token ≈ 3-4 字符, 限制 8192 tokens, 留余量用 6000 字符)
    MAX_CHUNK_CHARS = 6000
    
    def split_long_chunk(chunk_text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
        """将过长的文本块拆分成更小的块"""
        if len(chunk_text) <= max_chars:
            return [chunk_text]
        
        # 使用简单的段落分割
        paragraphs = chunk_text.split('\n\n')
        result_chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= max_chars:
                current_chunk += para + '\n\n'
            else:
                if current_chunk.strip():
                    result_chunks.append(current_chunk.strip())
                # 如果单个段落就超过限制，进一步按句子拆分
                if len(para) > max_chars:
                    sentences = para.replace('。', '。\n').replace('. ', '. \n').split('\n')
                    sub_chunk = ""
                    for sent in sentences:
                        if len(sub_chunk) + len(sent) <= max_chars:
                            sub_chunk += sent
                        else:
                            if sub_chunk.strip():
                                result_chunks.append(sub_chunk.strip())
                            # 如果单个句子还是太长，强制截断
                            if len(sent) > max_chars:
                                for i in range(0, len(sent), max_chars):
                                    result_chunks.append(sent[i:i+max_chars])
                            else:
                                sub_chunk = sent
                    if sub_chunk.strip():
                        current_chunk = sub_chunk
                    else:
                        current_chunk = ""
                else:
                    current_chunk = para + '\n\n'
        
        if current_chunk.strip():
            result_chunks.append(current_chunk.strip())
        
        return result_chunks if result_chunks else [chunk_text[:max_chars]]
    
    try:
        if type == "print":
            logger.info(md_content)
        elif type == "stdio":
            with open(param, 'w') as f:
                f.write(md_content)
        elif type == "milvus":
            if param is None:
                logger.error("Milvus存储参数为空")
                return
                
            chunker = TextChunker()
            md_config = ChunkConfig(
                strategy=ChunkStrategy.MARKDOWN_HEADER
            )
            # 使用传入的文档名或默认值
            doc_name = document_name or "未命名文档"
            document = DocumentContent(content=md_content, document_name=doc_name)
            md_result = chunker.chunk_document(document, md_config)
            
            # 检查分块结果
            if md_result is None or not md_result.chunks:
                logger.warning("文档分块结果为空，跳过存储")
                return
            
            # 二次拆分过长的分块
            final_chunks = []
            for chunk in md_result.chunks:
                if len(chunk.page_content) > MAX_CHUNK_CHARS:
                    sub_texts = split_long_chunk(chunk.page_content)
                    for sub_text in sub_texts:
                        final_chunks.append(Document(
                            page_content=sub_text,
                            metadata=chunk.metadata.copy()
                        ))
                else:
                    final_chunks.append(chunk)
            
            # 更新分块结果
            md_result.chunks = final_chunks
            md_result.total_chunks = len(final_chunks)
                
            param[0].store_chunks_batch([md_result])
            logger.info(f"成功存储文档分块，共 {len(md_result.chunks)} 个分块")
            
            # 更新爬虫计数
            if collection_id:
                await increment_crawl_count(collection_id)
                
        elif type == "light_and_milvus":
            if param is None:
                logger.error("Milvus存储参数为空")
                return
                
            chunker = TextChunker()
            md_config = ChunkConfig(
                strategy=ChunkStrategy.MARKDOWN_HEADER
            )
            # 使用传入的文档名或默认值
            doc_name = document_name or "未命名文档"
            document = DocumentContent(content=md_content, document_name=doc_name)
            md_result = chunker.chunk_document(document, md_config)
            
            # 检查分块结果
            if md_result is None or not md_result.chunks:
                logger.warning("文档分块结果为空，跳过存储")
                return
            
            # 二次拆分过长的分块
            final_chunks = []
            for chunk in md_result.chunks:
                if len(chunk.page_content) > MAX_CHUNK_CHARS:
                    sub_texts = split_long_chunk(chunk.page_content)
                    for sub_text in sub_texts:
                        final_chunks.append(Document(
                            page_content=sub_text,
                            metadata=chunk.metadata.copy()
                        ))
                    logger.info(f"拆分过长分块: {len(chunk.page_content)} 字符 -> {len(sub_texts)} 个子分块")
                else:
                    final_chunks.append(chunk)
            
            # 更新分块结果
            md_result.chunks = final_chunks
            md_result.total_chunks = len(final_chunks)
            
            param[0].store_chunks_batch([md_result])
            logger.info(f"成功存储文档分块到Milvus，共 {len(md_result.chunks)} 个分块")
            
            # 注意：不再自动调用 LightRAG 构建知识图谱
            # 知识图谱构建改为由用户通过 /kg-task/start/{collection_id} API 手动触发
            # 这样可以让文献处理快速完成，用户可以立即使用向量检索
            # 详见 backend/api/kg_task.py
            logger.info("向量存储完成。知识图谱可通过 /kg-task/start API 手动启动构建。")
            
            # 更新爬虫计数
            if collection_id:
                await increment_crawl_count(collection_id)
        
            
    except Exception as e:
        error_msg = f"处理markdown内容时发生错误: {str(e)}"
        logger.error(error_msg)
        logger.info("跳过此内容的处理...")
        # 更新状态为错误
        if collection_id:
            await update_crawl_status(collection_id, CRAWL_STATUS_ERROR, error_msg)


async def process_oss_file(request: CrawlRequest):
    """
    处理从 OSS 上传的本地文件
    
    Args:
        request: 包含文件URL和集合ID的请求对象
        
    流程:
    1. 从 OSS 下载文件
    2. 使用 DocumentExtractor 提取文本
    3. 调用 handle_md() 分块存储
    4. 更新 Redis 状态
    """
    from backend.config.oss import get_presigned_url_for_download
    from backend.rag.chunks.document_extraction import DocumentExtractor
    from backend.rag.storage.milvus_storage import MilvusStorage
    from backend.rag.storage.lightrag_storage import LightRAGStorage
    from backend.config.embedding import get_embedding_model
    import tempfile
    import os
    import requests
    
    # 初始化存储
    milvus_storage = MilvusStorage(
        embedding_function=get_embedding_model(),
        collection_name=request.collection_id,
    )
    lightrag_storage = LightRAGStorage(workspace=request.collection_id)
    
    # 初始化状态
    await init_crawl_status(request.collection_id)
    
    try:
        logger.info(f"开始处理 OSS 文件: {request.url}")

        # 1. 从 OSS URL 提取 bucket 和文件名
        # URL 格式: http://localhost:9000/bucket-name/file-name
        from urllib.parse import urlparse, unquote
        parsed_url = urlparse(request.url)
        path_parts = parsed_url.path.strip('/').split('/')

        if len(path_parts) < 2:
            raise ValueError(f"无法从 URL 中提取 bucket 和文件名: {request.url}")

        bucket_name = path_parts[0]
        # 对文件名进行 URL 解码，避免双重编码
        file_name = unquote(path_parts[-1])

        logger.info(f"提取 bucket: {bucket_name}, 文件名: {file_name}")

        # 2. 从 OSS 获取下载 URL
        download_url = get_presigned_url_for_download(
            bucket=bucket_name,
            key=file_name
        )

        if not download_url or not download_url.get("url"):
            raise ValueError("获取 OSS 下载 URL 失败")

        logger.info(f"成功获取下载 URL: {file_name}")
        
        # 3. 下载文件到临时目录
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=os.path.splitext(file_name)[1]
        ) as tmp_file:
            response = requests.get(download_url["url"], timeout=60)
            response.raise_for_status()
            tmp_file.write(response.content)
            tmp_file_path = tmp_file.name
        
        logger.info(f"文件已下载到临时目录: {tmp_file_path}")

        # 4. 提取学术元数据（PR-1新增）
        file_extension = os.path.splitext(file_name)[1].lower().lstrip('.')
        if file_extension == 'pdf':
            from backend.rag.chunks.academic_metadata_extractor import extract_academic_metadata
            from backend.service.knowledge_library import update_document_academic_metadata

            try:
                logger.info(f"开始提取PDF学术元数据: {file_name}")
                academic_metadata = extract_academic_metadata(tmp_file_path, "pdf")
                metadata_dict = academic_metadata.to_dict()

                # 更新数据库中的学术元数据
                await update_document_academic_metadata(
                    collection_id=request.collection_id,
                    url=request.url,
                    metadata=metadata_dict,
                    parse_status="completed"
                )
                logger.info(f"学术元数据提取完成: title={academic_metadata.academic_title}, authors={academic_metadata.authors}")
            except Exception as e:
                logger.warning(f"学术元数据提取失败（非致命）: {str(e)}")
                # 提取失败不影响后续流程，只更新状态
                from backend.service.knowledge_library import update_document_academic_metadata
                await update_document_academic_metadata(
                    collection_id=request.collection_id,
                    url=request.url,
                    metadata={"source_type": "document"},
                    parse_status="failed",
                    parse_error=str(e)
                )

        # 5. 提取文件内容
        extractor = DocumentExtractor()
        document_content = extractor.read_document(tmp_file_path)
        
        logger.info(f"成功提取文件内容，长度: {len(document_content.content)} 字符")
        
        # 4.5 自动提取论文标题并更新数据库
        from backend.service.title_extractor import extract_title_from_text
        from backend.service.knowledge_library import update_document_name_by_url
        
        extracted_title = extract_title_from_text(document_content.content)
        final_document_name = file_name  # 默认使用文件名
        
        if extracted_title:
            logger.info(f"成功提取论文标题: {extracted_title}")
            # 更新数据库中的文档名称
            update_success = await update_document_name_by_url(
                collection_id=request.collection_id,
                url=request.url,
                new_name=extracted_title
            )
            if update_success:
                final_document_name = extracted_title
                logger.info(f"已更新数据库文档名称为: {extracted_title}")
            else:
                logger.warning(f"更新数据库文档名称失败，使用原文件名: {file_name}")
        else:
            logger.info(f"未能提取论文标题，使用原文件名: {file_name}")
        
        # 5. 清理临时文件
        os.unlink(tmp_file_path)
        logger.info(f"已清理临时文件: {tmp_file_path}")
        
        # 6. 分块并存储（复用 handle_md）
        # 注意：document_name 必须使用 URL，因为白名单 filter 使用 URL 进行匹配
        await handle_md(
            md_content=document_content.content,
            type="light_and_milvus",
            param=[milvus_storage, lightrag_storage],
            collection_id=request.collection_id,
            document_name=request.url  # 使用 URL 作为 document_name，与白名单 filter 保持一致
        )
        
        # 7. 更新状态为完成
        await update_crawl_status(request.collection_id, CRAWL_STATUS_COMPLETED)
        logger.info(f"✅ 文件处理完成: {file_name}")
        
    except Exception as e:
        error_msg = f"文件处理失败: {str(e)}"
        logger.error(error_msg)
        # 更新状态为错误
        await update_crawl_status(request.collection_id, CRAWL_STATUS_ERROR, error_msg)
        raise
