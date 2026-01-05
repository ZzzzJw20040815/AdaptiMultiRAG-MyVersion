"""RAG系统数据模型定义"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from langchain_core.documents import Document


class ChunkStrategy(Enum):
    """分块策略枚举"""
    CHARACTER = "character"          # 字符级分块
    SEMANTIC = "semantic"           # 语义分块
    RECURSIVE = "recursive"         # 递归分块
    MARKDOWN_HEADER = "markdown_header"  # Markdown标题分块


@dataclass
class ChunkMetadata:
    """
    分块元数据 (PR-5)
    
    用于记录每个分块的来源和位置信息，支持精确溯源
    """
    # 文档标识
    doc_id: Optional[int] = None            # 知识库文档 ID
    doc_name: Optional[str] = None          # 文档名称
    source_url: Optional[str] = None        # 原始来源 URL
    
    # 位置信息
    page_number: Optional[int] = None       # 页码 (PDF)
    section: Optional[str] = None           # 章节标题
    section_hierarchy: Optional[List[str]] = None  # 章节层级 (如 ["Chapter 1", "Section 1.1"])
    
    # 字符范围
    char_start: Optional[int] = None        # 在原文中的起始位置
    char_end: Optional[int] = None          # 在原文中的结束位置
    
    # 分块信息
    chunk_index: Optional[int] = None       # 分块索引 (第几个分块)
    total_chunks: Optional[int] = None      # 总分块数
    
    # 时间戳
    created_at: Optional[str] = None        # 创建时间
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，过滤 None 值"""
        return {k: v for k, v in {
            "doc_id": self.doc_id,
            "doc_name": self.doc_name,
            "source_url": self.source_url,
            "page_number": self.page_number,
            "section": self.section,
            "section_hierarchy": self.section_hierarchy,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "created_at": self.created_at,
        }.items() if v is not None}


@dataclass
class DocumentContent:
    """
    文档内容数据类型
    
    PR-5 扩展: 支持额外的源文档信息
    """
    content: str        # 文档文本内容
    document_name: str  # 文档名称
    
    # PR-5: 扩展字段，用于溯源
    doc_id: Optional[int] = None        # 知识库文档 ID
    source_url: Optional[str] = None    # 原始来源 URL
    page_numbers: Optional[List[int]] = None  # 页码列表 (PDF)
    extra_metadata: Optional[Dict[str, Any]] = None  # 额外元数据


@dataclass
class ChunkConfig:
    """分块配置"""
    strategy: ChunkStrategy
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # 字符分块专用参数
    separator: str = ""
    is_separator_regex: bool = False
    
    # 语义分块专用参数
    breakpoint_threshold_type: str = "percentile"
    breakpoint_threshold_amount: float = 95
    min_chunk_size: Optional[int] = None
    sentence_split_regex: str = r'[。！？.\n]'
    
    # 递归分块专用参数
    separators: List[str] = None
    
    # Markdown分块专用参数
    headers_to_split_on: List[tuple] = None
    
    # PR-5: 是否添加溯源元数据
    add_source_metadata: bool = True

    def __post_init__(self):
        """初始化默认值"""
        if self.separators is None and self.strategy == ChunkStrategy.RECURSIVE:
            self.separators = ["\n\n", "。", "，", " ", ""]
            
        if self.headers_to_split_on is None and self.strategy == ChunkStrategy.MARKDOWN_HEADER:
            self.headers_to_split_on = [
                ("#", "Header_1"),
                ("##", "Header_2"), 
                ("###", "Header_3"),
                ("####", "Header_4"),
                ("#####", "Header_5"),
                ("######", "Header_6")
            ]


@dataclass
class ChunkResult:
    """分块结果"""
    chunks: List[Document]           # 分块后的文档列表
    strategy: ChunkStrategy          # 使用的分块策略
    total_chunks: int               # 总块数
    document_name: str              # 原文档名称
    
    # PR-5: 扩展字段
    doc_id: Optional[int] = None    # 知识库文档 ID
    source_url: Optional[str] = None  # 原始来源 URL