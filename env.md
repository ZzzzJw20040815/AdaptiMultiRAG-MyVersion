# ============================================================================
# RAG Backend Environment Configuration
# ============================================================================

# --- Database Configuration ---
# MySQL (Service: mysql)
DB_URL=mysql+pymysql://root:password@localhost:3306/rag_db

# PostgreSQL (Service: postgres)
# Used for LangGraph Checkpoint & Memory
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=rag_checkpoint
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# Redis (Service: redis)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# --- Vector & Graph Database ---
# Milvus (Service: standalone)
MILVUS_URI=http://localhost:19530
MILVUS_DB_NAME=default

# Neo4j (Service: neo4j)
# Required for Knowledge Graph
NEO4J_URI=bolt://localhost:17687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# LightRAG Configuration
LIGHTRAG_GRAPH_STORAGE=Neo4JStorage
LIGHTRAG_VECTOR_STORAGE=MilvusVectorDBStorage
LIGHTRAG_KV_STORAGE=PGKVStorage
LIGHTRAG_DOC_STATUS_STORAGE=PGDocStatusStorage

# --- LLM & Embedding (Aliyun Qwen) ---
DASHSCOPE_API_KEY=sk-a2bc50198f6a4b7ea832fa375df5d0bf

# LLM Model (Chat)
LLM_DASHSCOPE_CHAT_MODEL=qwen-turbo-2025-07-15

# Embedding Model
VECTOR_DASHSCOPE_API_KEY=sk-a2bc50198f6a4b7ea832fa375df5d0bf
VECTOR_DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4
#VECTOR_DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4

# Embedding API Base (LightRAG 需要)
VECTOR_DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1

# Embedding 维度
EMBEDDING_DIM=1024

# --- Storage Configuration (S3 Compatible) ---
# Option 1: Local MinIO (Default, Free)
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=rag-data
S3_REGION=us-east-1

# --- Application Security ---
JWT_SECRET_KEY=dev_secret_key_change_me_123456
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRES=86400

# --- App Settings ---
APP_ENV=development
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8888

# LightRAG LLM 配置 (知识图谱实体抽取用)
LLM_DASHSCOPE_API_KEY=sk-a2bc50198f6a4b7ea832fa375df5d0bf
LLM_DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1

# --- LangSmith Monitoring ---
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=lsv2_pt_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LANGCHAIN_PROJECT=rag_agent_demo