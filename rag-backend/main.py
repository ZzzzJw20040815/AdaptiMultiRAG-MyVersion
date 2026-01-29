#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG Backend 主入口
"""
# 首先加载环境变量（必须在导入其他模块之前）
import os
import sys
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), "backend", ".env")
load_dotenv(env_path, override=True)

# Windows 下需要设置事件循环策略以支持 subprocess（Playwright 需要）
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# 然后导入其他模块
from backend.config.log import setup_default_logging, get_logger
from fastapi import FastAPI
from backend.api import rag, chat, auth, crawl, knowledge_library, visual_graph, kg_task
import uvicorn
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理"""
    # 启动时执行（环境变量已在模块级别加载）
    setup_default_logging() # 初始化日志

    logger = get_logger(__name__)
    logger.info("FastAPI 应用启动中...")
    yield
    # 关闭时执行（如果需要清理资源）

app = FastAPI(title="RAG Demo API", version="1.0.0", lifespan=lifespan)

app.include_router(rag.router)
app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(crawl.router)
app.include_router(knowledge_library.router)
app.include_router(visual_graph.router)
app.include_router(kg_task.router)

@app.get("/health")
async def read_root():
    return {"message": "Hello, FastAPI!"}    

def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
