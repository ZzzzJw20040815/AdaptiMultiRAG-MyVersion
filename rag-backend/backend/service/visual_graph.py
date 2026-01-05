from typing import Optional
import logging
import os
from backend.param.visual_graph import KnowledgeGraph
from backend.rag.storage.lightrag_storage import LightRAGStorage
from backend.service.graph_filter import filter_graph_results

logger = logging.getLogger(__name__)


class VisualGraphService:
    """可视化图服务类，用于处理知识图谱的可视化相关功能"""
    
    def __init__(self, collection_id: str, max_graph_nodes: int = 1000):
        """
        初始化可视化图服务
        
        Args:
            collection_id: 知识库集合ID，用作workspace
            max_graph_nodes: 最大图节点数量，默认1000
        """
        self.collection_id = collection_id
        self.max_graph_nodes = max_graph_nodes
        self.entity_threshold = float(os.getenv("KG_ENTITY_THRESHOLD", "0.45"))
        self.relation_threshold = float(os.getenv("KG_RELATION_THRESHOLD", "0.3"))
        self.exclude_labels = {
            label.strip().lower()
            for label in os.getenv("KG_EXCLUDE_LABELS", "person,author").split(",")
            if label.strip()
        }
        self.drop_isolated_nodes = os.getenv("KG_DROP_ISOLATED", "true").lower() in {"1", "true", "yes"}
        
        # 初始化 LightRAGStorage
        self.lightrag_storage = LightRAGStorage(workspace=collection_id)
        self.lightrag = None  # 将在 _ensure_lightrag_initialized 中初始化
        
        logger.info(f"VisualGraphService initialized with collection_id={collection_id}, max_graph_nodes={max_graph_nodes}")
    
    async def _ensure_lightrag_initialized(self):
        """确保 LightRAG 实例已初始化"""
        if self.lightrag is None:
            logger.info(f"Initializing LightRAG instance for collection_id={self.collection_id}")
            # 异步初始化 lightrag_storage
            await self.lightrag_storage.initialize()
            # 从 lightrag_storage 获取 rag 实例
            self.lightrag = self.lightrag_storage.rag
    
    async def get_knowledge_graph(
        self,
        node_label: str,
        max_depth: int = 3,
        max_nodes: Optional[int] = None
    ) -> KnowledgeGraph:
        """
        获取知识图谱数据
        
        Args:
            node_label: 节点标签，用于筛选起始节点
            max_depth: 最大深度，默认为3
            max_nodes: 最大节点数量，如果为None则使用实例的max_graph_nodes
            
        Returns:
            KnowledgeGraph: 包含节点、边和截断标志的知识图谱对象
            
        Raises:
            ValueError: 当参数无效时抛出
            Exception: 当获取图数据失败时抛出
        """
        try:
            # 参数验证
            if max_depth < 1:
                raise ValueError("max_depth must be at least 1")
            
            if max_nodes is None:
                max_nodes = self.max_graph_nodes
            elif max_nodes < 1:
                raise ValueError("max_nodes must be at least 1")
            
            logger.info(f"Getting knowledge graph: node_label={node_label}, max_depth={max_depth}, max_nodes={max_nodes}")
            
            # 确保 LightRAG 实例已初始化
            await self._ensure_lightrag_initialized()
            
            # 直接使用 LightRAG 的 get_knowledge_graph 方法
            knowledge_graph = await self.lightrag.get_knowledge_graph(
                node_label=node_label,
                max_depth=max_depth,
                max_nodes=max_nodes
            )

            filtered_graph = self._filter_knowledge_graph(knowledge_graph, node_label=node_label)

            logger.info(
                "Knowledge graph retrieved: %s nodes/%s edges -> %s nodes/%s edges, truncated=%s",
                len(knowledge_graph.nodes),
                len(knowledge_graph.edges),
                len(filtered_graph.nodes),
                len(filtered_graph.edges),
                filtered_graph.is_truncated
            )

            return filtered_graph
            
        except ValueError as e:
            logger.error(f"Parameter validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get knowledge graph: {e}")
            raise Exception(f"Failed to retrieve knowledge graph: {str(e)}")

    def _filter_knowledge_graph(self, knowledge_graph: KnowledgeGraph, node_label: str) -> KnowledgeGraph:
        if not knowledge_graph.nodes:
            return knowledge_graph

        active_exclude_labels = self.exclude_labels if node_label == "*" else set()

        node_name_by_id = {}
        entities_input = []
        for node in knowledge_graph.nodes:
            labels = node.labels or []
            if self._should_exclude_label(labels, active_exclude_labels):
                continue
            name = self._extract_node_name(node)
            node_name_by_id[node.id] = name
            entities_input.append({
                "name": name,
                "type": labels[0] if labels else "",
                "description": (node.properties or {}).get("description", ""),
                "source_docs": (node.properties or {}).get("source_docs", []),
            })

        relations_input = []
        for edge in knowledge_graph.edges or []:
            source_name = node_name_by_id.get(edge.source)
            target_name = node_name_by_id.get(edge.target)
            if not source_name or not target_name:
                continue
            relations_input.append({
                "source": source_name,
                "target": target_name,
                "relation_type": edge.type or "",
                "description": (edge.properties or {}).get("description", ""),
            })

        filtered_entities, filtered_relations = filter_graph_results(
            entities=entities_input,
            relations=relations_input,
            entity_threshold=self.entity_threshold,
            relation_threshold=self.relation_threshold
        )

        keep_names = {entity.name for entity in filtered_entities}
        allowed_relations = {
            (relation.source, relation.target, relation.relation_type or "")
            for relation in filtered_relations
        }

        filtered_nodes = []
        for node in knowledge_graph.nodes:
            if self._should_exclude_label(node.labels or [], active_exclude_labels):
                continue
            if node_name_by_id.get(node.id) not in keep_names:
                continue
            filtered_nodes.append(self._normalize_node(node))

        filtered_edges = []
        for edge in knowledge_graph.edges or []:
            source_name = node_name_by_id.get(edge.source)
            target_name = node_name_by_id.get(edge.target)
            if not source_name or not target_name:
                continue
            if source_name not in keep_names or target_name not in keep_names:
                continue
            if (source_name, target_name, edge.type or "") not in allowed_relations:
                continue
            filtered_edges.append(self._normalize_edge(edge))

        if self.drop_isolated_nodes and filtered_edges:
            connected_ids = {edge["source"] for edge in filtered_edges} | {edge["target"] for edge in filtered_edges}
            filtered_nodes = [node for node in filtered_nodes if node["id"] in connected_ids]

        return KnowledgeGraph(
            nodes=filtered_nodes,
            edges=filtered_edges,
            is_truncated=knowledge_graph.is_truncated
        )

    def _extract_node_name(self, node) -> str:
        properties = node.properties or {}
        return properties.get("entity_id") or properties.get("name") or node.id

    def _normalize_node(self, node) -> dict:
        return {
            "id": getattr(node, "id", None),
            "labels": list(getattr(node, "labels", []) or []),
            "properties": getattr(node, "properties", None) or {}
        }

    def _normalize_edge(self, edge) -> dict:
        return {
            "id": getattr(edge, "id", None),
            "type": getattr(edge, "type", None),
            "source": getattr(edge, "source", None),
            "target": getattr(edge, "target", None),
            "properties": getattr(edge, "properties", None) or {}
        }

    def _should_exclude_label(self, labels, exclude_labels=None) -> bool:
        active_labels = exclude_labels if exclude_labels is not None else self.exclude_labels
        if not active_labels:
            return False
        for label in labels:
            if label and label.lower() in active_labels:
                return True
        return False
