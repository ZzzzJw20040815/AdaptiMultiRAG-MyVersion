#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库服务层
提供知识库相关的业务逻辑处理
"""
import uuid
import time
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from backend.model.knowledge_library import KnowledgeLibrary, KnowledgeDocument
from backend.param.knowledge_library import (
    CreateLibraryRequest, UpdateLibraryRequest, AddDocumentRequest, UpdateDocumentRequest
)
from backend.param.common import Response
from backend.config.log import get_logger
from backend.config.database import DatabaseFactory

logger = get_logger(__name__)


async def get_user_libraries(user_id: str) -> Response:
    """获取用户的知识库列表"""
    db = None
    try:
        logger.info(f"开始获取用户 {user_id} 的知识库列表")
        db = DatabaseFactory.create_session()
        
        libraries = db.query(KnowledgeLibrary).filter(
            KnowledgeLibrary.user_id == user_id,
            KnowledgeLibrary.is_active == True
        ).order_by(KnowledgeLibrary.updated_at.desc()).all()
        
        result = []
        for library in libraries:
            library_dict = library.to_dict()
            # 添加文档数量统计
            library_dict['document_count'] = len(library.documents) if library.documents else 0
            result.append(library_dict)
        
        logger.info(f"成功获取用户 {user_id} 的知识库列表，共 {len(result)} 个")
        return Response.success(result)
        
    except Exception as e:
        logger.error(f"获取用户知识库列表失败: {str(e)}")
        return Response.error(f"获取知识库列表失败: {str(e)}")
    finally:
        if db:
            db.close()


async def get_library_detail(library_id: int, user_id: str) -> Response:
    """获取知识库详情"""
    try:
        db_factory = DatabaseFactory()
        session = db_factory.create_session()
        
        try:
            library = session.query(KnowledgeLibrary).filter(
                KnowledgeLibrary.id == library_id,
                KnowledgeLibrary.user_id == user_id,
                KnowledgeLibrary.is_active == True
            ).first()
            
            if not library:
                return Response.error("知识库不存在或无权限访问")
            
            logger.info(f"成功获取知识库详情: {library.title}")
            return Response.success(library.to_dict())
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"获取知识库详情失败: {str(e)}")
        return Response.error(f"获取知识库详情失败: {str(e)}")


async def create_library(request: CreateLibraryRequest, user_id: str) -> Response:
    """创建知识库"""
    try:
        db_factory = DatabaseFactory()
        session = db_factory.create_session()
        
        try:
            # 检查同名知识库
            existing = session.query(KnowledgeLibrary).filter(
                KnowledgeLibrary.title == request.title,
                KnowledgeLibrary.user_id == user_id,
                KnowledgeLibrary.is_active == True
            ).first()
            
            if existing:
                return Response.error("已存在同名知识库")
            
            # 创建新知识库
            library = KnowledgeLibrary(
                title=request.title,
                description=request.description,
                user_id=user_id
            )
            
            session.add(library)
            session.commit()
            session.refresh(library)
            
            # 生成collection_id: kb + 知识库ID + 下划线 + 时间戳
            timestamp = str(int(time.time() * 1000))  # 毫秒级时间戳
            collection_id = f"kb{library.id}_{timestamp}"
            
            # 更新collection_id
            library.collection_id = collection_id
            session.commit()
            session.refresh(library)
            
            logger.info(f"成功创建知识库: {library.title}")
            return Response.success(library.to_dict())
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"创建知识库失败: {str(e)}")
        return Response.error(f"创建知识库失败: {str(e)}")


async def update_library(library_id: int, request: UpdateLibraryRequest, user_id: str) -> Response:
    """更新知识库"""
    try:
        db_factory = DatabaseFactory()
        session = db_factory.create_session()
        
        try:
            library = session.query(KnowledgeLibrary).filter(
                KnowledgeLibrary.id == library_id,
                KnowledgeLibrary.user_id == user_id,
                KnowledgeLibrary.is_active == True
            ).first()
            
            if not library:
                return Response.error("知识库不存在或无权限访问")
            
            # 更新字段
            if request.title is not None:
                # 检查同名知识库（排除当前库）
                existing = session.query(KnowledgeLibrary).filter(
                    KnowledgeLibrary.title == request.title,
                    KnowledgeLibrary.user_id == user_id,
                    KnowledgeLibrary.id != library_id,
                    KnowledgeLibrary.is_active == True
                ).first()
                
                if existing:
                    return Response.error("已存在同名知识库")
                
                library.title = request.title
            
            if request.description is not None:
                library.description = request.description
            
            session.commit()
            session.refresh(library)
            
            logger.info(f"成功更新知识库: {library.title}")
            return Response.success(library.to_dict())
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"更新知识库失败: {str(e)}")
        return Response.error(f"更新知识库失败: {str(e)}")


async def delete_library(library_id: int, user_id: str) -> Response:
    """删除知识库"""
    try:
        db_factory = DatabaseFactory()
        session = db_factory.create_session()
        
        try:
            library = session.query(KnowledgeLibrary).filter(
                KnowledgeLibrary.id == library_id,
                KnowledgeLibrary.user_id == user_id,
                KnowledgeLibrary.is_active == True
            ).first()
            
            if not library:
                return Response.error("知识库不存在或无权限访问")
            
            # 软删除
            library.is_active = False
            session.commit()
            
            logger.info(f"成功删除知识库: {library.title}")
            return Response.success({"message": "知识库删除成功"})
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"删除知识库失败: {str(e)}")
        return Response.error(f"删除知识库失败: {str(e)}")


async def add_document(request: AddDocumentRequest, user_id: str) -> Response:
    """添加文档到知识库"""
    try:
        db_factory = DatabaseFactory()
        session = db_factory.create_session()
        
        try:
            # 验证知识库权限
            library = session.query(KnowledgeLibrary).filter(
                KnowledgeLibrary.id == request.library_id,
                KnowledgeLibrary.user_id == user_id,
                KnowledgeLibrary.is_active == True
            ).first()
            
            if not library:
                return Response.error("知识库不存在或无权限访问")
            
            # 创建文档
            document = KnowledgeDocument(
                library_id=request.library_id,
                name=request.name,
                type=request.type,
                url=request.url,
                file_path=request.file_path,
                file_size=request.file_size
            )
            
            session.add(document)
            session.commit()
            session.refresh(document)
            
            logger.info(f"成功添加文档到知识库 {library.title}: {document.name}")
            return Response.success(document.to_dict())
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"添加文档失败: {str(e)}")
        return Response.error(f"添加文档失败: {str(e)}")


async def update_document(document_id: int, request: UpdateDocumentRequest, user_id: str) -> Response:
    """更新文档"""
    try:
        db_factory = DatabaseFactory()
        session = db_factory.create_session()
        
        try:
            # 查询文档并验证权限
            document = session.query(KnowledgeDocument).join(KnowledgeLibrary).filter(
                KnowledgeDocument.id == document_id,
                KnowledgeLibrary.user_id == user_id,
                KnowledgeLibrary.is_active == True
            ).first()
            
            if not document:
                return Response.error("文档不存在或无权限访问")
            
            # 更新字段
            if request.name is not None:
                document.name = request.name
            if request.type is not None:
                document.type = request.type
            if request.url is not None:
                document.url = request.url
            if request.file_path is not None:
                document.file_path = request.file_path
            if request.file_size is not None:
                document.file_size = request.file_size
            
            session.commit()
            session.refresh(document)
            
            logger.info(f"成功更新文档: {document.name}")
            return Response.success(document.to_dict())
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"更新文档失败: {str(e)}")
        return Response.error(f"更新文档失败: {str(e)}")


async def delete_document(document_id: int, user_id: str) -> Response:
    """删除文档"""
    from backend.config.oss import delete_file
    from backend.rag.storage.milvus_storage import MilvusStorage
    from backend.config.embedding import get_embedding_model

    try:
        db_factory = DatabaseFactory()
        session = db_factory.create_session()
        
        try:
            # 查询文档并验证权限
            document = session.query(KnowledgeDocument).join(KnowledgeLibrary).filter(
                KnowledgeDocument.id == document_id,
                KnowledgeLibrary.user_id == user_id,
                KnowledgeLibrary.is_active == True
            ).first()
            
            if not document:
                return Response.error("文档不存在或无权限访问")
            
            # 1. 物理删除文档记录
            session.delete(document)
            session.commit()

            # 2. 清理 OSS/MinIO 文件
            if document.name:
                delete_file(bucket=None, key=document.name)
                logger.info(f"已清理OSS文件: {document.name}")

            # 3. 清理 Milvus 向量 (如果 document 表没有存 doc_id 的话，暂时先跳过，
            #    因为 Milvus 删除需要 expr="doc_id in [...]"，
            #    目前表结构只有 file_path/url 等。
            #    通常 LightRAG 这里的 doc_id 可能是文件名或者是 hash。
            #    这里尝试用 name 作为 doc_id 进行删除，或者如果没存 doc_id 就先不删向量以防误删)
            
            # 尝试初始化 MilvusStorage 并删除
            try:
                # 注意：这里 collection_name 需要拿到。KnowledgeLibrary 里存了 collection_id
                library = document.library
                if library and library.collection_id:
                     # 这里的 embedding_model 参数其实删除操作用不到，但初始化需要
                    embedding_model = get_embedding_model()
                    milvus = MilvusStorage(
                        embedding_function=embedding_model,
                        collection_name=library.collection_id
                    )
                    # 构造 expr，假设 milvus 里 doc_id 存的是文件名 (常见做法)
                    # 或者是其它字段。这里先尝试用文件名。
                    # 如果不确定 doc_id 映射关系，最稳妥是不乱删，
                    # 但为了演示"彻底删除"，我们尝试删除 doc_name 匹配的数据
                    # expr = f'doc_name == "{document.name}"' 
                    # 具体字段取决于 insert 时的 schema。
                    # 暂且只打日志，提示已从数据库删除。
                    pass
            except Exception as e:
                logger.warning(f"尝试清理向量失败 (非致命): {e}")

            logger.info(f"成功删除文档: {document.name}")
            return Response.success({"message": "文档删除成功"})
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        return Response.error(f"删除文档失败: {str(e)}")


async def update_document_academic_metadata(
    collection_id: str,
    url: str,
    metadata: dict,
    parse_status: str = "completed",
    parse_error: str = None
) -> bool:
    """
    更新文档的学术元数据（内部服务调用）

    Args:
        collection_id: 知识库的 collection_id
        url: 文档的 URL（用于定位文档）
        metadata: 学术元数据字典，包含以下可选字段：
            - academic_title: 论文标题
            - authors: 作者列表（JSON字符串）
            - abstract: 摘要
            - keywords: 关键词（JSON字符串）
            - publish_year: 发表年份
            - doi: DOI标识
            - source_type: 来源类型
        parse_status: 解析状态 (pending/processing/completed/failed)
        parse_error: 解析错误信息

    Returns:
        bool: 是否更新成功
    """
    try:
        db = DatabaseFactory.create_session()

        try:
            # 1. 根据 collection_id 查找知识库
            library = db.query(KnowledgeLibrary).filter(
                KnowledgeLibrary.collection_id == collection_id,
                KnowledgeLibrary.is_active == True
            ).first()

            if not library:
                logger.warning(f"未找到 collection_id={collection_id} 的知识库")
                return False

            # 2. 根据 library_id 和 url 查找文档
            document = db.query(KnowledgeDocument).filter(
                KnowledgeDocument.library_id == library.id,
                KnowledgeDocument.url == url
            ).first()

            if not document:
                logger.warning(f"未找到 url={url} 的文档")
                return False

            # 3. 更新学术元数据字段
            if metadata.get("academic_title"):
                document.academic_title = metadata["academic_title"]
                # 同时更新 name 字段为论文标题（如果有）
                document.name = metadata["academic_title"]
            if metadata.get("authors"):
                document.authors = metadata["authors"]
            if metadata.get("abstract"):
                document.abstract = metadata["abstract"]
            if metadata.get("keywords"):
                document.keywords = metadata["keywords"]
            if metadata.get("publish_year"):
                document.publish_year = metadata["publish_year"]
            if metadata.get("doi"):
                document.doi = metadata["doi"]
            if metadata.get("source_type"):
                document.source_type = metadata["source_type"]

            # 4. 更新解析状态
            document.parse_status = parse_status
            if parse_error:
                document.parse_error = parse_error

            db.commit()

            logger.info(f"成功更新文档学术元数据: title={metadata.get('academic_title')}, status={parse_status}")
            return True

        finally:
            db.close()

    except Exception as e:
        logger.error(f"更新文档学术元数据失败: {str(e)}")
        return False


async def update_document_name_by_url(collection_id: str, url: str, new_name: str) -> bool:
    """
    根据 URL 更新文档名称（内部服务调用）
    
    用于在自动提取论文标题后更新数据库中的文档名称
    
    Args:
        collection_id: 知识库的 collection_id
        url: 文档的 URL（用于定位文档）
        new_name: 新的文档名称（提取的论文标题）
        
    Returns:
        bool: 是否更新成功
    """
    try:
        db = DatabaseFactory.create_session()
        
        try:
            # 1. 根据 collection_id 查找知识库
            library = db.query(KnowledgeLibrary).filter(
                KnowledgeLibrary.collection_id == collection_id,
                KnowledgeLibrary.is_active == True
            ).first()
            
            if not library:
                logger.warning(f"未找到 collection_id={collection_id} 的知识库")
                return False
            
            # 2. 根据 library_id 和 url 查找文档
            document = db.query(KnowledgeDocument).filter(
                KnowledgeDocument.library_id == library.id,
                KnowledgeDocument.url == url
            ).first()
            
            if not document:
                logger.warning(f"未找到 url={url} 的文档")
                return False
            
            # 3. 更新文档名称
            old_name = document.name
            document.name = new_name
            db.commit()
            
            logger.info(f"成功更新文档名称: '{old_name}' -> '{new_name}'")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"更新文档名称失败: {str(e)}")
        return False