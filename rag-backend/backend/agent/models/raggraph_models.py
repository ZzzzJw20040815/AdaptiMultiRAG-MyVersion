from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


class RetrievalMode:
    """检索模式常量类

    使用字符串常量而不是枚举，避免LangGraph状态序列化问题
    """
    VECTOR_ONLY = "vector_only"
    GRAPH_ONLY = "graph_only"
    NO_RETRIEVAL = "no_retrieval"
    AUTO = "auto"


@dataclass
class RetrievedDocument:
    """检索到的文档"""
    page_content: str  # 文档内容
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据，包含document_name, chunk_index, chunk_size, pk等


@dataclass
class CitationSource:
    """
    引用来源 (PR-7)
    
    用于结构化存储 RAG 回答中的引用信息，支持精确溯源
    """
    # 引用标识
    citation_id: int                        # 引用编号 [1], [2], ...
    
    # 来源文档
    doc_id: Optional[int] = None            # 知识库文档 ID
    doc_name: Optional[str] = None          # 文档名称
    source_url: Optional[str] = None        # 原始来源 URL
    
    # 位置信息
    page_number: Optional[int] = None       # 页码
    section: Optional[str] = None           # 章节标题
    char_start: Optional[int] = None        # 字符起始位置
    char_end: Optional[int] = None          # 字符结束位置
    
    # 引用内容
    cited_text: Optional[str] = None        # 被引用的原文片段
    relevance_score: Optional[float] = None # 相关性分数
    
    # 学术元数据 (如果有)
    paper_title: Optional[str] = None       # 论文标题
    authors: Optional[List[str]] = None     # 作者列表
    publication_year: Optional[int] = None  # 发表年份
    doi: Optional[str] = None               # DOI
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，过滤 None 值"""
        return {k: v for k, v in {
            "citation_id": self.citation_id,
            "doc_id": self.doc_id,
            "doc_name": self.doc_name,
            "source_url": self.source_url,
            "page_number": self.page_number,
            "section": self.section,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "cited_text": self.cited_text,
            "relevance_score": self.relevance_score,
            "paper_title": self.paper_title,
            "authors": self.authors,
            "publication_year": self.publication_year,
            "doi": self.doi,
        }.items() if v is not None}
    
    def to_display_string(self) -> str:
        """生成用于显示的引用字符串"""
        parts = []
        
        if self.paper_title:
            parts.append(f'"{self.paper_title}"')
        elif self.doc_name:
            parts.append(self.doc_name)
        
        if self.authors:
            if len(self.authors) > 2:
                parts.append(f"{self.authors[0]} et al.")
            else:
                parts.append(", ".join(self.authors))
        
        if self.publication_year:
            parts.append(f"({self.publication_year})")
        
        if self.page_number:
            parts.append(f"p.{self.page_number}")
        elif self.section:
            parts.append(f"§{self.section}")
        
        return " ".join(parts) if parts else f"Source {self.citation_id}"
    
    @classmethod
    def from_retrieved_doc(cls, doc: RetrievedDocument, citation_id: int) -> "CitationSource":
        """从 RetrievedDocument 构建 CitationSource"""
        metadata = doc.metadata or {}
        
        return cls(
            citation_id=citation_id,
            doc_id=metadata.get("doc_id"),
            doc_name=metadata.get("doc_name") or metadata.get("document_name"),
            source_url=metadata.get("source_url"),
            page_number=metadata.get("page_number"),
            section=metadata.get("section"),
            char_start=metadata.get("char_start"),
            char_end=metadata.get("char_end"),
            cited_text=doc.page_content[:500] if doc.page_content else None,  # 截取前500字符
            relevance_score=metadata.get("relevance_score") or metadata.get("score"),
            paper_title=metadata.get("paper_title"),
            authors=metadata.get("authors"),
            publication_year=metadata.get("publication_year"),
            doi=metadata.get("doi"),
        )