#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱节点过滤服务

提供多种过滤策略，减少不必要/不重要的节点，提升图谱可读性。
支持的过滤方式：
- 关键词黑名单过滤
- 正则表达式过滤
- 标签黑名单过滤
- 描述长度过滤
- 连接度过滤
"""

import re
from typing import List, Set, Optional
from dataclasses import dataclass, field
from backend.param.visual_graph import KnowledgeGraph, KnowledgeGraphNode, KnowledgeGraphEdge, FilterStats
from backend.config.log import get_logger

logger = get_logger(__name__)


@dataclass
class GraphFilterConfig:
    """
    图谱过滤规则配置类
    
    Attributes:
        keyword_blacklist: 关键词黑名单，节点名或描述包含这些词则过滤（大小写不敏感）
        regex_patterns: 正则表达式模式列表，节点名匹配到则过滤
        label_blacklist: 标签黑名单，节点标签属于这些类型则过滤（大小写不敏感）
        min_description_length: 最小描述长度，描述太短则过滤
        min_edge_count: 最小连接数，连接度低于此值则过滤
        enabled: 是否启用过滤
    """
    keyword_blacklist: List[str] = field(default_factory=list)
    regex_patterns: List[str] = field(default_factory=list)
    label_blacklist: List[str] = field(default_factory=list)
    min_description_length: int = 0
    min_edge_count: int = 0
    enabled: bool = True


# 默认过滤规则配置
DEFAULT_FILTER_CONFIG = GraphFilterConfig(
    # 关键词黑名单（节点名或描述包含这些词则过滤）
    keyword_blacklist=[
        # 参考文献相关
        "reference", "references", "bibliography", "et al", "et al.",
        "cited", "citation", "citations",
        # 元数据
        "doi:", "issn:", "isbn:", "http://", "https://", "www.",
        "arxiv:", "pmid:", "pmc:",
        # 格式化元素
        "figure", "table", "fig.", "tab.", "appendix", "supplementary",
        "supporting information", "acknowledgment", "acknowledgement",
        # 联系方式
        "@", ".edu", ".com", ".org", ".net", ".gov", ".ac.",
        "email:", "e-mail:", "fax:", "tel:", "phone:",
        # 资金来源
        "grant", "funding", "funded by", "supported by",
        "national science foundation", "nsf", "nih",
        # 版权和许可
        "copyright", "©", "all rights reserved", "license",
        "creative commons", "open access",
        # 出版信息
        "received:", "accepted:", "published:", "revised:",
        "volume", "issue", "pages", "pp.",
        # 过于泛化的词
        "introduction", "conclusion", "discussion", "method", "methods",
        "result", "results", "abstract", "keywords",
    ],
    
    # 正则表达式模式（节点名匹配到则过滤）
    regex_patterns=[
        r"^\d{4}$",                    # 纯年份 (如 "2024")
        r"^\[?\d+\]?$",                # 纯数字引用标记 (如 "[1]", "23")
        r"^p{1,2}\.?\s*\d+",           # 页码 (如 "p. 123", "pp.45")
        r"^\d+\.\d+\.\d+",             # 版本号 (如 "3.12.1")
        r"^v?\d+\.\d+",                # 版本号简写 (如 "v2.0", "1.5")
        r"^[A-Z]\.\s*[A-Z]",           # 姓名缩写 (如 "J. Smith", "A. B.")
        r"^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}$",  # 日期格式
        r"^[A-Za-z0-9._%+-]+@",        # 邮箱开头
        r"^\+?\d[\d\s\-]{8,}$",        # 电话号码
        r"^[A-Z]{2,4}\d{5,}$",         # 基金编号 (如 "NSF12345")
        r"^\d+\s*(k|K|M|G|T)?(B|b)?$", # 文件大小
        r"^[a-f0-9]{8,}$",             # 哈希值/ID
        r"^chapter\s*\d+",             # 章节编号
        r"^section\s*\d+",             # 小节编号
        r"^\d+(\.\d+)*$",              # 纯数字小节号 (如 "1.2.3")
    ],
    
    # 标签黑名单（大小写不敏感）
    # 这些标签类型的节点将被过滤掉
    label_blacklist=[
        # 人物相关 - 过滤研究人员、作者等
        "person", "people", "researcher", "author", "contributor",
        "scientist", "professor", "student", "member", "participant",
        "speaker", "presenter", "collaborator", "co-author",
        # 机构相关 - 过滤大学、公司、组织等
        "organization", "institution", "university", "college", "school",
        "company", "corporation", "lab", "laboratory", "center", "centre",
        "department", "faculty", "institute", "group", "team",
        "affiliation", "employer",
        # 地址相关
        "address", "location", "city", "country", "region",
        # 参考文献相关
        "reference", "citation", "bibliography",
        # 其他元数据
        "funding", "date", "time", "year", "url", "email", "link",
        "publisher", "journal", "venue", "conference",
        "page", "volume", "issue", "number",
        "unknown", "other", "misc", "na", "n/a",
    ],
    
    # 描述长度过滤（描述太短说明没有实质内容）
    min_description_length=5,
    
    # 连接度过滤（孤立节点过滤）
    min_edge_count=0,
    
    # 默认启用过滤
    enabled=True,
)


class GraphFilterService:
    """
    知识图谱节点过滤服务
    
    提供多种过滤策略，并确保过滤节点后边的一致性。
    """
    
    def __init__(self, config: Optional[GraphFilterConfig] = None):
        """
        初始化过滤服务
        
        Args:
            config: 过滤规则配置，如果为None则使用默认配置
        """
        self.config = config or DEFAULT_FILTER_CONFIG
        # 预编译正则表达式以提高性能
        self._compiled_patterns: List[re.Pattern] = []
        self._compile_regex_patterns()
        
        logger.info(f"GraphFilterService initialized with config: enabled={self.config.enabled}")
    
    def _compile_regex_patterns(self) -> None:
        """预编译正则表达式"""
        self._compiled_patterns = []
        for pattern in self.config.regex_patterns:
            try:
                self._compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")
    
    def filter_graph(
        self,
        graph,  # Accept any graph-like object
        min_edge_count: Optional[int] = None
    ) -> KnowledgeGraph:
        """
        过滤知识图谱节点和边
        
        Args:
            graph: 原始知识图谱（可以是 LightRAG 的 KnowledgeGraph 或我们自己的）
            min_edge_count: 可选的最小连接数覆盖值
            
        Returns:
            KnowledgeGraph: 过滤后的知识图谱
        """
        if not self.config.enabled:
            logger.info("Graph filtering is disabled, returning original graph")
            # 即使禁用过滤，也需要确保返回正确的类型
            return self._convert_to_our_model(graph)
        
        # 获取节点和边列表（兼容不同的对象类型）
        nodes = getattr(graph, 'nodes', []) or []
        edges = getattr(graph, 'edges', []) or []
        is_truncated = getattr(graph, 'is_truncated', False)
        
        original_node_count = len(nodes)
        original_edge_count = len(edges)
        
        logger.info(f"Starting graph filtering: {original_node_count} nodes, {original_edge_count} edges")
        
        # 使用传入的 min_edge_count 或配置中的值
        effective_min_edge_count = min_edge_count if min_edge_count is not None else self.config.min_edge_count
        
        # 计算每个节点的连接数
        edge_count_map = self._calculate_edge_counts_raw(nodes, edges)
        
        # 收集需要保留的节点
        retained_nodes = []
        filtered_node_ids: Set[str] = set()
        filter_reasons: dict = {}  # 记录过滤原因用于调试
        
        for node in nodes:
            is_filtered, reason = self._should_filter_node_raw(node, edge_count_map, effective_min_edge_count)
            node_id = self._get_node_id(node)
            if is_filtered:
                filtered_node_ids.add(node_id)
                filter_reasons[node_id] = reason
            else:
                retained_nodes.append(node)
        
        # 删除悬空边（指向已删除节点的边）
        retained_edges = self._remove_orphaned_edges_raw(edges, filtered_node_ids)
        
        # 记录过滤统计
        filtered_node_count = original_node_count - len(retained_nodes)
        filtered_edge_count = original_edge_count - len(retained_edges)
        
        logger.info(
            f"Graph filtering complete: "
            f"{len(retained_nodes)} nodes retained (filtered {filtered_node_count}), "
            f"{len(retained_edges)} edges retained (filtered {filtered_edge_count})"
        )
        
        # 记录部分过滤详情（仅前10个用于调试）
        if filter_reasons:
            sample_filtered = list(filter_reasons.items())[:10]
            for node_id, reason in sample_filtered:
                logger.debug(f"Filtered node '{node_id}': {reason}")
        
        # 转换为我们的模型类型，包含过滤统计
        return self._build_knowledge_graph(
            retained_nodes, retained_edges, is_truncated,
            original_node_count=original_node_count,
            original_edge_count=original_edge_count
        )
    
    def _calculate_edge_counts(
        self,
        nodes: List[KnowledgeGraphNode],
        edges: List[KnowledgeGraphEdge]
    ) -> dict:
        """
        计算每个节点的连接数
        
        Args:
            nodes: 节点列表
            edges: 边列表
            
        Returns:
            dict: 节点ID到连接数的映射
        """
        edge_count: dict = {node.id: 0 for node in nodes}
        
        for edge in edges:
            if edge.source in edge_count:
                edge_count[edge.source] += 1
            if edge.target in edge_count:
                edge_count[edge.target] += 1
        
        return edge_count
    
    def _should_filter_node(
        self,
        node: KnowledgeGraphNode,
        edge_count_map: dict,
        min_edge_count: int
    ) -> tuple:
        """
        判断节点是否应该被过滤
        
        Args:
            node: 待检查的节点
            edge_count_map: 节点连接数映射
            min_edge_count: 最小连接数
            
        Returns:
            tuple: (是否过滤, 过滤原因)
        """
        entity_id = node.properties.get("entity_id", node.id) or node.id
        description = node.properties.get("description", "") or ""
        labels = node.labels or []
        
        # 1. 关键词黑名单检查
        entity_lower = entity_id.lower()
        desc_lower = description.lower()
        for keyword in self.config.keyword_blacklist:
            keyword_lower = keyword.lower()
            if keyword_lower in entity_lower or keyword_lower in desc_lower:
                return True, f"keyword_blacklist: '{keyword}'"
        
        # 2. 正则表达式检查
        for i, pattern in enumerate(self._compiled_patterns):
            if pattern.search(entity_id):
                return True, f"regex_pattern: '{self.config.regex_patterns[i]}'"
        
        # 3. 标签黑名单检查
        for label in labels:
            label_lower = label.lower()
            for blacklisted in self.config.label_blacklist:
                if blacklisted.lower() == label_lower:
                    return True, f"label_blacklist: '{blacklisted}'"
        
        # 4. 描述长度检查
        if self.config.min_description_length > 0:
            if len(description.strip()) < self.config.min_description_length:
                return True, f"min_description_length: {len(description.strip())} < {self.config.min_description_length}"
        
        # 5. 连接度检查
        if min_edge_count > 0:
            node_edge_count = edge_count_map.get(node.id, 0)
            if node_edge_count < min_edge_count:
                return True, f"min_edge_count: {node_edge_count} < {min_edge_count}"
        
        return False, None
    
    def _remove_orphaned_edges(
        self,
        edges: List[KnowledgeGraphEdge],
        filtered_node_ids: Set[str]
    ) -> List[KnowledgeGraphEdge]:
        """
        删除悬空边（指向已删除节点的边）
        
        Args:
            edges: 原始边列表
            filtered_node_ids: 被过滤的节点ID集合
            
        Returns:
            List[KnowledgeGraphEdge]: 保留的边列表
        """
        retained_edges = []
        
        for edge in edges:
            if edge.source not in filtered_node_ids and edge.target not in filtered_node_ids:
                retained_edges.append(edge)
        
        return retained_edges
    
    # ==================== 兼容 LightRAG 对象的辅助方法 ====================
    
    def _get_node_id(self, node) -> str:
        """获取节点ID（兼容不同对象类型）"""
        if hasattr(node, 'id'):
            return node.id
        elif isinstance(node, dict):
            return node.get('id', '')
        return str(node)
    
    def _get_node_property(self, node, key: str, default=None):
        """获取节点属性（兼容不同对象类型）"""
        if hasattr(node, 'properties'):
            props = node.properties
            if isinstance(props, dict):
                return props.get(key, default)
            elif hasattr(props, key):
                return getattr(props, key, default)
        elif isinstance(node, dict):
            return node.get('properties', {}).get(key, default)
        return default
    
    def _get_node_labels(self, node) -> list:
        """获取节点标签（兼容不同对象类型）"""
        if hasattr(node, 'labels'):
            return node.labels or []
        elif isinstance(node, dict):
            return node.get('labels', []) or []
        return []
    
    def _get_edge_property(self, edge, key: str, default=None):
        """获取边属性（兼容不同对象类型）"""
        if hasattr(edge, key):
            return getattr(edge, key, default)
        elif isinstance(edge, dict):
            return edge.get(key, default)
        return default
    
    def _calculate_edge_counts_raw(self, nodes, edges) -> dict:
        """
        计算每个节点的连接数（兼容原始对象）
        """
        edge_count = {self._get_node_id(node): 0 for node in nodes}
        
        for edge in edges:
            source = self._get_edge_property(edge, 'source', '')
            target = self._get_edge_property(edge, 'target', '')
            if source in edge_count:
                edge_count[source] += 1
            if target in edge_count:
                edge_count[target] += 1
        
        return edge_count
    
    def _should_filter_node_raw(self, node, edge_count_map: dict, min_edge_count: int) -> tuple:
        """
        判断节点是否应该被过滤（兼容原始对象）
        """
        node_id = self._get_node_id(node)
        entity_id = self._get_node_property(node, 'entity_id', node_id) or node_id
        description = self._get_node_property(node, 'description', '') or ''
        labels = self._get_node_labels(node)
        
        # 1. 关键词黑名单检查
        entity_lower = entity_id.lower()
        desc_lower = description.lower()
        for keyword in self.config.keyword_blacklist:
            keyword_lower = keyword.lower()
            if keyword_lower in entity_lower or keyword_lower in desc_lower:
                return True, f"keyword_blacklist: '{keyword}'"
        
        # 2. 正则表达式检查
        for i, pattern in enumerate(self._compiled_patterns):
            if pattern.search(entity_id):
                return True, f"regex_pattern: '{self.config.regex_patterns[i]}'"
        
        # 3. 标签黑名单检查
        for label in labels:
            label_lower = label.lower()
            for blacklisted in self.config.label_blacklist:
                if blacklisted.lower() == label_lower:
                    return True, f"label_blacklist: '{blacklisted}'"
        
        # 4. 描述长度检查
        if self.config.min_description_length > 0:
            if len(description.strip()) < self.config.min_description_length:
                return True, f"min_description_length: {len(description.strip())} < {self.config.min_description_length}"
        
        # 5. 连接度检查
        if min_edge_count > 0:
            node_edge_count = edge_count_map.get(node_id, 0)
            if node_edge_count < min_edge_count:
                return True, f"min_edge_count: {node_edge_count} < {min_edge_count}"
        
        return False, None
    
    def _remove_orphaned_edges_raw(self, edges, filtered_node_ids: Set[str]) -> list:
        """
        删除悬空边（兼容原始对象）
        """
        retained_edges = []
        
        for edge in edges:
            source = self._get_edge_property(edge, 'source', '')
            target = self._get_edge_property(edge, 'target', '')
            if source not in filtered_node_ids and target not in filtered_node_ids:
                retained_edges.append(edge)
        
        return retained_edges
    
    def _convert_node_to_dict(self, node) -> dict:
        """将节点转换为字典格式"""
        if isinstance(node, dict):
            return node
        
        # 处理 Pydantic 模型或其他对象
        node_dict = {
            'id': self._get_node_id(node),
            'labels': self._get_node_labels(node),
            'properties': {}
        }
        
        # 提取 properties
        if hasattr(node, 'properties'):
            props = node.properties
            if isinstance(props, dict):
                node_dict['properties'] = props
            elif hasattr(props, '__dict__'):
                node_dict['properties'] = {k: v for k, v in props.__dict__.items() if not k.startswith('_')}
            elif hasattr(props, 'model_dump'):
                node_dict['properties'] = props.model_dump()
        
        return node_dict
    
    def _convert_edge_to_dict(self, edge) -> dict:
        """将边转换为字典格式"""
        if isinstance(edge, dict):
            return edge
        
        edge_dict = {
            'id': self._get_edge_property(edge, 'id', ''),
            'type': self._get_edge_property(edge, 'type', None),
            'source': self._get_edge_property(edge, 'source', ''),
            'target': self._get_edge_property(edge, 'target', ''),
            'properties': {}
        }
        
        if hasattr(edge, 'properties'):
            props = edge.properties
            if isinstance(props, dict):
                edge_dict['properties'] = props
            elif hasattr(props, '__dict__'):
                edge_dict['properties'] = {k: v for k, v in props.__dict__.items() if not k.startswith('_')}
            elif hasattr(props, 'model_dump'):
                edge_dict['properties'] = props.model_dump()
        
        return edge_dict
    
    def _build_knowledge_graph(
        self, 
        nodes: list, 
        edges: list, 
        is_truncated: bool = False,
        original_node_count: Optional[int] = None,
        original_edge_count: Optional[int] = None
    ) -> KnowledgeGraph:
        """
        构建 KnowledgeGraph 对象（将原始对象转换为我们的 Pydantic 模型）
        同时为每个节点添加语义类型分类
        """
        from backend.service.node_type_classifier import get_classifier
        classifier = get_classifier()
        
        # 转换节点并添加语义类型
        converted_nodes = []
        for node in nodes:
            node_dict = self._convert_node_to_dict(node)
            # 添加语义类型分类
            semantic_type = classifier.classify(node_dict)
            node_dict['properties']['semantic_type'] = semantic_type
            converted_nodes.append(KnowledgeGraphNode(**node_dict))
        
        # 转换边
        converted_edges = []
        for edge in edges:
            edge_dict = self._convert_edge_to_dict(edge)
            converted_edges.append(KnowledgeGraphEdge(**edge_dict))
        
        # 构建过滤统计信息
        filter_stats = None
        if original_node_count is not None:
            filter_stats = FilterStats(
                original_node_count=original_node_count,
                original_edge_count=original_edge_count or 0,
                filtered_node_count=len(converted_nodes),
                filtered_edge_count=len(converted_edges)
            )
        
        return KnowledgeGraph(
            nodes=converted_nodes,
            edges=converted_edges,
            is_truncated=is_truncated,
            filter_stats=filter_stats
        )
    
    def _convert_to_our_model(self, graph) -> KnowledgeGraph:
        """
        将外部 KnowledgeGraph 对象转换为我们的模型
        """
        nodes = getattr(graph, 'nodes', []) or []
        edges = getattr(graph, 'edges', []) or []
        is_truncated = getattr(graph, 'is_truncated', False)
        
        return self._build_knowledge_graph(nodes, edges, is_truncated)
    
    def update_config(self, **kwargs) -> None:
        """
        更新过滤配置
        
        Args:
            **kwargs: 要更新的配置项
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Updated filter config: {key}={value}")
            else:
                logger.warning(f"Unknown config key: {key}")
        
        # 如果更新了正则模式，重新编译
        if "regex_patterns" in kwargs:
            self._compile_regex_patterns()
    
    def get_filter_stats(self, graph: KnowledgeGraph) -> dict:
        """
        获取过滤统计信息（不实际过滤，仅统计）
        
        Args:
            graph: 知识图谱
            
        Returns:
            dict: 统计信息
        """
        edge_count_map = self._calculate_edge_counts(graph.nodes, graph.edges)
        
        stats = {
            "total_nodes": len(graph.nodes),
            "total_edges": len(graph.edges),
            "would_filter": {
                "by_keyword": 0,
                "by_regex": 0,
                "by_label": 0,
                "by_description_length": 0,
                "by_edge_count": 0,
            }
        }
        
        for node in graph.nodes:
            entity_id = node.properties.get("entity_id", node.id) or node.id
            description = node.properties.get("description", "") or ""
            labels = node.labels or []
            
            # 检查各种过滤条件
            entity_lower = entity_id.lower()
            desc_lower = description.lower()
            
            for keyword in self.config.keyword_blacklist:
                if keyword.lower() in entity_lower or keyword.lower() in desc_lower:
                    stats["would_filter"]["by_keyword"] += 1
                    break
            
            for pattern in self._compiled_patterns:
                if pattern.search(entity_id):
                    stats["would_filter"]["by_regex"] += 1
                    break
            
            for label in labels:
                if label.lower() in [l.lower() for l in self.config.label_blacklist]:
                    stats["would_filter"]["by_label"] += 1
                    break
            
            if len(description.strip()) < self.config.min_description_length:
                stats["would_filter"]["by_description_length"] += 1
            
            if edge_count_map.get(node.id, 0) < self.config.min_edge_count:
                stats["would_filter"]["by_edge_count"] += 1
        
        return stats
