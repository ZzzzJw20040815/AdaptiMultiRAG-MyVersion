import asyncio
import json
from datetime import datetime
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
import asyncio
import subprocess


# 获取logger实例
logger = get_logger("crawl_service")

# 定义爬虫状态常量
CRAWL_STATUS_PROCESSING = "processing"
CRAWL_STATUS_COMPLETED = "completed"
CRAWL_STATUS_ERROR = "error"


async def initialize_collection_and_store(request: CrawlRequest):
    """
    初始化集合并存储数据
    
    PR-4 增强：支持 arXiv/PDF/网页 智能路由
    - arXiv URL: 获取元数据 + 下载 PDF + 使用 PDF 解析器处理
    - PDF URL: 直接下载 + 使用 PDF 解析器处理
    - 网页 URL: 使用 crawl4ai 爬虫处理
    """
    from backend.service.url_handlers import detect_url_type, smart_url_process, URLType
    
    milvus_storage = MilvusStorage(
        embedding_function=get_embedding_model(),
        collection_name=request.collection_id,
    )

    lightrag_storage = LightRAGStorage(workspace=request.collection_id)
    
    
    # 初始化爬虫状态
    await init_crawl_status(request.collection_id)
    
    # PR-4: 检测 URL 类型
    url_info = detect_url_type(request.url)
    logger.info(f"URL 类型检测: {request.url} -> {url_info.url_type.value}")
    
    # 为对应的知识库添加文档记录
    from backend.service.knowledge_library import add_document
    from backend.param.knowledge_library import AddDocumentRequest
    from backend.config.database import DatabaseFactory
    from backend.model.knowledge_library import KnowledgeLibrary, KnowledgeDocument
    
    document_id = None
    try:
        # 根据collection_id查找知识库
        db = DatabaseFactory.create_session()
        library = db.query(KnowledgeLibrary).filter(
            KnowledgeLibrary.collection_id == request.collection_id,
            KnowledgeLibrary.is_active == True
        ).first()
        
        if library:
            # PR-4: 根据 URL 类型设置文档类型
            doc_type = "link"
            if url_info.url_type == URLType.PDF:
                doc_type = "pdf"
            elif url_info.url_type == URLType.ARXIV:
                doc_type = "pdf"  # arXiv 本质上也是 PDF
            
            # 创建文档记录
            doc_request = AddDocumentRequest(
                library_id=library.id,
                name=request.title or f"[{url_info.url_type.value}] 文档",
                type=doc_type,
                url=request.url
            )
            
            # 添加文档到知识库
            result = await add_document(doc_request, library.user_id)
            if result and result.data:
                document_id = result.data.get('id')
            logger.info(f"成功为知识库 {library.title} 添加文档记录: {request.title or '文档'}")
            
            # PR-4: 如果是 arXiv，预填充元数据
            if url_info.url_type == URLType.ARXIV and url_info.arxiv_id and document_id:
                try:
                    from backend.service.url_handlers import fetch_arxiv_metadata
                    metadata = await fetch_arxiv_metadata(url_info.arxiv_id)
                    if metadata:
                        # 更新文档元数据
                        doc = db.query(KnowledgeDocument).filter(
                            KnowledgeDocument.id == document_id
                        ).first()
                        if doc:
                            doc.paper_title = metadata.get('paper_title')
                            doc.authors = metadata.get('authors')
                            doc.abstract = metadata.get('abstract')
                            doc.keywords = metadata.get('keywords')
                            doc.publication_year = metadata.get('publication_year')
                            doc.publication_venue = metadata.get('publication_venue', 'arXiv')
                            doc.doi = metadata.get('doi')
                            doc.source_url = url_info.normalized_url
                            db.commit()
                            logger.info(f"已更新 arXiv 文档元数据: {url_info.arxiv_id}")
                except Exception as meta_err:
                    logger.warning(f"更新 arXiv 元数据失败: {meta_err}")
        else:
            logger.warning(f"未找到collection_id为 {request.collection_id} 的知识库")
            
    except Exception as e:
        logger.error(f"添加文档记录失败: {str(e)}")
    finally:
        if db:
            db.close()
    
    try:
        # PR-4: 根据 URL 类型选择处理方式
        if url_info.url_type in [URLType.ARXIV, URLType.PDF]:
            # arXiv 和 PDF 类型：下载后使用 PDF 解析器处理
            await process_pdf_url_content(
                url_info, 
                milvus_storage, 
                lightrag_storage, 
                request.collection_id,
                document_id
            )
        else:
            # 网页类型：使用爬虫处理
            await crawl_doc(
                request.url, 
                request.prefix, 
                request.if_llm, 
                request.model_id, 
                request.provider, 
                request.base_url, 
                request.api_key, 
                milvus_storage, 
                lightrag_storage, 
                request.collection_id
            )
        
        # 处理完成，更新状态为已完成
        await update_crawl_status(request.collection_id, CRAWL_STATUS_COMPLETED)
    except Exception as e:
        # 处理异常，更新状态为错误
        await update_crawl_status(request.collection_id, CRAWL_STATUS_ERROR, str(e))
        raise


