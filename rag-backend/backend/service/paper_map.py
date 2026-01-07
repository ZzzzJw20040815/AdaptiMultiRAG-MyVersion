#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
论文地图服务 (PR-11)

提供论文/文档之间的关系可视化数据:
- 文档-实体关联
- 文档相似度网络
- 跨文档实体桥接
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

from backend.config.log import get_logger
from backend.config.database import DatabaseFactory
from backend.model.knowledge_library import KnowledgeDocument

logger = get_logger(__name__)


@dataclass
class PaperNode:
    """论文/文档节点"""
    id: str                          # 文档 ID
    name: str                        # 文档名称
    paper_title: Optional[str] = None  # 论文标题
    authors: Optional[List[str]] = None
    publication_year: Optional[int] = None
    node_type: str = "document"      # 节点类型
    entity_count: int = 0            # 关联实体数
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "paper_title": self.paper_title,
            "authors": self.authors,
            "publication_year": self.publication_year,
            "node_type": self.node_type,
            "entity_count": self.entity_count,
        }


@dataclass
class EntityNode:
    """实体节点"""
    id: str
    name: str
    entity_type: str = ""
    doc_count: int = 0               # 关联文档数（桥接度）
    node_type: str = "entity"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "doc_count": self.doc_count,
            "node_type": self.node_type,
        }


@dataclass
class PaperLink:
    """论文关联边"""
    source: str                      # 源节点 ID
    target: str                      # 目标节点 ID
    weight: float = 1.0              # 边权重
    link_type: str = "related"       # 边类型
    shared_entities: List[str] = field(default_factory=list)  # 共享实体
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "weight": self.weight,
            "link_type": self.link_type,
            "shared_entities": self.shared_entities[:5],  # 限制数量
        }


