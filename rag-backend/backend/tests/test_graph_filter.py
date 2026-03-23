#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱节点过滤服务测试

测试各种过滤规则的有效性和边界情况。
"""

import pytest
from backend.service.graph_filter import (
    GraphFilterService,
    GraphFilterConfig,
    DEFAULT_FILTER_CONFIG
)
from backend.param.visual_graph import (
    KnowledgeGraph,
    KnowledgeGraphNode,
    KnowledgeGraphEdge
)


# ==================== 测试数据工厂 ====================

def create_node(
    node_id: str,
    entity_id: str = None,
    description: str = "Test description",
    labels: list = None
) -> KnowledgeGraphNode:
    """创建测试节点"""
    return KnowledgeGraphNode(
        id=node_id,
        labels=labels or ["Entity"],
        properties={
            "entity_id": entity_id or node_id,
            "description": description
        }
    )


def create_edge(
    edge_id: str,
    source: str,
    target: str,
    edge_type: str = "RELATED"
) -> KnowledgeGraphEdge:
    """创建测试边"""
    return KnowledgeGraphEdge(
        id=edge_id,
        type=edge_type,
        source=source,
        target=target,
        properties={}
    )


def create_graph(
    nodes: list,
    edges: list = None
) -> KnowledgeGraph:
    """创建测试图谱"""
    return KnowledgeGraph(
        nodes=nodes,
        edges=edges or [],
        is_truncated=False
    )


# ==================== 基础功能测试 ====================

class TestGraphFilterServiceBasic:
    """基础功能测试"""
    
    def test_filter_service_initialization(self):
        """测试过滤服务初始化"""
        service = GraphFilterService()
        assert service.config is not None
        assert service.config.enabled is True
    
    def test_filter_service_with_custom_config(self):
        """测试自定义配置"""
        config = GraphFilterConfig(
            keyword_blacklist=["test"],
            enabled=True
        )
        service = GraphFilterService(config)
        assert "test" in service.config.keyword_blacklist
    
    def test_empty_graph_returns_empty(self):
        """测试空图谱返回空"""
        service = GraphFilterService()
        graph = create_graph(nodes=[], edges=[])
        result = service.filter_graph(graph)
        assert len(result.nodes) == 0
        assert len(result.edges) == 0
    
    def test_disabled_filter_returns_original(self):
        """测试禁用过滤时返回原始图谱"""
        config = GraphFilterConfig(enabled=False)
        service = GraphFilterService(config)
        
        nodes = [create_node("n1", "reference")]  # 正常会被过滤
        graph = create_graph(nodes=nodes)
        
        result = service.filter_graph(graph)
        assert len(result.nodes) == 1  # 未被过滤


# ==================== 关键词过滤测试 ====================

class TestKeywordFiltering:
    """关键词黑名单过滤测试"""
    
    def test_filter_by_entity_id_keyword(self):
        """测试根据实体ID关键词过滤"""
        config = GraphFilterConfig(
            keyword_blacklist=["reference", "citation"],
            enabled=True
        )
        service = GraphFilterService(config)
        
        nodes = [
            create_node("n1", "Machine Learning"),  # 保留
            create_node("n2", "Reference List"),    # 过滤
            create_node("n3", "Citation Analysis"), # 过滤
        ]
        graph = create_graph(nodes=nodes)
        
        result = service.filter_graph(graph)
        assert len(result.nodes) == 1
        assert result.nodes[0].id == "n1"
    
    def test_filter_by_description_keyword(self):
        """测试根据描述关键词过滤"""
        config = GraphFilterConfig(
            keyword_blacklist=["doi:"],
            enabled=True
        )
        service = GraphFilterService(config)
        
        nodes = [
            create_node("n1", description="A scientific paper"),
            create_node("n2", description="doi:10.1234/example"),
        ]
        graph = create_graph(nodes=nodes)
        
        result = service.filter_graph(graph)
        assert len(result.nodes) == 1
        assert result.nodes[0].id == "n1"
    
    def test_keyword_case_insensitive(self):
        """测试关键词大小写不敏感"""
        config = GraphFilterConfig(
            keyword_blacklist=["Reference"],
            enabled=True
        )
        service = GraphFilterService(config)
        
        nodes = [
            create_node("n1", "REFERENCE"),
            create_node("n2", "reference"),
            create_node("n3", "ReFeReNcE"),
        ]
        graph = create_graph(nodes=nodes)
        
        result = service.filter_graph(graph)
        assert len(result.nodes) == 0


# ==================== 正则过滤测试 ====================

class TestRegexFiltering:
    """正则表达式过滤测试"""
    
    def test_filter_year_pattern(self):
        """测试过滤纯年份"""
        config = GraphFilterConfig(
            regex_patterns=[r"^\d{4}$"],
            keyword_blacklist=[],
            enabled=True
        )
        service = GraphFilterService(config)
        
        nodes = [
            create_node("n1", "2024"),           # 过滤 - 纯年份
            create_node("n2", "Year 2024"),      # 保留
            create_node("n3", "1990"),           # 过滤 - 纯年份
        ]
        graph = create_graph(nodes=nodes)
        
        result = service.filter_graph(graph)
        assert len(result.nodes) == 1
        assert result.nodes[0].id == "n2"
    
    def test_filter_version_numbers(self):
        """测试过滤版本号"""
        config = GraphFilterConfig(
            regex_patterns=[r"^\d+\.\d+\.\d+"],
            keyword_blacklist=[],
            enabled=True
        )
        service = GraphFilterService(config)
        
        nodes = [
            create_node("n1", "3.12.1"),           # 过滤
            create_node("n2", "Python 3.12.1"),   # 保留
            create_node("n3", "1.0.0"),           # 过滤
        ]
        graph = create_graph(nodes=nodes)
        
        result = service.filter_graph(graph)
        assert len(result.nodes) == 1
        assert result.nodes[0].id == "n2"
    
    def test_filter_citation_marks(self):
        """测试过滤引用标记"""
        config = GraphFilterConfig(
            regex_patterns=[r"^\[?\d+\]?$"],
            keyword_blacklist=[],
            enabled=True
        )
        service = GraphFilterService(config)
        
        nodes = [
            create_node("n1", "[1]"),
            create_node("n2", "23"),
            create_node("n3", "[123]"),
            create_node("n4", "Figure 1"),  # 保留
        ]
        graph = create_graph(nodes=nodes)
        
        result = service.filter_graph(graph)
        assert len(result.nodes) == 1
        assert result.nodes[0].id == "n4"


# ==================== 标签过滤测试 ====================

class TestLabelFiltering:
    """标签黑名单过滤测试"""
    
    def test_filter_by_label(self):
        """测试根据标签过滤"""
        config = GraphFilterConfig(
            label_blacklist=["AUTHOR", "DATE"],
            keyword_blacklist=[],
            enabled=True
        )
        service = GraphFilterService(config)
        
        nodes = [
            create_node("n1", labels=["CONCEPT"]),  # 保留
            create_node("n2", labels=["AUTHOR"]),   # 过滤
            create_node("n3", labels=["DATE"]),     # 过滤
        ]
        graph = create_graph(nodes=nodes)
        
        result = service.filter_graph(graph)
        assert len(result.nodes) == 1
        assert result.nodes[0].id == "n1"
    
    def test_label_case_insensitive(self):
        """测试标签大小写不敏感"""
        config = GraphFilterConfig(
            label_blacklist=["Author"],
            keyword_blacklist=[],
            enabled=True
        )
        service = GraphFilterService(config)
        
        nodes = [
            create_node("n1", labels=["AUTHOR"]),
            create_node("n2", labels=["author"]),
        ]
        graph = create_graph(nodes=nodes)
        
        result = service.filter_graph(graph)
        assert len(result.nodes) == 0


# ==================== 描述长度过滤测试 ====================

class TestDescriptionLengthFiltering:
    """描述长度过滤测试"""
    
    def test_filter_short_description(self):
        """测试过滤短描述"""
        config = GraphFilterConfig(
            min_description_length=10,
            keyword_blacklist=[],
            enabled=True
        )
        service = GraphFilterService(config)
        
        nodes = [
            create_node("n1", description="Deep learning model"),  # 保留 (18字符)
            create_node("n2", description="Short"),               # 过滤 (5字符)
            create_node("n3", description=""),                    # 过滤 (0字符)
        ]
        graph = create_graph(nodes=nodes)
        
        result = service.filter_graph(graph)
        assert len(result.nodes) == 1
        assert result.nodes[0].id == "n1"
    
    def test_zero_min_length_keeps_all(self):
        """测试最小长度为0时保留所有"""
        config = GraphFilterConfig(
            min_description_length=0,
            keyword_blacklist=[],
            enabled=True
        )
        service = GraphFilterService(config)
        
        nodes = [
            create_node("n1", description=""),
            create_node("n2", description="X"),
        ]
        graph = create_graph(nodes=nodes)
        
        result = service.filter_graph(graph)
        assert len(result.nodes) == 2


# ==================== 连接度过滤测试 ====================

class TestEdgeCountFiltering:
    """连接度过滤测试"""
    
    def test_filter_isolated_nodes(self):
        """测试过滤孤立节点"""
        config = GraphFilterConfig(
            min_edge_count=1,
            keyword_blacklist=[],
            enabled=True
        )
        service = GraphFilterService(config)
        
        nodes = [
            create_node("n1"),  # 有连接
            create_node("n2"),  # 有连接
            create_node("n3"),  # 孤立
        ]
        edges = [
            create_edge("e1", "n1", "n2")
        ]
        graph = create_graph(nodes=nodes, edges=edges)
        
        result = service.filter_graph(graph, min_edge_count=1)
        assert len(result.nodes) == 2
        assert "n3" not in [n.id for n in result.nodes]
    
    def test_filter_low_connectivity_nodes(self):
        """测试过滤低连接度节点"""
        config = GraphFilterConfig(
            keyword_blacklist=[],
            enabled=True
        )
        service = GraphFilterService(config)
        
        nodes = [
            create_node("n1"),  # 2条边
            create_node("n2"),  # 1条边
            create_node("n3"),  # 1条边
        ]
        edges = [
            create_edge("e1", "n1", "n2"),
            create_edge("e2", "n1", "n3"),
        ]
        graph = create_graph(nodes=nodes, edges=edges)
        
        result = service.filter_graph(graph, min_edge_count=2)
        assert len(result.nodes) == 1
        assert result.nodes[0].id == "n1"


# ==================== 边一致性测试 ====================

class TestEdgeConsistency:
    """边一致性测试 - 确保无悬空边"""
    
    def test_remove_orphaned_edges(self):
        """测试删除悬空边"""
        config = GraphFilterConfig(
            keyword_blacklist=["filter_me"],
            enabled=True
        )
        service = GraphFilterService(config)
        
        nodes = [
            create_node("n1", "Concept A"),     # 保留
            create_node("n2", "filter_me"),     # 过滤
            create_node("n3", "Concept B"),     # 保留
        ]
        edges = [
            create_edge("e1", "n1", "n2"),  # 悬空 - 删除
            create_edge("e2", "n1", "n3"),  # 保留
            create_edge("e3", "n2", "n3"),  # 悬空 - 删除
        ]
        graph = create_graph(nodes=nodes, edges=edges)
        
        result = service.filter_graph(graph)
        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        assert result.edges[0].id == "e2"
    
    def test_all_edges_removed_when_all_nodes_filtered(self):
        """测试所有节点被过滤时边也全部删除"""
        config = GraphFilterConfig(
            keyword_blacklist=["filter"],
            enabled=True
        )
        service = GraphFilterService(config)
        
        nodes = [
            create_node("n1", "filter_a"),
            create_node("n2", "filter_b"),
        ]
        edges = [
            create_edge("e1", "n1", "n2")
        ]
        graph = create_graph(nodes=nodes, edges=edges)
        
        result = service.filter_graph(graph)
        assert len(result.nodes) == 0
        assert len(result.edges) == 0


# ==================== 默认配置测试 ====================

class TestDefaultConfig:
    """默认配置过滤测试"""
    
    def test_default_config_filters_references(self):
        """测试默认配置过滤参考文献"""
        service = GraphFilterService()
        
        nodes = [
            create_node("n1", "Deep Learning"),
            create_node("n2", "References section"),
            create_node("n3", "et al. 2020"),
        ]
        graph = create_graph(nodes=nodes)
        
        result = service.filter_graph(graph)
        assert len(result.nodes) == 1
        assert result.nodes[0].id == "n1"
    
    def test_default_config_filters_metadata(self):
        """测试默认配置过滤元数据"""
        service = GraphFilterService()
        
        nodes = [
            create_node("n1", "Neural Network"),
            create_node("n2", description="doi:10.1234/test"),
            create_node("n3", "user@example.com"),
        ]
        graph = create_graph(nodes=nodes)
        
        result = service.filter_graph(graph)
        assert len(result.nodes) == 1
        assert result.nodes[0].id == "n1"


# ==================== 统计功能测试 ====================

class TestFilterStats:
    """过滤统计功能测试"""
    
    def test_get_filter_stats(self):
        """测试获取过滤统计信息"""
        config = GraphFilterConfig(
            keyword_blacklist=["reference"],
            min_description_length=10,
            enabled=True
        )
        service = GraphFilterService(config)
        
        nodes = [
            create_node("n1", "Reference"),
            create_node("n2", description="Short"),
            create_node("n3", "Valid", description="This is a valid node"),
        ]
        graph = create_graph(nodes=nodes)
        
        stats = service.get_filter_stats(graph)
        
        assert stats["total_nodes"] == 3
        assert stats["would_filter"]["by_keyword"] >= 1
        assert stats["would_filter"]["by_description_length"] >= 1


# ==================== 配置更新测试 ====================

class TestConfigUpdate:
    """配置更新测试"""
    
    def test_update_config(self):
        """测试更新配置"""
        service = GraphFilterService()
        original_length = service.config.min_description_length
        
        service.update_config(min_description_length=20)
        
        assert service.config.min_description_length == 20
        assert service.config.min_description_length != original_length
    
    def test_update_regex_recompiles(self):
        """测试更新正则后重新编译"""
        service = GraphFilterService()
        
        new_patterns = [r"^test\d+$"]
        service.update_config(regex_patterns=new_patterns)
        
        assert len(service._compiled_patterns) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