async def process_pdf_url_content(url_info, milvus_storage, lightrag_storage, collection_id: str, document_id: int = None):
    """
    处理 PDF URL 内容 (PR-4)
    
    下载 PDF 并提取文本，然后存储到向量库和图库
    """
    from backend.service.url_handlers import smart_url_process, URLType
    
    try:
        # 1. 智能处理 URL（下载 PDF）
        result = await smart_url_process(url_info.original_url)
        
        if not result.get("success"):
            error_msg = result.get("error", "未知错误")
            logger.error(f"PDF URL 处理失败: {error_msg}")
            # 回退到网页爬虫
            logger.info("尝试回退到网页爬虫处理...")
            await update_crawl_status(collection_id, CRAWL_STATUS_PROCESSING, f"PDF 下载失败，回退到网页模式")
            # 这里可以调用 crawl_doc 作为兜底，但简单起见先抛出异常
            raise Exception(f"PDF 处理失败: {error_msg}")
        
        pdf_path = result.get("pdf_path")
        if not pdf_path:
            raise Exception("PDF 下载成功但未获取到文件路径")
        
        logger.info(f"PDF 已下载到: {pdf_path}")
        
        # 2. 使用 PDF 提取器提取文本
        try:
            # 尝试使用现有的 PDF 提取器
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()
            
            # 简单的 PDF 文本提取（后续 PR-6 会增强）
            extracted_text = await extract_pdf_text_simple(pdf_path)
            
            if not extracted_text or len(extracted_text.strip()) < 100:
                logger.warning("PDF 文本提取结果太短，可能提取失败")
                raise Exception("PDF 文本提取失败或内容太少")
            
            logger.info(f"PDF 文本提取成功: {len(extracted_text)} 字符")
            
        finally:
            # 清理临时文件
            import os
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                logger.info(f"已清理临时文件: {pdf_path}")
        
        # 3. 存储到向量库和图库
        await handle_md(
            md_content=extracted_text,
            type="light_and_milvus",
            param=[milvus_storage, lightrag_storage],
            collection_id=collection_id
        )
        
        logger.info(f"PDF 内容已存储到知识库")
        
        # 4. 更新文档状态为已完成
        if document_id:
            from backend.config.database import DatabaseFactory
            from backend.model.knowledge_library import KnowledgeDocument, ParseStatus
            
            db = DatabaseFactory.create_session()
            try:
                doc = db.query(KnowledgeDocument).filter(
                    KnowledgeDocument.id == document_id
                ).first()
                if doc:
                    doc.parse_status = ParseStatus.COMPLETED.value
                    doc.is_processed = True
                    db.commit()
            finally:
                db.close()
        
    except Exception as e:
        logger.error(f"处理 PDF URL 内容失败: {e}")
        
        # 更新文档状态为失败
        if document_id:
            from backend.config.database import DatabaseFactory
            from backend.model.knowledge_library import KnowledgeDocument, ParseStatus
            
            db = DatabaseFactory.create_session()
            try:
                doc = db.query(KnowledgeDocument).filter(
                    KnowledgeDocument.id == document_id
                ).first()
                if doc:
                    doc.parse_status = ParseStatus.FAILED.value
                    doc.parse_error = str(e)
                    db.commit()
            finally:
                db.close()
        
        raise


async def extract_pdf_text_simple(pdf_path: str) -> str:
    """
    简单的 PDF 文本提取 (PR-4)
    
    使用 PyPDF2 提取文本，后续 PR-6 会使用更高级的解析器
    """
    try:
        import PyPDF2
        
        text_parts = []
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text:
                        text_parts.append(f"[Page {page_num + 1}]\n{text}")
                except Exception as page_err:
                    logger.warning(f"提取第 {page_num + 1} 页失败: {page_err}")
        
        return "\n\n".join(text_parts)
        
    except ImportError:
        logger.warning("PyPDF2 未安装，尝试使用备用方法")
        # 备用方法：使用 pdfminer 或其他
        return ""
    except Exception as e:
        logger.error(f"PDF 文本提取失败: {e}")
        return ""




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
        filter_chain=filter_chain
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
            try:
                async for result in await crawler.arun(site, config=config):
                    try:
                        logger.info(f"URL: {result.url}")
                        
                        # 检查result.markdown是否存在且不为None
                        if result.markdown is None:
                            logger.warning(f"URL {result.url} 的markdown内容为空，跳过处理")
                            continue
                            
                        # 检查fit_markdown是否存在且不为空
                        if not hasattr(result.markdown, 'fit_markdown') or result.markdown.fit_markdown is None:
                            logger.warning(f"URL {result.url} 的fit_markdown内容为空，跳过处理")
                            continue
                            
                        # 检查内容是否为空字符串
                        if not result.markdown.fit_markdown.strip():
                            logger.warning(f"URL {result.url} 的内容为空，跳过处理")
                            continue
                            
                        await handle_md(md_content=result.markdown.fit_markdown, type="light_and_milvus", param=[milvus_storage, lightrag_storage], collection_id=collection_id)
                        # await handle_md(md_content=result.markdown.fit_markdown, type="milvus", param=[milvus_storage], collection_id=collection_id)
                        logger.info(f"成功处理: {result.url}")
                        
                    except Exception as e:
                        error_msg = f"处理URL {result.url} 时发生错误: {str(e)}"
                        logger.error(error_msg)
                        logger.info("跳过此URL，继续处理下一个...")
                        # 更新状态为错误
                        await update_crawl_status(collection_id, CRAWL_STATUS_ERROR, error_msg)
                        continue
                        
            except Exception as e:
                error_msg = f"爬虫运行时发生错误: {str(e)}"
                logger.error(error_msg)
                logger.info("爬虫任务中断，但程序继续运行...")
                # 更新状态为错误
                await update_crawl_status(collection_id, CRAWL_STATUS_ERROR, error_msg)
            logger.info("爬虫运行完成")


async def handle_md(md_content, type="print", param=None, collection_id: str = None):
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
            document = DocumentContent(content=md_content, document_name="crawled_document")
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
            document = DocumentContent(content=md_content, document_name="crawled_document")
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
            # 将Document对象转换为字符串列表
            text_chunks = [chunk.page_content for chunk in md_result.chunks]
            await param[1].insert_texts(text_chunks)
            logger.info("成功存储文档到LightRAG")
            
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
