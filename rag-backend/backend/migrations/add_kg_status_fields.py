"""数据库迁移脚本 - 添加知识图谱状态字段

为 knowledge_libraries 表添加以下字段:
- kg_status: 知识图谱状态 (pending/running/paused/completed/cancelled/failed)
- kg_total_chunks: 总分块数
- kg_processed_chunks: 已处理分块数
- kg_error_message: 错误信息

运行方式: cd rag-backend && uv run python -m backend.migrations.add_kg_status_fields
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text, inspect
from backend.config.database import DatabaseFactory


def migrate():
    """执行迁移"""
    engine = DatabaseFactory.get_engine()
    inspector = inspect(engine)
    
    # 获取现有列
    columns = [col['name'] for col in inspector.get_columns('knowledge_libraries')]
    
    migrations_needed = []
    
    if 'kg_status' not in columns:
        migrations_needed.append(
            "ALTER TABLE knowledge_libraries ADD COLUMN kg_status VARCHAR(20) DEFAULT 'pending' NOT NULL"
        )
    
    if 'kg_total_chunks' not in columns:
        migrations_needed.append(
            "ALTER TABLE knowledge_libraries ADD COLUMN kg_total_chunks INT DEFAULT 0 NOT NULL"
        )
    
    if 'kg_processed_chunks' not in columns:
        migrations_needed.append(
            "ALTER TABLE knowledge_libraries ADD COLUMN kg_processed_chunks INT DEFAULT 0 NOT NULL"
        )
    
    if 'kg_error_message' not in columns:
        migrations_needed.append(
            "ALTER TABLE knowledge_libraries ADD COLUMN kg_error_message TEXT"
        )
    
    if not migrations_needed:
        print("✅ 所有字段已存在，无需迁移")
        return
    
    print(f"📦 需要添加 {len(migrations_needed)} 个字段...")
    
    with engine.connect() as conn:
        for sql in migrations_needed:
            print(f"  执行: {sql}")
            conn.execute(text(sql))
        conn.commit()
    
    print("✅ 迁移完成！")


if __name__ == "__main__":
    migrate()
