from typing import Any, Optional
from pydantic import BaseModel


class KnowledgeGraphNode(BaseModel):
    id: str
    labels: list[str]
    properties: dict[str, Any]  # anything else goes here


class KnowledgeGraphEdge(BaseModel):
    id: str
    type: Optional[str]
    source: str  # id of source node
    target: str  # id of target node
    properties: dict[str, Any]  # anything else goes here


class FilterStats(BaseModel):
    """过滤统计信息"""
    original_node_count: int = 0
    original_edge_count: int = 0
    filtered_node_count: int = 0
    filtered_edge_count: int = 0


class KnowledgeGraph(BaseModel):
    nodes: list[KnowledgeGraphNode] = []
    edges: list[KnowledgeGraphEdge] = []
    is_truncated: bool = False
    filter_stats: Optional[FilterStats] = None  # 过滤统计信息
