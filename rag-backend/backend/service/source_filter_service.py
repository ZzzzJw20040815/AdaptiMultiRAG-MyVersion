#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态白名单来源过滤服务 (P2 改进版)

核心改进：基于当前知识库中实际存在的文档进行过滤，
而不是使用硬编码的已知实体列表。

解决的问题：
- 避免技术名词（如 ResNet）被误识别为文档名
- 只有当用户意图与实际库存匹配时才生成过滤器
"""

import os
import re
from typing import List, Optional, Tuple, Dict, Set
from dataclasses import dataclass
from functools import lru_cache

from backend.config.log import get_logger
from backend.config.database import DatabaseFactory
from backend.model.knowledge_library import KnowledgeLibrary, KnowledgeDocument

logger = get_logger(__name__)


@dataclass
class SourceFilterConfig:
    """
    来源感知过滤配置
    
    Attributes:
        enabled: 是否启用来源过滤
        fallback_to_global: 无匹配时是否回退到全局搜索
    """
    enabled: bool = True
    fallback_to_global: bool = True  # 无匹配时进行全局搜索


# ==================== 步骤 A: 获取动态白名单 ====================

@dataclass
class DocInfo:
    """文档信息：包含名称和 URL"""
    name: str  # 用户填写的友好名称（用于匹配）
    url: str   # 实际的 URL（Milvus 中存储的 document_name）


def get_active_doc_info(collection_id: str) -> List[DocInfo]:
    """
    获取知识库中所有文档的信息（名称 + URL）
    
    注意：Milvus 入库时使用的是 URL 作为 document_name，
    但用户查询时用的是友好名称。所以我们需要两者的映射。
    
    Args:
        collection_id: 知识库的 collection_id
        
    Returns:
        DocInfo 列表，包含 name（匹配用）和 url（filter 用）
    """
    if not collection_id:
        logger.warning("collection_id 为空，无法获取文档白名单")
        return []
    
    logger.info(f"[P2白名单] 开始查询文档, collection_id = {collection_id}")
    
    try:
        session = DatabaseFactory.create_session()
        try:
            # 先检查 KnowledgeLibrary 是否存在
            library = session.query(KnowledgeLibrary).filter(
                KnowledgeLibrary.collection_id == collection_id
            ).first()
            
            if not library:
                logger.warning(f"[P2白名单] 未找到 collection_id={collection_id} 的知识库")
                all_libs = session.query(KnowledgeLibrary.id, KnowledgeLibrary.collection_id, KnowledgeLibrary.title).limit(5).all()
                logger.info(f"[P2白名单] 数据库中存在的知识库（前5个）: {[(l.id, l.collection_id, l.title) for l in all_libs]}")
                return []
            
            logger.info(f"[P2白名单] 找到知识库: id={library.id}, title={library.title}")
            
            # 查询该知识库下的所有文档
            documents = session.query(KnowledgeDocument).filter(
                KnowledgeDocument.library_id == library.id
            ).all()
            
            logger.info(f"[P2白名单] 查询到 {len(documents)} 个文档")
            
            # 构建 DocInfo 列表
            doc_infos = []
            for doc in documents:
                if doc.name:
                    # URL 可能为空，如果没有则用名称
                    url = doc.url or doc.name
                    doc_infos.append(DocInfo(name=doc.name, url=url))
                    logger.debug(f"  - 文档: name={doc.name}, url={url}")
            
            logger.info(f"[P2白名单] 获取到 {len(doc_infos)} 个文档信息")
            return doc_infos
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"[P2白名单] 获取文档白名单失败: {e}", exc_info=True)
        return []


# 兼容旧接口
def get_active_doc_names(collection_id: str) -> List[str]:
    """获取文档名称列表（兼容旧接口）"""
    doc_infos = get_active_doc_info(collection_id)
    return [info.name for info in doc_infos]


def get_url_to_name_mapping(collection_id: str) -> Dict[str, str]:
    """
    获取 URL 到文档名称的映射
    
    用途：在生成答案时，将 Milvus 中存储的 URL 转换为用户填写的友好名称
    
    Args:
        collection_id: 知识库 collection_id
        
    Returns:
        {url: name} 字典，例如 {"https://arxiv.org/...": "LLaVA论文"}
    """
    doc_infos = get_active_doc_info(collection_id)
    return {info.url: info.name for info in doc_infos}


# ==================== 步骤 B: 从查询中提取候选实体 ====================

# 分词用的正则：提取中英文词语
_TOKEN_PATTERN = re.compile(r'[a-zA-Z][\w\-]*|[\u4e00-\u9fff]+')

# 通用词黑名单：这些词太常见，不应该作为匹配依据
COMMON_WORD_BLACKLIST = {
    # 学术论文中常见的通用词
    'the', 'a', 'an', 'of', 'in', 'on', 'for', 'with', 'and', 'or', 'to', 'from',
    'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'this', 'that', 'these', 'those', 'it', 'its',
    'how', 'what', 'which', 'where', 'when', 'why', 'who',
    # 学术领域通用词（容易匹配多篇论文）
    'learning', 'robot', 'robotics', 'model', 'models', 'method', 'methods',
    'approach', 'system', 'systems', 'neural', 'network', 'networks',
    'deep', 'machine', 'artificial', 'intelligence', 'ai', 'ml',
    'training', 'data', 'dataset', 'language', 'visual', 'vision',
    'image', 'images', 'video', 'videos', 'text', 'paper', 'papers',
    'study', 'research', 'analysis', 'based', 'using', 'via',
    'new', 'novel', 'improved', 'efficient', 'effective', 'correction',
    'corrections', 'verbal', 'interactive', 'improving', 'fly',
    # 中文通用词
    '论文', '研究', '方法', '模型', '系统', '学习', '机器', '网络',
    '这篇', '什么', '内容', '主要', '介绍', '讲了',
}


def extract_candidates_from_query(query: str) -> List[str]:
    """
    从用户查询中提取可能是文档标题的候选词/短语
    
    优化策略：
    1. 提取连续的多词短语（更精确匹配）
    2. 过滤掉通用词
    
    Args:
        query: 用户查询
        
    Returns:
        候选词列表
    """
    if not query:
        return []
    
    candidates = []
    
    # 策略1: 提取完整的英文短语（2-6个词的连续序列）
    # 例如 "Improving On-the-Fly" 或 "Interactive Robot Learning"
    words = query.split()
    for length in range(min(6, len(words)), 1, -1):  # 从长到短
        for i in range(len(words) - length + 1):
            phrase = ' '.join(words[i:i+length])
            # 过滤掉纯中文短语和太短的短语
            if len(phrase) >= 8 and re.search(r'[a-zA-Z]', phrase):
                candidates.append(phrase)
    
    # 策略2: 提取单个有意义的词（过滤通用词）
    tokens = _TOKEN_PATTERN.findall(query)
    for token in tokens:
        token_lower = token.lower()
        # 长度至少4，且不在黑名单中
        if len(token) >= 4 and token_lower not in COMMON_WORD_BLACKLIST:
            candidates.append(token)
    
    # 去重并保持顺序
    seen = set()
    unique_candidates = []
    for c in candidates:
        c_lower = c.lower()
        if c_lower not in seen:
            seen.add(c_lower)
            unique_candidates.append(c)
    
    logger.debug(f"从查询中提取候选词: {unique_candidates}")
    return unique_candidates


# ==================== 步骤 C: 白名单校验与过滤器构建 ====================

def match_candidate_to_whitelist(
    candidate: str,
    whitelist: List[str]
) -> Optional[str]:
    """
    检查候选词是否匹配白名单中的任一文档名
    
    Args:
        candidate: 候选词（小写）
        whitelist: 文档名白名单
        
    Returns:
        匹配到的文档名，未匹配返回 None
    """
    candidate_lower = candidate.lower()
    
    for doc_name in whitelist:
        doc_name_lower = doc_name.lower()
        
        # 模糊匹配：候选词出现在文档名中
        if candidate_lower in doc_name_lower:
            return doc_name
    
    return None


def build_source_filter(
    query: str,
    collection_id: str,
    config: Optional[SourceFilterConfig] = None
) -> Optional[str]:
    """
    构建动态白名单来源过滤器（核心方法）
    
    流程：
    1. 获取当前知识库的文档信息（名称 + URL）
    2. 从查询中提取候选词
    3. 将候选词与文档名称校验
    4. 使用匹配文档的 URL 构建 Milvus filter
    
    注意：Milvus 入库时使用 URL 作为 document_name，
    所以 filter 必须用 URL，而不是用户填写的名称。
    
    Args:
        query: 用户查询
        collection_id: 知识库 collection_id
        config: 过滤配置
        
    Returns:
        Milvus filter 表达式
        如果无匹配或禁用，返回 None（进行全局搜索）
    """
    config = config or SourceFilterConfig(
        enabled=os.getenv("SOURCE_FILTER_ENABLED", "true").lower() == "true",
        fallback_to_global=os.getenv("SOURCE_FILTER_FALLBACK_GLOBAL", "true").lower() == "true"
    )
    
    if not config.enabled:
        logger.debug("来源过滤已禁用")
        return None
    
    logger.info(f"[P2动态白名单] 开始构建来源过滤器, collection_id={collection_id}")
    
    # 步骤 A: 获取文档信息（名称 + URL）
    doc_infos = get_active_doc_info(collection_id)
    if not doc_infos:
        logger.info("当前知识库无文档，跳过来源过滤")
        return None
    
    # 打印所有文档信息用于调试
    for info in doc_infos:
        logger.info(f"[P2白名单] 文档: name='{info.name}', url='{info.url}'")
    
    # 步骤 B: 提取候选词
    candidates = extract_candidates_from_query(query)
    if not candidates:
        logger.info("未从查询中提取到候选词，跳过来源过滤")
        return None
    
    # 步骤 C: 白名单校验 - 匹配名称，但记录 URL
    matched_urls: Set[str] = set()
    matched_names: Set[str] = set()  # 使用 Set 去重
    unmatched_candidates: List[str] = []
    
    for candidate in candidates:
        candidate_lower = candidate.lower()
        matched = False
        
        for doc_info in doc_infos:
            # 用名称匹配
            if candidate_lower in doc_info.name.lower():
                matched_urls.add(doc_info.url)  # 记录 URL
                matched_names.add(doc_info.name)  # 记录名称（自动去重）
                logger.debug(f"✓ 候选词 '{candidate}' 匹配到文档 '{doc_info.name}' (url={doc_info.url})")
                matched = True
                break
        
        if not matched:
            unmatched_candidates.append(candidate)
            logger.debug(f"✗ 候选词 '{candidate}' 未匹配任何文档（视为普通查询词）")
    
    # 判断是否有匹配
    if not matched_urls:
        logger.info(f"所有候选词 {candidates} 均未匹配白名单，进行全局搜索")
        return None
    
    # 构建 Milvus filter 表达式 - 使用 URL！
    url_list = list(matched_urls)
    if len(url_list) == 1:
        filter_expr = f'document_name == "{url_list[0]}"'
    else:
        # 多个文档用 in 操作符
        url_str = '", "'.join(url_list)
        filter_expr = f'document_name in ["{url_str}"]'
    
    # 简化日志输出：只显示去重后的文档名，候选词数量统计
    logger.info(
        f"[P2动态白名单] 构建 filter 成功:\n"
        f"  filter (用 URL): {filter_expr}\n"
        f"  匹配文档 ({len(matched_names)}篇): {list(matched_names)}\n"
        f"  候选词统计: 共{len(candidates)}个, 匹配{len(candidates) - len(unmatched_candidates)}个, 未匹配{len(unmatched_candidates)}个"
    )
    
    return filter_expr


# ==================== 兼容旧版的简单实体提取 ====================

# 常见的学术模型/系统名称（保留作为备用）
KNOWN_ENTITIES = [
    "llava", "clip", "blip", "blip-2", "flamingo", "gpt-4", "gpt-4v",
    "gemini", "palm", "qwen-vl", "cogvlm", "internvl",
    "llama", "vicuna", "alpaca", "chatgpt", "bert", "roberta", "t5",
    "vit", "resnet", "efficientnet", "swin", "dino", "transformer",
]

_ENTITY_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(e) for e in KNOWN_ENTITIES) + r')\b',
    re.IGNORECASE
)


def extract_entities_simple(question: str) -> List[str]:
    """
    使用简单规则从问题中提取主实体（保留作为备用）
    """
    if not question:
        return []
    matches = _ENTITY_PATTERN.findall(question)
    return list(set(m.lower() for m in matches))


def is_simple_question(question: str) -> bool:
    """
    判断问题是否为简单事实性问题（P4 优化）
    """
    if not question:
        return False
    
    question_lower = question.lower()
    
    # 复杂问题关键词
    complex_keywords = [
        "比较", "对比", "区别", "不同", "相同",
        "优缺点", "优势", "劣势", "分析",
        "为什么", "如何实现", "原理是什么",
        "综合", "总结", "评价",
        "compare", "contrast", "difference", "analyze",
    ]
    
    for keyword in complex_keywords:
        if keyword in question_lower:
            return False
    
    # 问题较短通常是简单问题
    if len(question) < 50:
        return True
    
    return False


# ==================== 全局服务 ====================

class SourceFilterService:
    """来源感知过滤服务（兼容旧版接口）"""
    
    def __init__(self, config: Optional[SourceFilterConfig] = None):
        self.config = config or SourceFilterConfig()
        logger.info(f"SourceFilterService 初始化完成: enabled={self.config.enabled}")
    
    def build_filter(self, query: str, collection_id: str) -> Optional[str]:
        """构建来源过滤器"""
        return build_source_filter(query, collection_id, self.config)


_source_filter_service: Optional[SourceFilterService] = None


def get_source_filter_service() -> SourceFilterService:
    """获取全局 SourceFilterService 单例"""
    global _source_filter_service
    if _source_filter_service is None:
        _source_filter_service = SourceFilterService()
    return _source_filter_service
