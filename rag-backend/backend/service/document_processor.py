#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档处理器服务层 (PR-2)
提供文档解析状态机和处理队列逻辑
"""
import asyncio
import hashlib
import os
import re
from urllib.parse import urlparse
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from backend.model.knowledge_library import KnowledgeDocument, KnowledgeLibrary, ParseStatus
from backend.param.common import Response
from backend.config.log import get_logger
from backend.config.database import DatabaseFactory

logger = get_logger(__name__)


class DocumentProcessor:
    """
    文档处理器
    
    实现文档解析状态机：
    - pending → processing → completed/failed
    
    支持：
    - 异步处理
    - 重试机制
    - 可插拔的处理函数
    """
    
    # 最大重试次数
    MAX_RETRIES = 3
    
    # 默认处理超时（秒）
    DEFAULT_TIMEOUT = int(os.getenv("DOCUMENT_PROCESS_TIMEOUT", "300"))
    # 元数据提取超时（秒）
    METADATA_TIMEOUT = int(os.getenv("DOCUMENT_METADATA_TIMEOUT", "60"))
    # LightRAG 索引构建超时（秒）
    LIGHTRAG_TIMEOUT = int(os.getenv("LIGHTRAG_INSERT_TIMEOUT", str(DEFAULT_TIMEOUT)))
    # LightRAG 索引最大字符数（0 表示不限制）
    LIGHTRAG_MAX_CHARS = int(os.getenv("LIGHTRAG_MAX_CHARS", "20000"))
    # 向量索引最大字符数（0 表示不限制）
    VECTOR_MAX_CHARS = int(os.getenv("VECTOR_MAX_CHARS", "0"))
    # 向量分块配置
    VECTOR_CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    VECTOR_CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
    VECTOR_CHUNK_STRATEGY = os.getenv("VECTOR_CHUNK_STRATEGY", "recursive").lower()
    VECTOR_INSERT_BATCH_CHUNKS = int(os.getenv("VECTOR_INSERT_BATCH_CHUNKS", "80"))
    # 处理中超时阈值（秒）
    STALE_PROCESSING_SECONDS = int(os.getenv("DOCUMENT_PROCESS_STALE_SECONDS", "1800"))
    
    def __init__(self):
        """初始化处理器"""
        self._processing_handlers: Dict[str, Callable] = {}
        
    def register_handler(self, doc_type: str, handler: Callable):
        """
        注册文档类型处理器
        
        Args:
            doc_type: 文档类型 (pdf, docx, link, etc.)
            handler: 处理函数，签名: async def handler(document: KnowledgeDocument) -> Dict[str, Any]
        """
        self._processing_handlers[doc_type] = handler
        logger.info(f"已注册 {doc_type} 类型处理器")
    
    async def get_document_by_id(self, document_id: int, user_id: str) -> Optional[KnowledgeDocument]:
        """
        获取文档（带权限验证）
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
            
        Returns:
            文档对象或 None
        """
        db = None
        try:
            db = DatabaseFactory.create_session()
            
            document = db.query(KnowledgeDocument).join(KnowledgeLibrary).filter(
                KnowledgeDocument.id == document_id,
                KnowledgeLibrary.user_id == user_id,
                KnowledgeLibrary.is_active == True
            ).first()
            
            return document
        finally:
            if db:
                db.close()
    
    async def update_parse_status(
        self, 
        document_id: int, 
        status: ParseStatus, 
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新文档解析状态
        
        Args:
            document_id: 文档ID
            status: 新状态
            error_message: 错误信息（仅 FAILED 状态）
            metadata: 解析出的元数据（仅 COMPLETED 状态）
            
        Returns:
            是否更新成功
        """
        db = None
        try:
            db = DatabaseFactory.create_session()
            
            document = db.query(KnowledgeDocument).filter(
                KnowledgeDocument.id == document_id
            ).first()
            
            if not document:
                logger.error(f"文档 {document_id} 不存在")
                return False
            
            # 状态流转验证
            old_status = document.parse_status
            if not self._is_valid_transition(old_status, status.value):
                logger.warning(f"无效的状态流转: {old_status} → {status.value}")
                return False
            
            # 更新状态
            document.parse_status = status.value
            
            if status == ParseStatus.FAILED:
                document.parse_error = error_message
            elif status == ParseStatus.COMPLETED:
                document.parse_error = None  # 清除错误信息
                document.is_processed = True  # 同步更新旧字段
                
                # 更新解析出的元数据
                if metadata:
                    if metadata.get('paper_title'):
                        document.paper_title = metadata['paper_title']
                    if metadata.get('authors'):
                        document.authors = metadata['authors']
                    if metadata.get('affiliations'):
                        document.affiliations = metadata['affiliations']
                    if metadata.get('doi'):
                        document.doi = metadata['doi']
                    if metadata.get('abstract'):
                        document.abstract = metadata['abstract']
                    if metadata.get('keywords'):
                        document.keywords = metadata['keywords']
                    if metadata.get('publication_venue'):
                        document.publication_venue = metadata['publication_venue']
                    if metadata.get('publication_year'):
                        document.publication_year = metadata['publication_year']
                    if metadata.get('references'):
                        document.references = metadata['references']
            
            db.commit()
            logger.info(f"文档 {document_id} 状态更新: {old_status} → {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"更新文档状态失败: {e}")
            if db:
                db.rollback()
            return False
        finally:
            if db:
                db.close()
    
    def _is_valid_transition(self, old_status: str, new_status: str) -> bool:
        """
        验证状态流转是否有效
        
        有效流转：
        - pending → processing
        - processing → completed
        - processing → failed
        - failed → pending (重试)
        """
        valid_transitions = {
            ParseStatus.PENDING.value: [ParseStatus.PROCESSING.value],
            ParseStatus.PROCESSING.value: [ParseStatus.COMPLETED.value, ParseStatus.FAILED.value],
            ParseStatus.FAILED.value: [ParseStatus.PENDING.value],  # 允许重试
            ParseStatus.COMPLETED.value: [],  # 已完成不允许再变更
        }
        
        allowed = valid_transitions.get(old_status, [])
        return new_status in allowed

    def _is_processing_stale(self, document: KnowledgeDocument) -> bool:
        if not document.updated_at:
            return False
        elapsed = (datetime.now() - document.updated_at).total_seconds()
        return elapsed > self.STALE_PROCESSING_SECONDS
    
    async def process_document(
        self, 
        document_id: int, 
        user_id: str,
        force_retry: bool = False
    ) -> Response:
        """
        处理单个文档
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
            force_retry: 是否强制重试（即使已失败）
            
        Returns:
            处理结果
        """
        db = None
        try:
            db = DatabaseFactory.create_session()
            
            # 获取文档
            document = db.query(KnowledgeDocument).join(KnowledgeLibrary).filter(
                KnowledgeDocument.id == document_id,
                KnowledgeLibrary.user_id == user_id,
                KnowledgeLibrary.is_active == True
            ).first()
            
            if not document:
                return Response.error("文档不存在或无权限访问")
            
            # 检查当前状态
            current_status = document.parse_status
            
            if current_status == ParseStatus.COMPLETED.value:
                return Response.error("文档已处理完成，无需重复处理")
            
            if current_status == ParseStatus.PROCESSING.value:
                if self._is_processing_stale(document):
                    logger.warning(f"文档 {document.id} 处理超时，重置为 pending")
                    document.parse_status = ParseStatus.PENDING.value
                    document.parse_error = "处理超时，已自动重置"
                    db.commit()
                else:
                    return Response.error("文档正在处理中，请稍后")
            
            if current_status == ParseStatus.FAILED.value:
                if not force_retry:
                    return Response.error(
                        f"文档处理失败: {document.parse_error}。如需重试请设置 force_retry=true"
                    )
                # 重试：先重置为 pending
                document.parse_status = ParseStatus.PENDING.value
                db.commit()
            
            # 关闭数据库连接后进行异步处理
            doc_type = document.type
            doc_id = document.id
            
        finally:
            if db:
                db.close()
        
        # 异步触发处理（不阻塞响应）
        asyncio.create_task(self._async_process(doc_id, doc_type, user_id))
        
        return Response.success({
            "document_id": doc_id,
            "status": "processing",
            "message": "文档处理已启动，请稍后查询状态"
        })
    
    async def _async_process(self, document_id: int, doc_type: str, user_id: str):
        """
        异步处理文档（后台任务）
        
        Args:
            document_id: 文档ID
            doc_type: 文档类型
            user_id: 用户ID
        """
        try:
            # 更新为处理中
            await self.update_parse_status(document_id, ParseStatus.PROCESSING)
            
            # 获取处理器
            handler = self._processing_handlers.get(doc_type)
            
            if not handler:
                # 使用默认处理器
                handler = self._default_handler
                logger.warning(f"文档类型 {doc_type} 无专用处理器，使用默认处理器")
            
            # 获取文档信息
            db = DatabaseFactory.create_session()
            try:
                document = db.query(KnowledgeDocument).filter(
                    KnowledgeDocument.id == document_id
                ).first()
                
                if not document:
                    raise ValueError(f"文档 {document_id} 不存在")
                
                # 计算文件哈希（如果有文件路径）
                file_hash = None
                if document.file_path:
                    file_hash = await self._compute_file_hash(document.file_path)
                    if file_hash:
                        document.file_hash = file_hash
                        db.commit()
                
                # 复制必要信息用于后续处理
                collection_id = document.library.collection_id if document.library else None
                doc_info = {
                    'id': document.id,
                    'name': document.name,
                    'type': document.type,
                    'url': document.url,
                    'file_path': document.file_path,
                    'file_hash': file_hash,
                    'collection_id': collection_id
                }
            finally:
                db.close()
            
            # 执行处理
            logger.info(f"开始处理文档 {document_id} (类型: {doc_type})")
            result = await handler(doc_info)

            vector_text = None
            lightrag_text = None
            if isinstance(result, dict):
                vector_text = result.pop("_vector_text", None)
                lightrag_text = result.pop("_lightrag_text", None)

            if not collection_id:
                raise ValueError("文档缺少 collection_id，无法构建索引")

            pdf_source = self._get_pdf_source(doc_info)
            if pdf_source:
                try:
                    await self._build_milvus_index_from_pdf(
                        collection_id=collection_id,
                        document_id=document_id,
                        document_name=doc_info.get("name"),
                        source_url=doc_info.get("url") or doc_info.get("file_path"),
                        pdf_source=pdf_source
                    )
                except Exception as e:
                    if vector_text:
                        logger.warning(f"PDF 流式向量索引失败，回退为文本索引: {e}")
                        await self._build_milvus_index(
                            collection_id=collection_id,
                            document_id=document_id,
                            document_name=doc_info.get("name"),
                            source_url=doc_info.get("url") or doc_info.get("file_path"),
                            text_content=vector_text
                        )
                    else:
                        raise
            else:
                if not vector_text:
                    raise ValueError("未获取到可索引文本，无法构建向量索引")
                await self._build_milvus_index(
                    collection_id=collection_id,
                    document_id=document_id,
                    document_name=doc_info.get("name"),
                    source_url=doc_info.get("url") or doc_info.get("file_path"),
                    text_content=vector_text
                )

            # 更新为完成
            await self.update_parse_status(
                document_id,
                ParseStatus.COMPLETED,
                metadata=result
            )
            logger.info(f"文档 {document_id} 处理完成")

            if lightrag_text:
                asyncio.create_task(self._build_lightrag_index(collection_id, lightrag_text))
                logger.info(f"LightRAG 索引构建已转为后台任务: {collection_id}")
            else:
                logger.warning("缺少可用文本，跳过 LightRAG 索引构建")
            
        except Exception as e:
            # 更新为失败
            error_msg = str(e)
            logger.error(f"文档 {document_id} 处理失败: {error_msg}")
            await self.update_parse_status(
                document_id, 
                ParseStatus.FAILED,
                error_message=error_msg
            )
    
    async def _default_handler(self, doc_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        默认处理器 (PR-6 增强)
        
        使用 LLM 从文档中提取学术元数据
        """
        from backend.service.academic_metadata_extractor import extract_academic_metadata
        
        logger.info(f"使用默认处理器处理文档: {doc_info['name']}")
        
        # 获取文档文本内容
        text_content = await self._get_document_text(doc_info)
        
        if not text_content:
            logger.warning(f"无法获取文档 {doc_info['name']} 的文本内容")
            return {
                'paper_title': None,
                'authors': None,
                'abstract': None,
                'keywords': None,
            }
        
        # 使用 LLM 提取元数据
        # 使用 LLM 提取元数据
        metadata_dict = {
            'paper_title': None,
            'authors': None,
            'abstract': None,
            'keywords': None,
        }
        
        try:
            metadata = await asyncio.wait_for(
                extract_academic_metadata(text_content, use_llm=True),
                timeout=self.METADATA_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning("元数据提取超时，回退启发式方法")
            metadata = await extract_academic_metadata(text_content, use_llm=False)
        except Exception as e:
            logger.error(f"元数据提取失败: {e}")
            metadata = await extract_academic_metadata(text_content, use_llm=False)
        try:
            metadata_dict = metadata.to_dict()
            logger.info(f"元数据提取成功: {metadata_dict.get('paper_title', '未知标题')}")
        except Exception as e:
            logger.error(f"元数据提取失败: {e}")
            
        vector_text = self._prepare_vector_text(text_content)
        lightrag_text = self._prepare_index_text(text_content)

        if vector_text:
            metadata_dict["_vector_text"] = vector_text
        else:
            logger.warning("文档文本为空，跳过向量索引构建")

        if lightrag_text:
            metadata_dict["_lightrag_text"] = lightrag_text
        else:
            logger.warning("文档文本为空，跳过 LightRAG 索引构建")

        return metadata_dict

    def _strip_reference_section(self, text: str) -> str:
        if not text:
            return text
        match = re.search(r'(?m)^\s*(references|参考文献)\b', text, re.IGNORECASE)
        if match:
            return text[:match.start()].strip()
        return text

    def _prepare_index_text(self, text: str) -> str:
        if not text:
            return text
        index_text = self._strip_reference_section(text)
        if self.LIGHTRAG_MAX_CHARS > 0 and len(index_text) > self.LIGHTRAG_MAX_CHARS:
            index_text = index_text[:self.LIGHTRAG_MAX_CHARS]
        return index_text

    def _prepare_vector_text(self, text: str) -> str:
        if not text:
            return text
        vector_text = self._strip_reference_section(text)
        if self.VECTOR_MAX_CHARS > 0 and len(vector_text) > self.VECTOR_MAX_CHARS:
            vector_text = vector_text[:self.VECTOR_MAX_CHARS]
        return vector_text

    def _get_pdf_source(self, doc_info: Dict[str, Any]) -> Optional[str]:
        url = doc_info.get("url") or ""
        file_path = doc_info.get("file_path") or ""
        name = doc_info.get("name") or ""

        if self._is_pdf_reference(url):
            return url
        if self._is_pdf_reference(file_path):
            return file_path
        if name.lower().endswith(".pdf"):
            return url or file_path
        return None

    def _is_pdf_reference(self, value: str) -> bool:
        if not value:
            return False
        lower = value.lower()
        if lower.endswith(".pdf"):
            return True
        try:
            parsed = urlparse(value)
            return parsed.path.lower().endswith(".pdf")
        except Exception:
            return False

    async def _build_milvus_index(
        self,
        collection_id: str,
        document_id: int,
        document_name: Optional[str],
        source_url: Optional[str],
        text_content: str
    ) -> None:
        if not collection_id or not text_content:
            raise ValueError("向量索引缺少必要参数")

        from backend.config.embedding import get_embedding_model
        from backend.rag.storage.milvus_storage import MilvusStorage
        from backend.rag.chunks.chunks import TextChunker
        from backend.rag.chunks.models import ChunkConfig, ChunkStrategy, DocumentContent

        logger.info(f"开始 Milvus 向量索引构建，collection: {collection_id}")

        embeddings_model = get_embedding_model()
        milvus_storage = MilvusStorage(
            embedding_function=embeddings_model,
            collection_name=collection_id
        )

        chunker = TextChunker()
        strategy = ChunkStrategy.RECURSIVE if self.VECTOR_CHUNK_STRATEGY != "character" else ChunkStrategy.CHARACTER
        chunk_config = ChunkConfig(
            strategy=strategy,
            chunk_size=self.VECTOR_CHUNK_SIZE,
            chunk_overlap=self.VECTOR_CHUNK_OVERLAP
        )

        document = DocumentContent(
            content=text_content,
            document_name=document_name or f"doc_{document_id}",
            doc_id=document_id,
            source_url=source_url
        )

        chunk_result = chunker.chunk_document(document, chunk_config)
        if not chunk_result.chunks:
            raise ValueError("文档分块结果为空，无法构建向量索引")

        milvus_storage.store_chunks_batch([chunk_result])
        logger.info(f"Milvus 向量索引构建完成，共 {len(chunk_result.chunks)} 个分块")

    async def _build_milvus_index_from_pdf(
        self,
        collection_id: str,
        document_id: int,
        document_name: Optional[str],
        source_url: Optional[str],
        pdf_source: str
    ) -> None:
        from backend.config.embedding import get_embedding_model
        from backend.rag.storage.milvus_storage import MilvusStorage
        from backend.rag.chunks.chunks import TextChunker
        from backend.rag.chunks.models import ChunkConfig, ChunkStrategy, DocumentContent

        logger.info(f"开始 PDF 按页向量索引构建，collection: {collection_id}")

        embeddings_model = get_embedding_model()
        milvus_storage = MilvusStorage(
            embedding_function=embeddings_model,
            collection_name=collection_id
        )

        chunker = TextChunker()
        strategy = ChunkStrategy.RECURSIVE if self.VECTOR_CHUNK_STRATEGY != "character" else ChunkStrategy.CHARACTER
        chunk_config = ChunkConfig(
            strategy=strategy,
            chunk_size=self.VECTOR_CHUNK_SIZE,
            chunk_overlap=self.VECTOR_CHUNK_OVERLAP
        )

        batch_results = []
        batch_chunks = 0
        total_chunks = 0

        async for page_number, page_text in self._iter_pdf_pages(pdf_source):
            if not page_text or not page_text.strip():
                continue

            document = DocumentContent(
                content=page_text,
                document_name=document_name or f"doc_{document_id}",
                doc_id=document_id,
                source_url=source_url
            )
            chunk_result = chunker.chunk_document(document, chunk_config)
            if not chunk_result.chunks:
                continue

            for chunk in chunk_result.chunks:
                chunk.metadata["page_number"] = page_number

            batch_results.append(chunk_result)
            batch_chunks += len(chunk_result.chunks)

            if batch_chunks >= self.VECTOR_INSERT_BATCH_CHUNKS:
                milvus_storage.store_chunks_batch(batch_results)
                total_chunks += batch_chunks
                logger.info(f"已入库 {total_chunks} 个分块（按页批次）")
                batch_results = []
                batch_chunks = 0

        if batch_results:
            milvus_storage.store_chunks_batch(batch_results)
            total_chunks += batch_chunks

        if total_chunks == 0:
            raise ValueError("PDF 按页分块结果为空，无法构建向量索引")

        logger.info(f"PDF 向量索引构建完成，共 {total_chunks} 个分块")

    async def _iter_pdf_pages(self, pdf_source: str):
        import tempfile
        import os
        import PyPDF2
        from backend.service.url_handlers import download_pdf

        pdf_path = None
        temp_file = None

        if pdf_source.startswith("http"):
            pdf_content, error = await download_pdf(pdf_source)
            if not pdf_content:
                raise ValueError(f"下载 PDF 失败: {error}")
            temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            temp_file.write(pdf_content)
            temp_file.close()
            pdf_path = temp_file.name
        else:
            pdf_path = pdf_source

        try:
            with open(pdf_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                total_pages = len(reader.pages)
                max_pages = int(os.getenv("PDF_MAX_PAGES", "0"))
                page_limit = total_pages if max_pages <= 0 else min(max_pages, total_pages)

                for page_num in range(page_limit):
                    page = reader.pages[page_num]
                    text = page.extract_text() or ""
                    yield page_num + 1, text
        finally:
            if temp_file and os.path.exists(temp_file.name):
                os.remove(temp_file.name)

    async def _build_lightrag_index(self, collection_id: str, text_content: str) -> None:
        if not collection_id or not text_content:
            return
        try:
            from backend.rag.storage.lightrag_storage import LightRAGStorage
            logger.info(f"开始 LightRAG 索引构建，workspace: {collection_id}")

            storage = LightRAGStorage(workspace=collection_id)
            await storage.initialize()

            index_text = self._prepare_index_text(text_content)
            if not index_text:
                logger.warning("文档文本为空，跳过 LightRAG 索引构建")
                return

            await asyncio.wait_for(
                storage.insert_text(index_text),
                timeout=self.LIGHTRAG_TIMEOUT
            )
            logger.info("LightRAG 索引构建完成")
        except asyncio.TimeoutError:
            logger.error(f"LightRAG 索引构建超时({self.LIGHTRAG_TIMEOUT}s)")
        except Exception as e:
            logger.error(f"LightRAG 索引构建失败: {e}")
    
    async def _get_document_text(self, doc_info: Dict[str, Any]) -> Optional[str]:
        """
        获取文档文本内容 (PR-6)
        
        根据文档类型获取文本：
        - PDF: 从文件提取
        - 网页: 从 URL 爬取
        - 文件: 尝试读取
        
        Args:
            doc_info: 文档信息
            
        Returns:
            文档文本或 None
        """
        doc_type = doc_info.get('type', '')
        url = doc_info.get('url', '')
        file_path = doc_info.get('file_path', '')
        
        try:
            # PDF 类型 (本地文件或 URL)
            if doc_type == 'file' or doc_type == 'pdf' or (url and url.lower().endswith('.pdf')):
                # 对于本地上传的文件，尝试获取 presigned URL
                if doc_type == 'file' and not file_path:
                    # 尝试从 OSS 获取
                    try:
                        from backend.config.oss import get_presigned_url_for_download
                        # 假设 document name 就是 OSS key
                        file_name = doc_info.get('name')
                        if file_name:
                            presigned = get_presigned_url_for_download(bucket=None, key=file_name)
                            if presigned and presigned.get('url'):
                                # 使用临时的预签名 URL 进行下载
                                return await self._extract_pdf_text(presigned['url'])
                    except Exception as oss_err:
                        logger.warning(f"尝试从 OSS 获取文件失败: {oss_err}")
                
                return await self._extract_pdf_text(url or file_path)
            
            # 网页链接类型
            if doc_type == 'link' and url:
                return await self._fetch_webpage_text(url)
            
            # 普通文件 (已有本地路径)
            if file_path:
                return await self._read_file_text(file_path)
            
            return None
            
        except Exception as e:
            logger.error(f"获取文档文本失败: {e}")
            return None
    
    async def _extract_pdf_text(self, pdf_source: str) -> Optional[str]:
        """
        从 PDF 提取文本
        
        Args:
            pdf_source: PDF URL 或文件路径
            
        Returns:
            提取的文本或 None
        """
        try:
            import tempfile
            import os
            
            pdf_path = None
            temp_file = None
            
            # 如果是 URL，先下载
            if pdf_source.startswith('http'):
                from backend.service.url_handlers import download_pdf
                
                pdf_content, error = await download_pdf(pdf_source)
                if not pdf_content:
                    logger.warning(f"下载 PDF 失败: {error}")
                    return None
                
                # 保存到临时文件
                temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                temp_file.write(pdf_content)
                temp_file.close()
                pdf_path = temp_file.name
            else:
                pdf_path = pdf_source
            
            # 使用 PyPDF2 提取文本
            try:
                import PyPDF2
                
                text_parts = []
                max_pages = int(os.getenv("PDF_MAX_PAGES", "0"))
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    total_pages = len(reader.pages)
                    page_limit = total_pages if max_pages <= 0 else min(max_pages, total_pages)
                    # 默认提取全文，避免只取前几页导致检索缺失
                    for page_num in range(page_limit):
                        page = reader.pages[page_num]
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                
                return "\n\n".join(text_parts)
                
            finally:
                # 清理临时文件
                if temp_file and os.path.exists(temp_file.name):
                    os.remove(temp_file.name)
                    
        except Exception as e:
            logger.error(f"PDF 文本提取失败: {e}")
            return None
    
    async def _fetch_webpage_text(self, url: str) -> Optional[str]:
        """
        获取网页文本内容
        
        Args:
            url: 网页 URL
            
        Returns:
            网页文本或 None
        """
        try:
            import aiohttp
            from bs4 import BeautifulSoup
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # 移除脚本和样式
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        text = soup.get_text()
                        # 清理空白
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = '\n'.join(chunk for chunk in chunks if chunk)
                        
                        return text[:20000]  # 限制长度
                    
                    return None
                    
        except Exception as e:
            logger.error(f"获取网页文本失败: {e}")
            return None
    
    async def _read_file_text(self, file_path: str) -> Optional[str]:
        """
        读取文件文本内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件文本或 None
        """
        try:
            # OSS 文件处理（简化版）
            if file_path.startswith('http'):
                import aiohttp
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(file_path, timeout=aiohttp.ClientTimeout(total=60)) as response:
                        if response.status == 200:
                            return (await response.text())[:20000]
                return None
            
            # 本地文件
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()[:20000]
                
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return None
    
    async def _compute_file_hash(self, file_path: str) -> Optional[str]:
        """
        计算文件 SHA-256 哈希
        
        Args:
            file_path: 文件路径（OSS key 或本地路径）
            
        Returns:
            哈希值或 None
        """
        try:
            # TODO: 实现 OSS 文件哈希计算
            # 当前返回 None，后续 PR 实现
            return None
        except Exception as e:
            logger.warning(f"计算文件哈希失败: {e}")
            return None
    
    async def get_pending_documents(self, library_id: Optional[int] = None, limit: int = 10) -> list:
        """
        获取待处理的文档列表
        
        Args:
            library_id: 可选，限定知识库
            limit: 最大返回数量
            
        Returns:
            待处理文档列表
        """
        db = None
        try:
            db = DatabaseFactory.create_session()
            
            query = db.query(KnowledgeDocument).filter(
                KnowledgeDocument.parse_status == ParseStatus.PENDING.value
            )
            
            if library_id:
                query = query.filter(KnowledgeDocument.library_id == library_id)
            
            documents = query.limit(limit).all()
            return [doc.to_dict() for doc in documents]
            
        finally:
            if db:
                db.close()
    
    async def retry_failed_document(self, document_id: int, user_id: str) -> Response:
        """
        重试失败的文档
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
            
        Returns:
            处理结果
        """
        return await self.process_document(document_id, user_id, force_retry=True)
    
    async def get_processing_stats(self, library_id: int, user_id: str) -> Response:
        """
        获取知识库文档处理统计
        
        Args:
            library_id: 知识库ID
            user_id: 用户ID
            
        Returns:
            统计信息
        """
        db = None
        try:
            db = DatabaseFactory.create_session()
            
            # 验证权限
            library = db.query(KnowledgeLibrary).filter(
                KnowledgeLibrary.id == library_id,
                KnowledgeLibrary.user_id == user_id,
                KnowledgeLibrary.is_active == True
            ).first()
            
            if not library:
                return Response.error("知识库不存在或无权限访问")
            
            # 统计各状态数量
            from sqlalchemy import func as sql_func
            
            stats = db.query(
                KnowledgeDocument.parse_status,
                sql_func.count(KnowledgeDocument.id)
            ).filter(
                KnowledgeDocument.library_id == library_id
            ).group_by(
                KnowledgeDocument.parse_status
            ).all()
            
            result = {
                'total': 0,
                'pending': 0,
                'processing': 0,
                'completed': 0,
                'failed': 0,
            }
            
            for status, count in stats:
                result['total'] += count
                if status in result:
                    result[status] = count
            
            return Response.success(result)
            
        except Exception as e:
            logger.error(f"获取处理统计失败: {e}")
            return Response.error(f"获取统计失败: {str(e)}")
        finally:
            if db:
                db.close()


# 全局处理器实例
document_processor = DocumentProcessor()
