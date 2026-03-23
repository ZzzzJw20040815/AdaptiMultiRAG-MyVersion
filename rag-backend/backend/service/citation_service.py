#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
引用服务层 (PR-2)

提供引用溯源相关的业务逻辑，包括：
- 获取文档的完整学术元数据
- 构建引用信息
- 格式化参考文献
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from backend.config.database import DatabaseFactory
from backend.model.knowledge_library import KnowledgeLibrary, KnowledgeDocument
from backend.config.log import get_logger

logger = get_logger(__name__)


@dataclass
class CitationInfo:
    """引用信息结构"""
    doc_id: int
    doc_name: str  # 文档名称/论文标题
    academic_title: Optional[str] = None
    authors: Optional[List[str]] = None
    publish_year: Optional[int] = None
    doi: Optional[str] = None
    source_type: str = "unknown"
    evidence_snippet: Optional[str] = None  # 证据片段
    page_info: Optional[str] = None  # 页码信息（如果有）

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "doc_id": self.doc_id,
            "doc_name": self.doc_name,
            "academic_title": self.academic_title,
            "authors": self.authors,
            "publish_year": self.publish_year,
            "doi": self.doi,
            "source_type": self.source_type,
            "evidence_snippet": self.evidence_snippet,
            "page_info": self.page_info
        }

    def format_citation(self, index: int) -> str:
        """格式化为参考文献字符串

        Args:
            index: 引用编号（1, 2, 3...）

        Returns:
            格式化的参考文献字符串
        """
        parts = [f"[{index}]"]

        # 作者
        if self.authors and len(self.authors) > 0:
            if len(self.authors) == 1:
                parts.append(self.authors[0])
            elif len(self.authors) == 2:
                parts.append(f"{self.authors[0]} & {self.authors[1]}")
            else:
                parts.append(f"{self.authors[0]} et al.")

        # 年份
        if self.publish_year:
            parts.append(f"({self.publish_year})")

        # 标题
        title = self.academic_title or self.doc_name
        parts.append(f'"{title}"')

        # DOI
        if self.doi:
            parts.append(f"DOI: {self.doi}")

        return " ".join(parts)


def _load_documents_metadata_maps(collection_id: str) -> Tuple[Dict[str, CitationInfo], Dict[str, CitationInfo]]:
    """加载文档元数据，并分别返回唯一文献映射与别名查找映射。"""
    canonical_map: Dict[str, CitationInfo] = {}
    alias_map: Dict[str, CitationInfo] = {}

    db = DatabaseFactory.create_session()

    try:
        library = db.query(KnowledgeLibrary).filter(
            KnowledgeLibrary.collection_id == collection_id,
            KnowledgeLibrary.is_active == True
        ).first()

        if not library:
            logger.warning(f"未找到collection_id={collection_id}的知识库")
            return canonical_map, alias_map

        documents = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.library_id == library.id
        ).all()

        for doc in documents:
            authors = None
            if doc.authors:
                try:
                    authors = json.loads(doc.authors)
                except Exception:
                    authors = [doc.authors]

            citation_info = CitationInfo(
                doc_id=doc.id,
                doc_name=doc.name,
                academic_title=doc.academic_title,
                authors=authors,
                publish_year=doc.publish_year,
                doi=doc.doi,
                source_type=doc.source_type or "unknown"
            )

            canonical_key = doc.name or doc.academic_title or doc.url or f"doc_{doc.id}"
            canonical_map[canonical_key] = citation_info

            alias_candidates = [doc.name, doc.academic_title, doc.url]
            for alias in alias_candidates:
                if alias:
                    alias_map[alias] = citation_info

        logger.info(
            f"获取到{len(canonical_map)}个文档的元数据"
            f"，可用于查找的别名键共{len(alias_map)}个"
        )
        return canonical_map, alias_map
    finally:
        db.close()


def get_document_metadata_by_name(collection_id: str, doc_name: str) -> Optional[CitationInfo]:
    """
    根据文档名称获取完整的学术元数据

    Args:
        collection_id: 知识库的collection_id
        doc_name: 文档名称（可能是URL或标题）

    Returns:
        CitationInfo: 包含完整元数据的引用信息，如果未找到返回None
    """
    try:
        db = DatabaseFactory.create_session()

        try:
            # 根据collection_id查找知识库
            library = db.query(KnowledgeLibrary).filter(
                KnowledgeLibrary.collection_id == collection_id,
                KnowledgeLibrary.is_active == True
            ).first()

            if not library:
                logger.warning(f"未找到collection_id={collection_id}的知识库")
                return None

            # 查找文档（优先按name匹配，其次按academic_title匹配，最后按url匹配）
            document = db.query(KnowledgeDocument).filter(
                KnowledgeDocument.library_id == library.id
            ).filter(
                (KnowledgeDocument.name == doc_name) |
                (KnowledgeDocument.academic_title == doc_name) |
                (KnowledgeDocument.url == doc_name)
            ).first()

            if not document:
                logger.debug(f"未找到名为'{doc_name}'的文档")
                return None

            # 解析作者JSON
            authors = None
            if document.authors:
                try:
                    authors = json.loads(document.authors)
                except:
                    authors = [document.authors]

            return CitationInfo(
                doc_id=document.id,
                doc_name=document.name,
                academic_title=document.academic_title,
                authors=authors,
                publish_year=document.publish_year,
                doi=document.doi,
                source_type=document.source_type or "unknown"
            )

        finally:
            db.close()

    except Exception as e:
        logger.error(f"获取文档元数据失败: {str(e)}")
        return None


