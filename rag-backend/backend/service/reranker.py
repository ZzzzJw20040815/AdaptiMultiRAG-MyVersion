#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reranker 服务 (PR-9)

提供检索结果的重排序和相关性过滤功能:
- LLM-based 相关性评分
- 相关性阈值过滤 (relevance gate)
- 交叉编码器重排序 (可选)
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from backend.config.log import get_logger

logger = get_logger(__name__)


@dataclass
class RankedDocument:
    """重排序后的文档"""
    page_content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    relevance_score: float = 0.0       # 相关性分数 (0-1)
    relevance_reason: str = ""         # 相关性判断理由
    is_relevant: bool = True           # 是否通过相关性门控
    original_rank: int = 0             # 原始排名


# LLM 相关性评分 Prompt
RELEVANCE_SCORING_PROMPT = """你是一个专业的文档相关性评估助手。请评估以下检索到的文档片段与用户问题的相关性。

## 用户问题
{question}

## 文档片段
{document}

## 评估标准

1. **高度相关 (0.8-1.0)**: 文档直接回答了问题，包含关键信息
2. **中度相关 (0.5-0.7)**: 文档包含相关信息，但不完全匹配
3. **低度相关 (0.2-0.4)**: 文档仅涉及相关主题，无直接答案
4. **不相关 (0.0-0.1)**: 文档与问题无关

## 输出格式

请以 JSON 格式返回评估结果：
```json
{{
  "relevance_score": 0.85,
  "is_relevant": true,
  "reason": "该文档包含...的详细解释，直接回答了用户关于...的问题"
}}
```

注意：
- relevance_score 必须在 0-1 之间
- is_relevant 为 true 表示相关性 >= 0.5
- 只返回 JSON，不要添加其他文字
"""


