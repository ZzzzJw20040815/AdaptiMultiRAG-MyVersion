#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图谱去噪/过滤服务 (PR-10)

提供知识图谱结果的质量过滤功能:
- 实体质量评分
- 边（关系）质量评分
- 噪声实体过滤
- 冗余实体合并
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import Counter

from backend.config.log import get_logger

logger = get_logger(__name__)


@dataclass
class GraphEntity:
    """图谱实体"""
    name: str
    entity_type: str = ""
    description: str = ""
    source_docs: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    is_noise: bool = False
    merged_from: List[str] = field(default_factory=list)


@dataclass
class GraphRelation:
    """图谱关系（边）"""
    source: str
    target: str
    relation_type: str
    description: str = ""
    source_docs: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    is_noise: bool = False


# 噪声实体模式（正则表达式）
NOISE_PATTERNS = [
    # 纯数字
    r'^[\d\.\,\%]+$',
    # 纯标点
    r'^[\s\.,;:!?\-\—\–\'\"\(\)\[\]\{\}]+$',
    # 太短的实体（通常 < 2 字符）
    r'^.{0,1}$',
    # 常见的无意义词
    r'^(the|a|an|this|that|these|those|it|is|are|was|were|be|been|being|have|has|had)$',
    # 中文无意义词
    r'^(的|是|在|有|和|与|及|或|等|了|着|过|个|些|用|被|把|对|将|从|到|为|也|还|就|而|但|可|能|要|会|如|如果|因为|所以|然后|因此)$',
    # 编号引用 [1] [2]
    r'^\[\d+\]$',
    # HTML/XML 标签残留
    r'^<[^>]*>$',
    # URL 残留
    r'^(http|https|www\.)\S*$',
    # 论文作者格式 (如 "Smith, J." / "Chen, X. Y.")
    r'^[A-Z][a-z]+,\s*(?:[A-Z]\.?\s*){1,3}$',
    # 论文作者格式 (如 "J. Smith")
    r'^[A-Z]\.\s*[A-Z][a-z]+$',
    # 孤立的文件扩展名
    r'^\.(pdf|doc|docx|txt|md)$',
]

# 低质量关系类型
LOW_QUALITY_RELATIONS = [
    'unknown', 'undefined', 'related', 'related to', 'associated', 
    'associated with', 'connected', 'linked', '相关', '关联', '有关'
]


