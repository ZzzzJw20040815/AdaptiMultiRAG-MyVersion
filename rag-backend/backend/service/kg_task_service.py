"""知识图谱构建任务管理服务

提供知识图谱构建任务的启动、暂停、恢复、取消和状态查询功能。
任务状态持久化到数据库，支持后端重启后恢复进度。
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import threading

from backend.config.database import DatabaseFactory
from backend.model.knowledge_library import KnowledgeLibrary

logger = logging.getLogger(__name__)


class KGTaskStatus(str, Enum):
    """知识图谱任务状态"""
    PENDING = "pending"          # 待构建
    RUNNING = "running"          # 构建中
    PAUSED = "paused"            # 已暂停
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消


@dataclass
class KGTaskProgress:
    """知识图谱任务进度"""
    total_chunks: int = 0
    processed_chunks: int = 0
    status: KGTaskStatus = KGTaskStatus.PENDING
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    @property
    def progress_percent(self) -> float:
        if self.total_chunks == 0:
            return 0.0
        return (self.processed_chunks / self.total_chunks) * 100


class KGTaskManager:
    """知识图谱任务管理器
    
    管理所有知识图谱构建任务的状态和控制信号。
    使用 collection_id 作为任务标识。
    任务状态持久化到数据库，控制信号保存在内存中。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # 控制信号 (内存中): collection_id -> 是否应该暂停
        self._pause_signals: Dict[str, bool] = {}
        
        # 取消信号 (内存中): collection_id -> 是否应该取消
        self._cancel_signals: Dict[str, bool] = {}
        
        # 正在运行的任务 (内存中)
        self._running_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info("KGTaskManager 初始化完成 (数据库持久化模式)")
    
    def _get_library(self, collection_id: str) -> Optional[KnowledgeLibrary]:
        """从数据库获取知识库"""
        session = DatabaseFactory.create_session()
        try:
            library = session.query(KnowledgeLibrary).filter_by(
                collection_id=collection_id
            ).first()
            return library
        finally:
            session.close()
    
    def _update_library(self, collection_id: str, **updates) -> bool:
        """更新数据库中的知识库状态"""
        session = DatabaseFactory.create_session()
        try:
            library = session.query(KnowledgeLibrary).filter_by(
                collection_id=collection_id
            ).first()
            if not library:
                return False
            
            for key, value in updates.items():
                if hasattr(library, key):
                    setattr(library, key, value)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"更新知识库状态失败: {e}")
            return False
        finally:
            session.close()
    
    def get_task_status(self, collection_id: str) -> KGTaskProgress:
        """获取任务状态 (从数据库读取)"""
        library = self._get_library(collection_id)
        if not library:
            return KGTaskProgress(status=KGTaskStatus.PENDING)
        
        return KGTaskProgress(
            total_chunks=library.kg_total_chunks or 0,
            processed_chunks=library.kg_processed_chunks or 0,
            status=KGTaskStatus(library.kg_status) if library.kg_status else KGTaskStatus.PENDING,
            error_message=library.kg_error_message
        )
    
    def init_task(self, collection_id: str, total_chunks: int) -> None:
        """初始化任务 (写入数据库)"""
        self._update_library(
            collection_id,
            kg_status=KGTaskStatus.PENDING.value,
            kg_total_chunks=total_chunks,
            kg_processed_chunks=0,
            kg_error_message=None
        )
        self._pause_signals[collection_id] = False
        self._cancel_signals[collection_id] = False
        logger.info(f"任务 {collection_id} 初始化: {total_chunks} 个分块待处理")
    
    def start_task(self, collection_id: str) -> None:
        """标记任务开始"""
        self._update_library(
            collection_id,
            kg_status=KGTaskStatus.RUNNING.value
        )
        self._pause_signals[collection_id] = False
        self._cancel_signals[collection_id] = False
        logger.info(f"任务 {collection_id} 开始")
    
    def update_progress(self, collection_id: str, processed_chunks: int) -> None:
        """更新进度 (写入数据库)"""
        self._update_library(
            collection_id,
            kg_processed_chunks=processed_chunks
        )
        status = self.get_task_status(collection_id)
        logger.info(f"任务 {collection_id} 进度: {processed_chunks}/{status.total_chunks}")
    
    def pause_task(self, collection_id: str) -> bool:
        """发送暂停信号"""
        status = self.get_task_status(collection_id)
        if status.status != KGTaskStatus.RUNNING:
            return False
        self._pause_signals[collection_id] = True
        logger.info(f"任务 {collection_id} 收到暂停信号")
        return True
    
    def resume_task(self, collection_id: str) -> bool:
        """发送恢复信号"""
        status = self.get_task_status(collection_id)
        if status.status != KGTaskStatus.PAUSED:
            return False
        self._pause_signals[collection_id] = False
        self._update_library(
            collection_id,
            kg_status=KGTaskStatus.RUNNING.value
        )
        logger.info(f"任务 {collection_id} 恢复运行")
        return True
    
    def cancel_task(self, collection_id: str) -> bool:
        """发送取消信号"""
        status = self.get_task_status(collection_id)
        if status.status in (KGTaskStatus.COMPLETED, KGTaskStatus.CANCELLED):
            return False
        self._cancel_signals[collection_id] = True
        logger.info(f"任务 {collection_id} 收到取消信号")
        return True
    
    def should_pause(self, collection_id: str) -> bool:
        """检查是否应该暂停"""
        return self._pause_signals.get(collection_id, False)
    
    def should_cancel(self, collection_id: str) -> bool:
        """检查是否应该取消"""
        return self._cancel_signals.get(collection_id, False)
    
    def mark_paused(self, collection_id: str) -> None:
        """标记任务为已暂停 (写入数据库)"""
        self._update_library(
            collection_id,
            kg_status=KGTaskStatus.PAUSED.value
        )
        logger.info(f"任务 {collection_id} 已暂停")
    
    def mark_completed(self, collection_id: str) -> None:
        """标记任务完成 (写入数据库)"""
        self._update_library(
            collection_id,
            kg_status=KGTaskStatus.COMPLETED.value
        )
        logger.info(f"任务 {collection_id} 已完成")
    
    def mark_cancelled(self, collection_id: str) -> None:
        """标记任务取消 (写入数据库)"""
        self._update_library(
            collection_id,
            kg_status=KGTaskStatus.CANCELLED.value
        )
        logger.info(f"任务 {collection_id} 已取消")
    
    def mark_failed(self, collection_id: str, error: str) -> None:
        """标记任务失败 (写入数据库)"""
        self._update_library(
            collection_id,
            kg_status=KGTaskStatus.FAILED.value,
            kg_error_message=error
        )
        logger.error(f"任务 {collection_id} 失败: {error}")
    
    def register_running_task(self, collection_id: str, task: asyncio.Task) -> None:
        """注册运行中的任务"""
        self._running_tasks[collection_id] = task
    
    def unregister_running_task(self, collection_id: str) -> None:
        """取消注册运行中的任务"""
        self._running_tasks.pop(collection_id, None)


# 全局任务管理器实例
kg_task_manager = KGTaskManager()