class Reranker:
    """
    Reranker 重排序器
    
    支持多种重排序策略:
    1. LLM-based: 使用大语言模型评分
    2. Cross-encoder: 使用交叉编码器 (需额外模型)
    3. Hybrid: 结合多种方法
    """
    
    # 默认相关性阈值
    DEFAULT_RELEVANCE_THRESHOLD = 0.5
    
    # 最大批处理文档数
    MAX_BATCH_SIZE = 10
    
    def __init__(
        self,
        llm = None,
        relevance_threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
        max_docs: int = 5
    ):
        """
        初始化 Reranker
        
        Args:
            llm: LangChain 聊天模型实例
            relevance_threshold: 相关性阈值 (0-1)
            max_docs: 最终返回的最大文档数
        """
        self.llm = llm
        self.relevance_threshold = relevance_threshold
        self.max_docs = max_docs
        self.logger = logger
    
    async def rerank(
        self,
        question: str,
        documents: List[Any],
        use_llm: bool = True
    ) -> List[RankedDocument]:
        """
        对检索结果进行重排序
        
        Args:
            question: 用户问题
            documents: 检索到的文档列表
            use_llm: 是否使用 LLM 评分
            
        Returns:
            重排序后的文档列表
        """
        if not documents:
            return []
        
        self.logger.info(f"开始重排序 {len(documents)} 个文档")
        
        # 转换为 RankedDocument
        ranked_docs = []
        for idx, doc in enumerate(documents):
            content = getattr(doc, 'page_content', None) or doc.get('page_content', '') if isinstance(doc, dict) else str(doc)
            metadata = getattr(doc, 'metadata', None) or doc.get('metadata', {}) if isinstance(doc, dict) else {}
            
            ranked_docs.append(RankedDocument(
                page_content=content,
                metadata=metadata,
                original_rank=idx
            ))
        
        if use_llm and self.llm:
            # 使用 LLM 评分
            ranked_docs = await self._llm_score(question, ranked_docs)
        else:
            # 使用简单的关键词匹配评分
            ranked_docs = self._keyword_score(question, ranked_docs)
        
        # 过滤低相关性文档
        filtered_docs = [
            doc for doc in ranked_docs 
            if doc.is_relevant and doc.relevance_score >= self.relevance_threshold
        ]
        
        self.logger.info(
            f"重排序完成: {len(documents)} -> {len(filtered_docs)} 个文档 "
            f"(阈值: {self.relevance_threshold})"
        )
        
        # 按相关性分数排序
        filtered_docs.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # 限制返回数量
        return filtered_docs[:self.max_docs]
    
    async def _llm_score(
        self,
        question: str,
        documents: List[RankedDocument]
    ) -> List[RankedDocument]:
        """使用 LLM 对文档进行相关性评分"""
        
        for doc in documents[:self.MAX_BATCH_SIZE]:
            try:
                prompt = RELEVANCE_SCORING_PROMPT.format(
                    question=question,
                    document=doc.page_content[:1500]  # 限制文档长度
                )
                
                response = await self.llm.ainvoke(prompt)
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # 解析 JSON 响应
                score_data = self._parse_score_response(response_text)
                
                doc.relevance_score = score_data.get('relevance_score', 0.5)
                doc.is_relevant = score_data.get('is_relevant', True)
                doc.relevance_reason = score_data.get('reason', '')
                
            except Exception as e:
                self.logger.warning(f"LLM 评分失败: {e}")
                # 失败时使用默认分数
                doc.relevance_score = 0.5
                doc.is_relevant = True
        
        return documents
    
    def _keyword_score(
        self,
        question: str,
        documents: List[RankedDocument]
    ) -> List[RankedDocument]:
        """简单的关键词匹配评分 (作为 LLM 的备用)"""
        
        # 提取问题关键词
        keywords = set(question.lower().split())
        
        for doc in documents:
            content_lower = doc.page_content.lower()
            
            # 计算关键词匹配率
            matched = sum(1 for kw in keywords if kw in content_lower)
            score = matched / len(keywords) if keywords else 0.5
            
            doc.relevance_score = min(score + 0.3, 1.0)  # 基础分
            doc.is_relevant = doc.relevance_score >= self.relevance_threshold
            doc.relevance_reason = f"关键词匹配率: {matched}/{len(keywords)}"
        
        return documents
    
    def _parse_score_response(self, response_text: str) -> Dict[str, Any]:
        """解析 LLM 评分响应"""
        
        try:
            # 尝试直接解析 JSON
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            pass
        
        # 尝试从 code block 中提取
        json_match = re.search(r'```json\s*\n?(.*?)\n?```', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass
        
        # 尝试提取 {} 包围的内容
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # 默认返回
        return {'relevance_score': 0.5, 'is_relevant': True, 'reason': '解析失败'}


async def rerank_documents(
    question: str,
    documents: List[Any],
    llm = None,
    relevance_threshold: float = 0.5,
    max_docs: int = 5,
    use_llm: bool = True
) -> List[RankedDocument]:
    """
    便捷函数：对文档进行重排序和过滤
    
    Args:
        question: 用户问题
        documents: 检索到的文档列表
        llm: LangChain 聊天模型
        relevance_threshold: 相关性阈值
        max_docs: 最大返回文档数
        use_llm: 是否使用 LLM 评分
        
    Returns:
        重排序后的文档列表
    """
    reranker = Reranker(
        llm=llm,
        relevance_threshold=relevance_threshold,
        max_docs=max_docs
    )
    
    return await reranker.rerank(question, documents, use_llm=use_llm)


def filter_by_relevance(
    documents: List[Any],
    threshold: float = 0.5
) -> List[Any]:
    """
    简单的相关性过滤（基于已有分数）
    
    Args:
        documents: 带有 relevance_score 的文档列表
        threshold: 相关性阈值
        
    Returns:
        过滤后的文档列表
    """
    filtered = []
    
    for doc in documents:
        score = None
        
        # 尝试从不同位置获取分数
        if isinstance(doc, RankedDocument):
            score = doc.relevance_score
        elif hasattr(doc, 'metadata'):
            score = doc.metadata.get('relevance_score') or doc.metadata.get('score')
        elif isinstance(doc, dict):
            score = doc.get('relevance_score') or doc.get('metadata', {}).get('score')
        
        if score is not None and score >= threshold:
            filtered.append(doc)
        elif score is None:
            # 没有分数的文档默认保留
            filtered.append(doc)
    
    return filtered
