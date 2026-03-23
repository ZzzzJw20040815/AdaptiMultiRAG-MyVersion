#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PR-1 迁移脚本：为 knowledge_documents 表添加学术元数据字段

运行方式：
    cd rag-backend
    uv run python backend/migrations/add_academic_metadata_fields.py
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

# 加载环境变量
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

from sqlalchemy import create_engine, text

def run_migration():
    """执行数据库迁移"""
    db_url = os.getenv('DB_URL')
    if not db_url:
        print("错误: 未找到 DB_URL 环境变量")
        return False

    print(f"连接数据库...")
    engine = create_engine(db_url)

    # 要添加的字段
    columns_to_add = [
        ("academic_title", "VARCHAR(500) NULL COMMENT '论文标题'"),
        ("authors", "TEXT NULL COMMENT '作者列表，JSON格式'"),
        ("abstract", "TEXT NULL COMMENT '摘要'"),
        ("keywords", "TEXT NULL COMMENT '关键词，JSON格式'"),
        ("publish_year", "INT NULL COMMENT '发表年份'"),
        ("doi", "VARCHAR(100) NULL COMMENT 'DOI标识'"),
        ("source_type", "VARCHAR(20) NOT NULL DEFAULT 'unknown' COMMENT '来源类型'"),
        ("parse_status", "VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '解析状态'"),
        ("parse_error", "TEXT NULL COMMENT '解析错误信息'"),
    ]

    with engine.connect() as conn:
        for column_name, column_def in columns_to_add:
            try:
                # 检查字段是否已存在
                check_sql = text(f"""
                    SELECT COUNT(*)
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = 'knowledge_documents'
                    AND COLUMN_NAME = '{column_name}'
                """)
                result = conn.execute(check_sql)
                exists = result.scalar() > 0

                if exists:
                    print(f"  ✓ 字段 {column_name} 已存在，跳过")
                else:
                    # 添加字段
                    alter_sql = text(f"ALTER TABLE knowledge_documents ADD COLUMN {column_name} {column_def}")
                    conn.execute(alter_sql)
                    conn.commit()
                    print(f"  ✓ 成功添加字段: {column_name}")

            except Exception as e:
                print(f"  ✗ 添加字段 {column_name} 失败: {str(e)}")
                return False

    print("\n迁移完成!")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("PR-1 数据库迁移: 添加学术元数据字段")
    print("=" * 50)
    print()

    success = run_migration()

    if success:
        print("\n所有字段已成功添加到 knowledge_documents 表")
    else:
        print("\n迁移过程中出现错误")
        sys.exit(1)