def get_all_documents_metadata(collection_id: str, include_aliases: bool = True) -> Dict[str, CitationInfo]:
    """
    获取知识库中所有文档的元数据

    Args:
        collection_id: 知识库的collection_id

    Returns:
        Dict[str, CitationInfo]: 文档名到元数据的映射
    """
    try:
        canonical_map, alias_map = _load_documents_metadata_maps(collection_id)
        if not include_aliases:
            return canonical_map

        merged_map = dict(alias_map)
        merged_map.update(canonical_map)
        return merged_map

    except Exception as e:
        logger.error(f"获取所有文档元数据失败: {str(e)}")
        return {}


def build_citation_context(
    collection_id: str,
    retrieved_docs: List[Any],
    url_to_name: Dict[str, str]
) -> Dict[str, Any]:
    """
    构建引用上下文信息，用于答案生成

    Args:
        collection_id: 知识库ID
        retrieved_docs: 检索到的文档列表
        url_to_name: URL到名称的映射

    Returns:
        包含文档内容和引用元数据的上下文
    """
    # 唯一文献映射用于统计与前端状态，别名映射仅用于内部匹配。
    canonical_metadata, alias_metadata = _load_documents_metadata_maps(collection_id)

    # 构建文档内容和引用信息
    documents_with_citations = []
    citation_map = {}  # doc_name -> CitationInfo

    for i, doc in enumerate(retrieved_docs):
        # 获取文档来源
        raw_source = doc.metadata.get("document_name", doc.metadata.get("source", f"未知来源_{i+1}"))
        doc_name = url_to_name.get(raw_source, raw_source)

        # 获取元数据
        citation_info = canonical_metadata.get(doc_name) or alias_metadata.get(doc_name) or alias_metadata.get(raw_source)

        if citation_info is None:
            # 创建基础引用信息
            citation_info = CitationInfo(
                doc_id=0,
                doc_name=doc_name
            )

        # 添加证据片段
        citation_info.evidence_snippet = doc.page_content[:500] if doc.page_content else None

        # 存储到映射
        if doc_name not in citation_map:
            citation_map[doc_name] = citation_info

        documents_with_citations.append({
            "source": doc_name,
            "content": doc.page_content,
            "citation_info": citation_info.to_dict()
        })

    return {
        "documents": documents_with_citations,
        "citation_map": {name: info.to_dict() for name, info in citation_map.items()},
        "available_citations": list(citation_map.keys())
    }


def format_enhanced_references(citation_infos: List[CitationInfo]) -> str:
    """
    格式化增强版参考文献列表

    Args:
        citation_infos: 引用信息列表

    Returns:
        格式化的参考文献字符串
    """
    if not citation_infos:
        return ""

    lines = ["**引用片段索引：**"]
    for i, info in enumerate(citation_infos, 1):
        lines.append(info.format_citation(i))

    return "\n".join(lines)


def normalize_citation_index_section(answer_content: str) -> str:
    """将答案末尾的参考文献区块统一规范为“引用片段索引”。"""
    if not answer_content:
        return answer_content

    normalized = answer_content
    normalized = normalized.replace("**参考文献：**", "**引用片段索引：**")
    normalized = normalized.replace("**参考文献**", "**引用片段索引**")
    normalized = normalized.replace("\n参考文献：", "\n引用片段索引：")
    normalized = normalized.replace("\n参考文献\n", "\n引用片段索引\n")

    normalized = re.sub(
        r'(^|\n)\*{0,2}\s*参考文献\s*[:：]\s*\*{0,2}',
        lambda match: f"{match.group(1)}**引用片段索引：**",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r'(^|\n)\*{0,2}\s*参考文献\s*\*{0,2}(?=\n)',
        lambda match: f"{match.group(1)}**引用片段索引：**",
        normalized,
        flags=re.IGNORECASE,
    )

    return normalized
