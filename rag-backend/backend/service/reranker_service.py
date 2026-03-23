#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reranker 服务层

使用 DashScope qwen3-rerank 模型对 RAG 检索结果进行语义相关性重排序和过滤。
"""

import os
import re
from typing import List, Optional
from dataclasses import dataclass
import dashscope
from dashscope import TextReRank

from backend.config.log import get_logger
from backend.service.chunk_filter import (
    normalize_title_front_matter_text,
    is_title_page_metadata_text,
)

logger = get_logger(__name__)


@dataclass
class RerankerConfig:
    """
    Reranker 配置类
    
    Attributes:
        model: Rerank 模型名称
        threshold: 相关性分数阈值，低于此值的文档将被过滤
        top_k: 返回的最大文档数量
        enabled: 是否启用 Reranker
    """
    model: str = "qwen3-rerank"
    threshold: float = 0.3
    top_k: int = 5
    enabled: bool = True


# 从环境变量读取默认配置
DEFAULT_RERANKER_CONFIG = RerankerConfig(
    model=os.getenv("RERANK_MODEL", "qwen3-rerank"),
    threshold=float(os.getenv("RERANK_THRESHOLD", "0.3")),
    top_k=int(os.getenv("RERANK_TOP_K", "5")),
    enabled=os.getenv("RERANK_ENABLED", "true").lower() == "true"
)


class RerankerService:
    """
    Reranker 服务
    
    使用 DashScope Text ReRank API 对检索结果进行语义相关性重排序。
    """
    
    def __init__(self, config: Optional[RerankerConfig] = None):
        """
        初始化 Reranker 服务
        
        Args:
            config: Reranker 配置，如果为 None 则使用默认配置
        """
        self.config = config or DEFAULT_RERANKER_CONFIG
        
        # 确保 DashScope API Key 已设置
        if not os.getenv("DASHSCOPE_API_KEY"):
            logger.warning("DASHSCOPE_API_KEY 未设置，Reranker 将无法工作")
        
        logger.info(
            f"RerankerService 初始化完成: model={self.config.model}, "
            f"threshold={self.config.threshold}, top_k={self.config.top_k}, "
            f"enabled={self.config.enabled}"
        )
    
    def rerank(
        self,
        query: str,
        documents: List,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> List:
        """
        对文档列表进行重排序和过滤
        
        Args:
            query: 用户查询问题
            documents: 待排序的文档列表（Document 或 RetrievedDocument 对象）
            top_k: 返回的最大文档数量（可选，默认使用配置值）
            threshold: 相关性阈值（可选，默认使用配置值）
            
        Returns:
            经过重排序和过滤的文档列表
        """
        if not self.config.enabled:
            logger.debug("Reranker 已禁用，返回原始文档")
            return documents
        
        if not documents:
            return documents
        
        if not query or not query.strip():
            logger.warning("查询为空，跳过 Rerank")
            return documents
        
        # 使用传入参数或默认配置
        effective_top_k = top_k if top_k is not None else self.config.top_k
        effective_threshold = threshold if threshold is not None else self.config.threshold
        
        # 提取文档内容
        doc_contents = []
        for doc in documents:
            content = self._get_document_content(doc)
            if content and content.strip():
                doc_contents.append(content)
        
        if not doc_contents:
            logger.warning("没有有效的文档内容，跳过 Rerank")
            return documents
        
        logger.info(f"开始 Rerank: query='{query[:50]}...', docs={len(doc_contents)}")
        
        try:
            # 调用 DashScope Text ReRank API
            response = TextReRank.call(
                model=self.config.model,
                query=query,
                documents=doc_contents,
                top_n=min(effective_top_k, len(doc_contents)),
                return_documents=False  # 不需要返回原始文档内容
            )
            
            if response.status_code != 200:
                logger.error(f"Rerank API 调用失败: {response.code} - {response.message}")
                return self._local_fallback_rerank(
                    query=query,
                    documents=documents,
                    top_k=effective_top_k
                )
            
            # 解析结果并过滤
            reranked_docs = []
            results = response.output.get("results", [])
            
            # 记录所有结果用于兜底（按分数排序）
            all_scored_docs = []
            
            for result in results:
                index = result.get("index")
                score = result.get("relevance_score", 0.0)
                
                if index is None or index >= len(documents):
                    continue
                
                doc = documents[index]
                all_scored_docs.append((doc, score, index))
                
                # 根据阈值过滤
                if score >= effective_threshold:
                    # 将相关性分数添加到 metadata
                    if hasattr(doc, 'metadata'):
                        doc.metadata["rerank_score"] = score
                    reranked_docs.append(doc)
                    logger.debug(f"保留文档 index={index}, score={score:.4f}")
                else:
                    logger.debug(f"过滤文档 index={index}, score={score:.4f} < threshold={effective_threshold}")
            
            # 兜底机制：如果所有文档都被过滤掉了，保留分数最高的 top-1 文档
            # 这样可以确保即使问题较泛泛，也不会完全没有内容可用于回答
            if not reranked_docs and all_scored_docs:
                # 按分数降序排序
                all_scored_docs.sort(key=lambda x: x[1], reverse=True)
                top_doc, top_score, top_index = all_scored_docs[0]
                
                if hasattr(top_doc, 'metadata'):
                    top_doc.metadata["rerank_score"] = top_score
                    top_doc.metadata["rerank_fallback"] = True  # 标记为兜底保留
                
                reranked_docs.append(top_doc)
                logger.info(
                    f"[Rerank兜底] 所有文档分数低于阈值{effective_threshold}，"
                    f"保留分数最高的文档 index={top_index}, score={top_score:.4f}"
                )
            
            logger.info(
                f"Rerank 完成: 输入={len(documents)}, 输出={len(reranked_docs)} "
                f"(过滤了 {len(documents) - len(reranked_docs)} 个低相关性文档)"
            )
            
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Rerank 失败: {e}")
            # API 失败时执行本地降权重排，避免标题页元数据片段排在首位
            return self._local_fallback_rerank(
                query=query,
                documents=documents,
                top_k=effective_top_k
            )
    
    def _get_document_content(self, doc) -> str:
        """获取文档的文本内容"""
        if hasattr(doc, 'page_content'):
            return doc.page_content or ""
        elif hasattr(doc, 'content'):
            return doc.content or ""
        elif isinstance(doc, dict):
            return doc.get('page_content', doc.get('content', ''))
        return str(doc)

    def _local_fallback_rerank(self, query: str, documents: List, top_k: int) -> List:
        """
        本地兜底重排（当 API Key 无效或接口失败时）。
        
        策略：
        - 用 query-token 重叠进行轻量打分
        - 对标题页元数据文本施加强惩罚，避免其成为 S1
        """
        if not documents:
            return documents
        
        query_tokens = set(re.findall(r'[\w\u4e00-\u9fff]+', (query or "").lower()))
        if not query_tokens:
            return documents[:top_k] if top_k > 0 else documents
        
        scored_docs = []
        for idx, doc in enumerate(documents):
            raw_content = self._get_document_content(doc)
            normalized_content = normalize_title_front_matter_text(raw_content, min_content_length=30)
            content_for_score = normalized_content or raw_content
            doc_tokens = set(re.findall(r'[\w\u4e00-\u9fff]+', content_for_score.lower()))
            
            overlap = len(query_tokens & doc_tokens) / max(len(query_tokens), 1)
            length_bonus = min(len(content_for_score) / 1200.0, 0.15)
            
            metadata_penalty = 0.0
            if is_title_page_metadata_text(raw_content):
                metadata_penalty -= 0.60
            elif normalized_content != raw_content:
                # 命中“标题页前缀清理”但仍有正文，降权但不过滤
                metadata_penalty -= 0.25
            
            score = overlap + length_bonus + metadata_penalty
            scored_docs.append((score, idx, doc))
        
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        selected = scored_docs[:top_k] if top_k > 0 else scored_docs
        
        reranked_docs = []
        for score, _, doc in selected:
            if hasattr(doc, 'metadata'):
                doc.metadata["rerank_score"] = score
                doc.metadata["rerank_fallback"] = True
                doc.metadata["rerank_source"] = "local_fallback"
            reranked_docs.append(doc)
        
        rank_debug = []
        for score, _, doc in selected[:3]:
            preview = self._get_document_content(doc)[:60].replace('\n', ' ')
            rank_debug.append(f"{score:.3f}:{preview}")
        
        logger.info(
            f"[Rerank本地兜底] API失败，执行本地降权重排: 输入={len(documents)}, 输出={len(reranked_docs)}, "
            f"top={rank_debug}"
        )
        return reranked_docs
    
    def update_config(self, **kwargs) -> None:
        """
        更新 Reranker 配置
        
        Args:
            **kwargs: 要更新的配置项
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"更新 Reranker 配置: {key}={value}")
            else:
                logger.warning(f"未知配置项: {key}")


# 全局单例
_reranker_service: Optional[RerankerService] = None


def get_reranker_service() -> RerankerService:
    """获取全局 RerankerService 单例"""
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = RerankerService()
    return _reranker_service
