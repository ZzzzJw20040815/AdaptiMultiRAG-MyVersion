"""知识图谱构建任务 API

提供知识图谱构建任务的启动、暂停、恢复、取消和状态查询接口。
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from backend.service.kg_task_service import kg_task_manager, KGTaskStatus, KGTaskProgress
from backend.rag.storage.lightrag_storage import LightRAGStorage
from backend.rag.storage.milvus_storage import MilvusStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kg-task", tags=["知识图谱任务"])


class KGTaskStatusResponse(BaseModel):
    """知识图谱任务状态响应"""
    collection_id: str
    status: str
    total_chunks: int
    processed_chunks: int
    progress_percent: float
    error_message: Optional[str] = None


class KGTaskActionResponse(BaseModel):
    """知识图谱任务操作响应"""
    success: bool
    message: str
    collection_id: str


@router.get("/status/{collection_id}", response_model=KGTaskStatusResponse)
async def get_kg_task_status(collection_id: str):
    """获取知识图谱构建任务状态"""
    progress = kg_task_manager.get_task_status(collection_id)
    return KGTaskStatusResponse(
        collection_id=collection_id,
        status=progress.status.value,
        total_chunks=progress.total_chunks,
        processed_chunks=progress.processed_chunks,
        progress_percent=progress.progress_percent,
        error_message=progress.error_message
    )


@router.post("/start/{collection_id}", response_model=KGTaskActionResponse)
async def start_kg_task(collection_id: str):
    """启动知识图谱构建任务
    
    从 Milvus 获取该 collection 已存储的分块，然后开始向 LightRAG 插入构建知识图谱。
    """
    try:
        # 检查是否已有运行中的任务
        current_status = kg_task_manager.get_task_status(collection_id)
        if current_status.status == KGTaskStatus.RUNNING:
            return KGTaskActionResponse(
                success=False,
                message="任务已在运行中",
                collection_id=collection_id
            )
        
        
        # 获取 Milvus 中的分块数据
        
        # 获取所有文档分块（需要实现此方法）
        chunks = await get_chunks_from_milvus(collection_id)
        
        if not chunks:
            return KGTaskActionResponse(
                success=False,
                message="未找到可处理的分块数据",
                collection_id=collection_id
            )
        
        # 初始化任务
        start_index = 0
        if current_status.status == KGTaskStatus.PAUSED:
            # 从上次暂停的位置继续
            start_index = current_status.processed_chunks
        else:
            kg_task_manager.init_task(collection_id, len(chunks))
        
        kg_task_manager.start_task(collection_id)
        
        # 启动后台任务
        task = asyncio.create_task(
            run_kg_build_task(collection_id, chunks, start_index)
        )
        kg_task_manager.register_running_task(collection_id, task)
        
        return KGTaskActionResponse(
            success=True,
            message=f"知识图谱构建任务已启动，共 {len(chunks)} 个分块",
            collection_id=collection_id
        )
    except Exception as e:
        logger.error(f"启动知识图谱任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause/{collection_id}", response_model=KGTaskActionResponse)
async def pause_kg_task(collection_id: str):
    """暂停知识图谱构建任务"""
    success = kg_task_manager.pause_task(collection_id)
    if success:
        return KGTaskActionResponse(
            success=True,
            message="暂停信号已发送",
            collection_id=collection_id
        )
    else:
        return KGTaskActionResponse(
            success=False,
            message="任务不存在或无法暂停",
            collection_id=collection_id
        )


@router.post("/resume/{collection_id}", response_model=KGTaskActionResponse)
async def resume_kg_task(collection_id: str):
    """恢复知识图谱构建任务"""
    current_status = kg_task_manager.get_task_status(collection_id)
    if current_status.status != KGTaskStatus.PAUSED:
        return KGTaskActionResponse(
            success=False,
            message="任务不在暂停状态",
            collection_id=collection_id
        )
    
    # 重新启动任务
    return await start_kg_task(collection_id)


@router.post("/cancel/{collection_id}", response_model=KGTaskActionResponse)
async def cancel_kg_task(collection_id: str):
    """取消知识图谱构建任务"""
    success = kg_task_manager.cancel_task(collection_id)
    if success:
        return KGTaskActionResponse(
            success=True,
            message="取消信号已发送",
            collection_id=collection_id
        )
    else:
        return KGTaskActionResponse(
            success=False,
            message="任务不存在或无法取消",
            collection_id=collection_id
        )


async def get_chunks_from_milvus(collection_id: str) -> list:
    """从 Milvus 获取分块数据
    
    注意：这是一个简化实现，实际可能需要根据 Milvus 的存储结构调整。
    """
    try:
        import os
        from backend.agent.models import load_embeddings, register_embeddings_provider
        
        # 注册 embedding 提供商
        register_embeddings_provider(
            provider_name="dashscope",
            embeddings_model="openai",
            base_url=os.getenv("VECTOR_DASHSCOPE_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        )
        
        # 加载 embedding 模型
        embedding_model = os.getenv("VECTOR_DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4")
        embeddings = load_embeddings(
            f"dashscope:{embedding_model}",
            api_key=os.getenv("VECTOR_DASHSCOPE_API_KEY"),
            dimensions=int(os.getenv("EMBEDDING_DIM", 1024))
        )
        
        # 初始化 MilvusStorage
        milvus_storage = MilvusStorage(
            embedding_function=embeddings,
            collection_name=collection_id
        )
        
        # 获取所有分块的文本内容
        chunks = await milvus_storage.get_all_chunks()
        return [chunk.page_content for chunk in chunks] if chunks else []
    except Exception as e:
        logger.error(f"从 Milvus 获取分块失败: {e}")
        return []


async def run_kg_build_task(collection_id: str, chunks: list, start_index: int = 0):
    """运行知识图谱构建任务"""
    try:
        lightrag_storage = LightRAGStorage(workspace=collection_id)
        result = await lightrag_storage.insert_texts_with_control(
            texts=chunks,
            collection_id=collection_id,
            start_index=start_index
        )
        logger.info(f"知识图谱构建任务结果: {result}")
    except Exception as e:
        logger.error(f"知识图谱构建任务异常: {e}")
        kg_task_manager.mark_failed(collection_id, str(e))
    finally:
        kg_task_manager.unregister_running_task(collection_id)
