from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, func, JSON
from sqlalchemy.orm import relationship
from enum import Enum
import uuid
from backend.utils.timezone import to_china_time
from backend.config.database import DatabaseFactory

Base = DatabaseFactory.get_base()


class ParseStatus(str, Enum):
    """文档解析状态枚举"""
    PENDING = "pending"          # 待处理
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 处理完成
    FAILED = "failed"            # 处理失败


class KnowledgeLibrary(Base):
    """知识库模型"""
    __tablename__ = 'knowledge_libraries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    collection_id = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False, comment='知识库唯一标识UUID')
    title = Column(String(200), nullable=False, comment='知识库标题')
    description = Column(Text, nullable=True, comment='知识库描述')
    user_id = Column(String(100), nullable=False, comment='创建用户ID')
    is_active = Column(Boolean, default=True, nullable=False, comment='是否激活')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')
    
    # 关联文档
    documents = relationship("KnowledgeDocument", back_populates="library", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'collection_id': self.collection_id,
            'title': self.title,
            'description': self.description,
            'user_id': self.user_id,
            'is_active': self.is_active,
            'documents': [doc.to_dict() for doc in self.documents] if self.documents else [],
            'created_at': to_china_time(self.created_at).isoformat() if self.created_at else None,
            'updated_at': to_china_time(self.updated_at).isoformat() if self.updated_at else None
        }


class KnowledgeDocument(Base):
    """知识库文档模型"""
    __tablename__ = 'knowledge_documents'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    library_id = Column(Integer, ForeignKey('knowledge_libraries.id'), nullable=False, comment='所属知识库ID')
    name = Column(String(200), nullable=False, comment='文档名称')
    type = Column(String(20), nullable=False, comment='文档类型：link, file, pdf等')
    url = Column(String(500), nullable=True, comment='文档链接地址')
    file_path = Column(String(500), nullable=True, comment='文件存储路径')
    file_size = Column(Integer, nullable=True, comment='文件大小（字节）')
    is_processed = Column(Boolean, default=False, nullable=False, comment='是否已处理')
    
    # ==================== 学术元数据字段 (PR-1) ====================
    paper_title = Column(String(500), nullable=True, comment='论文标题（区别于文件名）')
    authors = Column(JSON, nullable=True, comment='作者列表 JSON 数组')
    affiliations = Column(JSON, nullable=True, comment='机构列表 JSON 数组')
    doi = Column(String(100), nullable=True, comment='DOI 标识符')
    abstract = Column(Text, nullable=True, comment='论文摘要')
    keywords = Column(JSON, nullable=True, comment='关键词列表 JSON 数组')
    publication_venue = Column(String(200), nullable=True, comment='发表会议/期刊')
    publication_year = Column(Integer, nullable=True, comment='发表年份')
    references = Column(JSON, nullable=True, comment='引用文献列表 JSON 数组')
    
    # ==================== 文档溯源字段 (PR-1) ====================
    source_url = Column(String(1000), nullable=True, comment='原始来源 URL')
    file_hash = Column(String(64), nullable=True, comment='文件 SHA-256 哈希')
    
    # ==================== 解析状态字段 (PR-1) ====================
    parse_status = Column(String(20), default=ParseStatus.PENDING.value, nullable=False, comment='解析状态：pending/processing/completed/failed')
    parse_error = Column(Text, nullable=True, comment='解析错误信息')
    
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')
    
    # 关联知识库
    library = relationship("KnowledgeLibrary", back_populates="documents")
    
    def to_dict(self):
        return {
            'id': self.id,
            'library_id': self.library_id,
            'name': self.name,
            'type': self.type,
            'url': self.url,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'is_processed': self.is_processed,
            # 学术元数据字段
            'paper_title': self.paper_title,
            'authors': self.authors,
            'affiliations': self.affiliations,
            'doi': self.doi,
            'abstract': self.abstract,
            'keywords': self.keywords,
            'publication_venue': self.publication_venue,
            'publication_year': self.publication_year,
            'references': self.references,
            # 溯源字段
            'source_url': self.source_url,
            'file_hash': self.file_hash,
            # 解析状态
            'parse_status': self.parse_status,
            'parse_error': self.parse_error,
            # 时间戳
            'created_at': to_china_time(self.created_at).isoformat() if self.created_at else None,
            'updated_at': to_china_time(self.updated_at).isoformat() if self.updated_at else None
        }