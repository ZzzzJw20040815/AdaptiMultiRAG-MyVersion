from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.param.knowledge_library import (
    CreateLibraryRequest, UpdateLibraryRequest, AddDocumentRequest, UpdateDocumentRequest
)
from backend.param.common import Response
from backend.service import knowledge_library as library_service
from backend.service.citation_service import get_all_documents_metadata
from backend.config.log import get_logger
from backend.config.dependencies import get_current_user

logger = get_logger(__name__)

router = APIRouter(
    prefix="/knowledge",
    tags=["KNOWLEDGE_LIBRARY"]
)


@router.get("/libraries")
async def get_libraries(current_user: int = Depends(get_current_user)):
    """获取用户的知识库列表"""
    logger.info(f"用户 {current_user} 请求获取知识库列表")
    return await library_service.get_user_libraries(current_user)


@router.get("/libraries/{library_id}")
async def get_library(library_id: int, current_user: int = Depends(get_current_user)):
    """获取知识库详情"""
    logger.info(f"用户 {current_user} 请求获取知识库详情: {library_id}")
    return await library_service.get_library_detail(library_id, current_user)


@router.post("/libraries")
async def create_library(request: CreateLibraryRequest, current_user: int = Depends(get_current_user)):
    """创建知识库"""
    logger.info(f"用户 {current_user} 请求创建知识库: {request.title}")
    return await library_service.create_library(request, current_user)


@router.put("/libraries/{library_id}")
async def update_library(
    library_id: int,
    request: UpdateLibraryRequest,
    current_user: int = Depends(get_current_user)
):
    """更新知识库"""
    logger.info(f"用户 {current_user} 请求更新知识库: {library_id}")
    return await library_service.update_library(library_id, request, current_user)


@router.delete("/libraries/{library_id}")
async def delete_library(library_id: int, current_user: int = Depends(get_current_user)):
    """删除知识库"""
    logger.info(f"用户 {current_user} 请求删除知识库: {library_id}")
    return await library_service.delete_library(library_id, current_user)


@router.post("/documents")
async def add_document(
    request: AddDocumentRequest,
    current_user: int = Depends(get_current_user)
):
    """添加文档到知识库"""
    logger.info(f"用户 {current_user} 请求添加文档到知识库: {request.library_id}")
    return await library_service.add_document(request, current_user)


@router.put("/documents/{document_id}")
async def update_document(
    document_id: int,
    request: UpdateDocumentRequest,
    current_user: int = Depends(get_current_user)
):
    """更新文档"""
    logger.info(f"用户 {current_user} 请求更新文档: {document_id}")
    return await library_service.update_document(document_id, request, current_user)


from backend.param.crawl import UploadDocRequest
from backend.config.oss import get_presigned_url_for_upload

@router.post("/upload-url")
async def get_upload_url(
    request: UploadDocRequest,
    current_user: int = Depends(get_current_user)
):
    """获取文档上传URL (Presigned URL)"""
    logger.info(f"用户 {current_user} 请求上传URL: {request.document_name}")
    try:
        # 调用 OSS 配置中的方法生成预签名 URL
        # 默认存储到 'rag-data' bucket (在 oss.py 中处理)
        upload_data = get_presigned_url_for_upload(bucket=None, key=request.document_name)
        
        # 返回 URL 字符串，适配前端逻辑
        return Response.success(upload_data["url"])
    except Exception as e:
        logger.error(f"生成上传URL失败: {e}")
        return Response.error(f"生成上传URL失败: {str(e)}")


@router.delete("/documents/{document_id}")
async def delete_document(document_id: int, current_user: int = Depends(get_current_user)):
    """删除文档"""
    logger.info(f"用户 {current_user} 请求删除文档: {document_id}")
    return await library_service.delete_document(document_id, current_user)


@router.get("/citation-metadata/{collection_id}")
async def get_citation_metadata(collection_id: str, current_user: int = Depends(get_current_user)):
    """
    PR-2: 获取知识库的学术引用元数据
    用于历史对话中显示引用标记的学术信息
    """
    logger.info(f"用户 {current_user} 请求获取引用元数据: {collection_id}")
    try:
        citation_metadata = get_all_documents_metadata(collection_id, include_aliases=False)
        if citation_metadata:
            # 转换为可序列化格式
            serializable_metadata = {}
            for doc_name, info in citation_metadata.items():
                serializable_metadata[doc_name] = info.to_dict()
            return Response.success(serializable_metadata)
        else:
            return Response.success({})
    except Exception as e:
        logger.error(f"获取引用元数据失败: {e}")
        return Response.error(f"获取引用元数据失败: {str(e)}")