class GraphFilter:
    """
    图谱过滤器
    
    提供实体和关系的质量评估与过滤功能
    """
    
    # 最小实体名称长度
    MIN_ENTITY_LENGTH = 2
    
    # 质量分数阈值
    DEFAULT_ENTITY_THRESHOLD = 0.3
    DEFAULT_RELATION_THRESHOLD = 0.3
    
    def __init__(
        self,
        entity_threshold: float = DEFAULT_ENTITY_THRESHOLD,
        relation_threshold: float = DEFAULT_RELATION_THRESHOLD,
        min_entity_length: int = MIN_ENTITY_LENGTH
    ):
        """
        初始化图谱过滤器
        
        Args:
            entity_threshold: 实体质量阈值
            relation_threshold: 关系质量阈值
            min_entity_length: 最小实体名称长度
        """
        self.entity_threshold = entity_threshold
        self.relation_threshold = relation_threshold
        self.min_entity_length = min_entity_length
        
        # 编译噪声模式
        self.noise_patterns = [re.compile(p, re.IGNORECASE) for p in NOISE_PATTERNS]
    
    def filter_entities(self, entities: List[Dict[str, Any]]) -> List[GraphEntity]:
        """
        过滤实体列表
        
        Args:
            entities: 原始实体列表
            
        Returns:
            过滤后的实体列表
        """
        if not entities:
            return []
        
        logger.info(f"开始过滤 {len(entities)} 个实体")
        
        # 转换并评分
        scored_entities = []
        for entity_data in entities:
            entity = self._convert_to_entity(entity_data)
            entity.quality_score = self._score_entity(entity)
            entity.is_noise = self._is_noise_entity(entity)
            scored_entities.append(entity)
        
        # 过滤噪声
        filtered = [
            e for e in scored_entities 
            if not e.is_noise and e.quality_score >= self.entity_threshold
        ]
        
        # 合并相似实体
        merged = self._merge_similar_entities(filtered)
        
        logger.info(f"实体过滤完成: {len(entities)} -> {len(merged)} (移除 {len(entities) - len(merged)})")
        
        return merged
    
    def filter_relations(
        self, 
        relations: List[Dict[str, Any]],
        valid_entities: Optional[Set[str]] = None
    ) -> List[GraphRelation]:
        """
        过滤关系列表
        
        Args:
            relations: 原始关系列表
            valid_entities: 有效的实体名称集合（用于过滤孤立边）
            
        Returns:
            过滤后的关系列表
        """
        if not relations:
            return []
        
        logger.info(f"开始过滤 {len(relations)} 条关系")
        
        scored_relations = []
        for rel_data in relations:
            relation = self._convert_to_relation(rel_data)
            relation.quality_score = self._score_relation(relation)
            relation.is_noise = self._is_noise_relation(relation, valid_entities)
            scored_relations.append(relation)
        
        filtered = [
            r for r in scored_relations
            if not r.is_noise and r.quality_score >= self.relation_threshold
        ]
        
        logger.info(f"关系过滤完成: {len(relations)} -> {len(filtered)}")
        
        return filtered
    
    def _convert_to_entity(self, data: Dict[str, Any]) -> GraphEntity:
        """将字典转换为 GraphEntity"""
        if isinstance(data, GraphEntity):
            return data
        
        return GraphEntity(
            name=data.get('name', data.get('entity_name', str(data))),
            entity_type=data.get('type', data.get('entity_type', '')),
            description=data.get('description', ''),
            source_docs=data.get('source_docs', data.get('sources', []))
        )
    
    def _convert_to_relation(self, data: Dict[str, Any]) -> GraphRelation:
        """将字典转换为 GraphRelation"""
        if isinstance(data, GraphRelation):
            return data
        
        return GraphRelation(
            source=data.get('source', data.get('src', '')),
            target=data.get('target', data.get('dst', '')),
            relation_type=data.get('relation_type', data.get('type', '')),
            description=data.get('description', ''),
            source_docs=data.get('source_docs', [])
        )
    
    def _score_entity(self, entity: GraphEntity) -> float:
        """
        计算实体质量分数
        
        评分维度:
        - 名称长度
        - 是否有描述
        - 来源文档数量
        - 实体类型是否明确
        """
        score = 0.0
        
        # 名称长度 (0-0.3)
        name_len = len(entity.name)
        if name_len >= 5:
            score += 0.3
        elif name_len >= 3:
            score += 0.2
        elif name_len >= 2:
            score += 0.1
        
        # 有描述 (0-0.3)
        if entity.description and len(entity.description) > 10:
            score += 0.3
        elif entity.description:
            score += 0.15
        
        # 来源文档数量 (0-0.2)
        doc_count = len(entity.source_docs)
        if doc_count >= 3:
            score += 0.2
        elif doc_count >= 1:
            score += 0.1
        
        # 实体类型 (0-0.2)
        if entity.entity_type and entity.entity_type.lower() not in ['unknown', 'other', '其他']:
            score += 0.2
        
        return min(score, 1.0)
    
    def _score_relation(self, relation: GraphRelation) -> float:
        """
        计算关系质量分数
        
        评分维度:
        - 源和目标是否有效
        - 关系类型是否明确
        - 是否有描述
        """
        score = 0.0
        
        # 源和目标有效 (0-0.4)
        if relation.source and len(relation.source) >= 2:
            score += 0.2
        if relation.target and len(relation.target) >= 2:
            score += 0.2
        
        # 关系类型明确 (0-0.4)
        rel_type = relation.relation_type.lower() if relation.relation_type else ''
        if rel_type and rel_type not in LOW_QUALITY_RELATIONS:
            score += 0.4
        elif rel_type:
            score += 0.1
        
        # 有描述 (0-0.2)
        if relation.description and len(relation.description) > 5:
            score += 0.2
        
        return min(score, 1.0)
    
    def _is_noise_entity(self, entity: GraphEntity) -> bool:
        """判断实体是否为噪声"""
        name = entity.name.strip()
        
        # 长度检查
        if len(name) < self.min_entity_length:
            return True
        
        # 模式匹配
        for pattern in self.noise_patterns:
            if pattern.match(name):
                return True
        
        return False
    
    def _is_noise_relation(
        self, 
        relation: GraphRelation,
        valid_entities: Optional[Set[str]] = None
    ) -> bool:
        """判断关系是否为噪声"""
        
        # 自环检查
        if relation.source == relation.target:
            return True
        
        # 源或目标为空
        if not relation.source or not relation.target:
            return True
        
        # 如果提供了有效实体集，检查边的端点
        if valid_entities:
            if relation.source not in valid_entities or relation.target not in valid_entities:
                return True
        
        return False
    
    def _merge_similar_entities(
        self, 
        entities: List[GraphEntity]
    ) -> List[GraphEntity]:
        """
        合并相似实体
        
        规则:
        - 名称完全相同（忽略大小写）合并
        - 保留分数最高的那个
        """
        if not entities:
            return []
        
        # 按名称分组
        name_groups: Dict[str, List[GraphEntity]] = {}
        for entity in entities:
            key = entity.name.lower().strip()
            if key not in name_groups:
                name_groups[key] = []
            name_groups[key].append(entity)
        
        # 每组选择最佳
        merged = []
        for key, group in name_groups.items():
            if len(group) == 1:
                merged.append(group[0])
            else:
                # 选择分数最高的
                best = max(group, key=lambda e: e.quality_score)
                # 记录合并来源
                best.merged_from = [e.name for e in group if e.name != best.name]
                merged.append(best)
        
        return merged


def filter_graph_results(
    entities: List[Dict[str, Any]] = None,
    relations: List[Dict[str, Any]] = None,
    entity_threshold: float = 0.3,
    relation_threshold: float = 0.3
) -> Tuple[List[GraphEntity], List[GraphRelation]]:
    """
    便捷函数：过滤图谱结果
    
    Args:
        entities: 实体列表
        relations: 关系列表
        entity_threshold: 实体质量阈值
        relation_threshold: 关系质量阈值
        
    Returns:
        (过滤后的实体列表, 过滤后的关系列表)
    """
    graph_filter = GraphFilter(
        entity_threshold=entity_threshold,
        relation_threshold=relation_threshold
    )
    
    filtered_entities = graph_filter.filter_entities(entities or [])
    
    # 构建有效实体集
    valid_entity_names = {e.name for e in filtered_entities}
    
    filtered_relations = graph_filter.filter_relations(
        relations or [],
        valid_entities=valid_entity_names
    )
    
    return filtered_entities, filtered_relations
