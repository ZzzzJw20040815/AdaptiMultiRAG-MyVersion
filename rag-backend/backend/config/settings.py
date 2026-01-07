#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理中心 (PR-12)

集中管理所有可配置项:
- 环境变量映射
- 默认值定义
- 配置验证
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = field(default_factory=lambda: os.getenv("MYSQL_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("MYSQL_PORT", "3306")))
    user: str = field(default_factory=lambda: os.getenv("MYSQL_USER", "root"))
    password: str = field(default_factory=lambda: os.getenv("MYSQL_PASSWORD", ""))
    database: str = field(default_factory=lambda: os.getenv("MYSQL_DATABASE", "rag_db"))
    
    @property
    def url(self) -> str:
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class MilvusConfig:
    """Milvus 向量数据库配置"""
    host: str = field(default_factory=lambda: os.getenv("MILVUS_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("MILVUS_PORT", "19530")))
    
    @property
    def uri(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class Neo4jConfig:
    """Neo4j 图数据库配置"""
    uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    user: str = field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    password: str = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", ""))


@dataclass
class RedisConfig:
    """Redis 配置"""
    host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    password: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_PASSWORD"))
    db: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))


@dataclass
class MinIOConfig:
    """MinIO 对象存储配置"""
    endpoint: str = field(default_factory=lambda: os.getenv("MINIO_ENDPOINT", "localhost:9000"))
    access_key: str = field(default_factory=lambda: os.getenv("MINIO_ACCESS_KEY", ""))
    secret_key: str = field(default_factory=lambda: os.getenv("MINIO_SECRET_KEY", ""))
    bucket: str = field(default_factory=lambda: os.getenv("MINIO_BUCKET", "rag-files"))
    secure: bool = field(default_factory=lambda: os.getenv("MINIO_SECURE", "false").lower() == "true")


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "dashscope"))
    api_key: str = field(default_factory=lambda: os.getenv("LLM_DASHSCOPE_API_KEY", ""))
    api_base: str = field(default_factory=lambda: os.getenv("LLM_DASHSCOPE_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1"))
    chat_model: str = field(default_factory=lambda: os.getenv("LLM_DASHSCOPE_CHAT_MODEL", "qwen-plus"))
    

@dataclass
class EmbeddingConfig:
    """Embedding 配置"""
    provider: str = field(default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "dashscope"))
    api_key: str = field(default_factory=lambda: os.getenv("VECTOR_DASHSCOPE_API_KEY", ""))
    model: str = field(default_factory=lambda: os.getenv("VECTOR_DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4"))
    dimension: int = field(default_factory=lambda: int(os.getenv("EMBEDDING_DIM", "1024")))


@dataclass
class RAGConfig:
    """RAG 流程配置"""
    max_retrieval_docs: int = field(default_factory=lambda: int(os.getenv("RAG_MAX_RETRIEVAL_DOCS", "5")))
    relevance_threshold: float = field(default_factory=lambda: float(os.getenv("RAG_RELEVANCE_THRESHOLD", "0.5")))
    enable_reranking: bool = field(default_factory=lambda: os.getenv("RAG_ENABLE_RERANKING", "true").lower() == "true")
    chunk_size: int = field(default_factory=lambda: int(os.getenv("RAG_CHUNK_SIZE", "500")))
    chunk_overlap: int = field(default_factory=lambda: int(os.getenv("RAG_CHUNK_OVERLAP", "50")))


@dataclass
class AppConfig:
    """应用总配置"""
    # 服务器配置
    host: str = field(default_factory=lambda: os.getenv("APP_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("APP_PORT", "8000")))
    debug: bool = field(default_factory=lambda: os.getenv("APP_DEBUG", "false").lower() == "true")
    
    # 子配置
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    milvus: MilvusConfig = field(default_factory=MilvusConfig)
    neo4j: Neo4jConfig = field(default_factory=Neo4jConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    minio: MinIOConfig = field(default_factory=MinIOConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    
    def validate(self) -> list:
        """验证配置完整性"""
        errors = []
        
        if not self.llm.api_key:
            errors.append("LLM API Key 未配置")
        if not self.embedding.api_key:
            errors.append("Embedding API Key 未配置")
        if not self.database.password:
            errors.append("数据库密码未配置")
        
        return errors
    
    def to_dict(self) -> dict:
        """转换为字典（隐藏敏感信息）"""
        return {
            "app": {"host": self.host, "port": self.port, "debug": self.debug},
            "database": {"host": self.database.host, "port": self.database.port},
            "milvus": {"host": self.milvus.host, "port": self.milvus.port},
            "neo4j": {"uri": self.neo4j.uri},
            "redis": {"host": self.redis.host, "port": self.redis.port},
            "minio": {"endpoint": self.minio.endpoint, "bucket": self.minio.bucket},
            "llm": {"provider": self.llm.provider, "model": self.llm.chat_model},
            "embedding": {"provider": self.embedding.provider, "model": self.embedding.model},
            "rag": {
                "max_docs": self.rag.max_retrieval_docs,
                "threshold": self.rag.relevance_threshold,
                "reranking": self.rag.enable_reranking,
            }
        }


# 全局配置实例
config = AppConfig()


def get_config() -> AppConfig:
    """获取全局配置"""
    return config


def print_config():
    """打印当前配置（调试用）"""
    import json
    print("=== AdaptiMultiRAG 配置 ===")
    print(json.dumps(config.to_dict(), indent=2, ensure_ascii=False))
    
    errors = config.validate()
    if errors:
        print("\n⚠️ 配置警告:")
        for err in errors:
            print(f"  - {err}")