class PaperMapService:
    """
    论文地图服务
    
    构建文档间的关系网络：
    1. 通过共享实体连接文档
    2. 识别桥接实体（连接多个文档）
    3. 生成可视化数据
    """
    
    def __init__(self, library_id: int):
        """
        初始化服务
        
        Args:
            library_id: 知识库 ID
        """
        self.library_id = library_id
        self.documents: List[PaperNode] = []
        self.entities: List[EntityNode] = []
        self.links: List[PaperLink] = []
        
        # 文档-实体映射
        self.doc_entity_map: Dict[str, Set[str]] = defaultdict(set)
        # 实体-文档映射
        self.entity_doc_map: Dict[str, Set[str]] = defaultdict(set)
    
    async def build_paper_map(
        self,
        include_entities: bool = True,
        min_bridge_docs: int = 2,
        max_entities_per_doc: int = 20
    ) -> Dict[str, Any]:
        """
        构建论文地图数据
        
        Args:
            include_entities: 是否包含实体节点
            min_bridge_docs: 最小桥接文档数（实体至少连接几个文档才显示）
            max_entities_per_doc: 每个文档最多显示多少实体
            
        Returns:
            论文地图数据 (nodes, links, stats)
        """
        logger.info(f"开始构建知识库 {self.library_id} 的论文地图")
        
        # 1. 加载文档
        await self._load_documents()
        
        # 2. 模拟加载文档-实体关联 (实际应从 LightRAG 获取)
        await self._load_document_entities()
        
        # 3. 构建文档间链接
        self._build_document_links()
        
        # 4. 识别桥接实体
        bridge_entities = self._find_bridge_entities(min_bridge_docs)
        
        # 构建结果
        nodes = []
        links = []
        
        # 添加文档节点
        for doc in self.documents:
            nodes.append({
                **doc.to_dict(),
                "category": 0,  # ECharts 分类
                "symbolSize": 30 + min(doc.entity_count, 20),  # 节点大小
            })
        
        # 添加桥接实体节点
        if include_entities:
            for entity in bridge_entities:
                nodes.append({
                    **entity.to_dict(),
                    "category": 1,
                    "symbolSize": 15 + min(entity.doc_count * 5, 25),
                })
        
        # 添加链接
        for link in self.links:
            links.append(link.to_dict())
        
        # 添加文档-桥接实体链接
        if include_entities:
            for entity in bridge_entities:
                for doc_id in self.entity_doc_map.get(entity.id, []):
                    links.append({
                        "source": doc_id,
                        "target": entity.id,
                        "weight": 0.5,
                        "link_type": "has_entity",
                    })
        
        stats = {
            "document_count": len(self.documents),
            "entity_count": len(bridge_entities) if include_entities else 0,
            "link_count": len(links),
            "bridge_entity_count": len(bridge_entities),
        }
        
        logger.info(f"论文地图构建完成: {stats}")
        
        return {
            "nodes": nodes,
            "links": links,
            "categories": [
                {"name": "文档"},
                {"name": "桥接实体"},
            ],
            "stats": stats,
        }
    
    async def _load_documents(self):
        """加载知识库中的文档"""
        db = None
        try:
            db = DatabaseFactory.create_session()
            
            documents = db.query(KnowledgeDocument).filter(
                KnowledgeDocument.library_id == self.library_id
            ).all()
            
            for doc in documents:
                paper_node = PaperNode(
                    id=f"doc_{doc.id}",
                    name=doc.name,
                    paper_title=doc.paper_title,
                    authors=doc.authors if doc.authors else None,
                    publication_year=doc.publication_year,
                )
                self.documents.append(paper_node)
            
            logger.info(f"加载了 {len(self.documents)} 个文档")
            
        finally:
            if db:
                db.close()
    
    async def _load_document_entities(self):
        """
        加载文档-实体关联
        
        TODO: 实际应从 LightRAG/Neo4j 获取实体数据
        当前使用占位实现
        """
        # 占位：为每个文档生成模拟实体关联
        # 实际实现需要从 LightRAG 查询
        
        for doc in self.documents:
            # 模拟一些实体
            doc_id = doc.id
            
            # 这里应该调用 LightRAG 获取文档关联的实体
            # entities = await lightrag.get_entities_for_document(doc.id)
            
            # 占位：使用文档名生成虚拟实体
            if doc.paper_title:
                # 从标题提取关键词作为实体
                words = doc.paper_title.split()[:3]
                for word in words:
                    if len(word) > 3:
                        entity_id = f"entity_{word.lower()}"
                        self.doc_entity_map[doc_id].add(entity_id)
                        self.entity_doc_map[entity_id].add(doc_id)
            
            doc.entity_count = len(self.doc_entity_map[doc_id])
    
    def _build_document_links(self):
        """基于共享实体构建文档间链接"""
        doc_ids = [doc.id for doc in self.documents]
        
        for i, doc1_id in enumerate(doc_ids):
            for doc2_id in doc_ids[i+1:]:
                # 查找共享实体
                shared = self.doc_entity_map[doc1_id] & self.doc_entity_map[doc2_id]
                
                if shared:
                    link = PaperLink(
                        source=doc1_id,
                        target=doc2_id,
                        weight=len(shared),
                        link_type="shared_entity",
                        shared_entities=list(shared),
                    )
                    self.links.append(link)
        
        logger.info(f"构建了 {len(self.links)} 条文档间链接")
    
    def _find_bridge_entities(self, min_docs: int = 2) -> List[EntityNode]:
        """
        识别桥接实体（连接多个文档的实体）
        
        Args:
            min_docs: 最少连接文档数
            
        Returns:
            桥接实体列表
        """
        bridge_entities = []
        
        for entity_id, doc_ids in self.entity_doc_map.items():
            if len(doc_ids) >= min_docs:
                entity = EntityNode(
                    id=entity_id,
                    name=entity_id.replace("entity_", ""),
                    doc_count=len(doc_ids),
                )
                bridge_entities.append(entity)
        
        # 按连接数排序
        bridge_entities.sort(key=lambda e: e.doc_count, reverse=True)
        
        logger.info(f"识别了 {len(bridge_entities)} 个桥接实体")
        
        return bridge_entities[:50]  # 限制数量


async def get_paper_map_data(
    library_id: int,
    include_entities: bool = True
) -> Dict[str, Any]:
    """
    获取论文地图数据
    
    Args:
        library_id: 知识库 ID
        include_entities: 是否包含实体节点
        
    Returns:
        论文地图数据
    """
    service = PaperMapService(library_id)
    return await service.build_paper_map(include_entities=include_entities)
