# AdaptiMultiRAG 启动指南

本指南将帮助你从零开始启动 AdaptiMultiRAG 系统。

## 1. 启动基础设施 (Docker)

在运行任何代码之前，必须先启动数据库和中间件服务。

1.  打开终端，进入项目根目录。
2.  确保 **Docker Desktop** 已启动。
3.  运行以下命令启动服务 (MySQL, PostgreSQL, Neo4j, Redis, Milvus, MinIO)：

    ```powershell
    # 在 rag-backend 目录下运行
    cd rag-backend
    docker-compose -f backend/docker-compose-full.yml up -d
    ```

4.  **初始化数据库** (仅首次启动或清空数据后需要)：
    确保 Docker 容器全部变绿 (Running) 后，运行：
    ```powershell
    uv run python backend/init_db.py
    ```
    *如果看到 "数据库初始化完成!"，则说明环境准备就绪。*

---

## 2. 配置 API Key

确保你已经配置了阿里云 Qwen 模型的 API Key，否则无法进行对话。

1.  打开文件：`rag-backend/backend/.env`
2.  找到 `DASHSCOPE_API_KEY=`
3.  填入你的阿里云 DashScope API Key。
    *注意：无需修改 S3 配置，默认已配置为本地 MinIO。*

---

## 3. 启动后端 (Backend)

在一个新的终端窗口中：

```powershell
cd rag-backend
# 启动 FastAPI 服务 (开发模式)
uv run uvicorn main:app --host 0.0.0.0 --port 8888 --reload

uv run python -c "import asyncio; asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy()); import uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=8888)"
```
*   当看到 `Application startup complete.` 时，后端已成功启动。
*   API 文档地址：http://localhost:8888/docs

---

## 4. 启动前端 (Frontend)

在另一个新的终端窗口中：

```powershell
cd rag-frontend
# 启动 Vue 开发服务
npm run dev
```
*   启动成功后，按住 Ctrl 点击终端显示的链接 (通常是 http://localhost:5173) 即可并在浏览器中打开系统。

---

## 常见问题

*   **数据库连接失败**: 如果 `init_db.py` 报错，通常是因为 Docker 容器还在启动中。请等待 10-20 秒后重试。
*   **Docker 空间不足**: 如果 C 盘爆满，请参考我们之前的对话，在 Docker Settings -> Resources 中迁移 Disk image location 到其他盘。

---

## 5. 启动 LangGraph

# 先进入目录
cd rag-backend

# 启动 (带上编码修正 + uv run)
$env:PYTHONUTF8="1"; uv run langgraph dev


非常简单，就像按那个“撤销/重做”按钮一样方便。你只需要在终端运行下面这两个命令：

1. 切换到“现在的修改”（找回那 27 个文件）
powershell
git checkout temp-save-work
这时你会看到你的代码全回来了。

2. 切换到“最初的修改”（回到干净的状态）
powershell
git checkout main
这时你会看到文件又变回了原来的样子。

小贴士： 如果你不确定自己现在在哪儿，可以随时输入：

powershell
git branch
带星号 * 和绿色高亮的就是你当前所在的分支。

账号：admin@example.com

密码：admin123


• 最方便的是用 Mermaid CLI（mmdc）直接生成 svg/png。

  1. CLI（推荐，1‑2 条命令）

  # 全局安装一次
  npm i -g @mermaid-js/mermaid-cli

  # 生成 SVG
  mmdc -i rag-backend/docs/raggraph-flow.mmd -o rag-backend/docs/raggraph-flow.svg

  # 生成 PNG（可选）
  mmdc -i rag-backend/docs/raggraph-flow.mmd -o rag-backend/docs/raggraph-flow.png

  2. VS Code（无命令行）

  - 装 Mermaid Preview/Markdown Mermaid 扩展
  - 打开 rag-backend/docs/raggraph-flow.mmd → 预览 → 导出图片

  如果你希望我在这里直接生成图片，告诉我要 svg 还是 png。
