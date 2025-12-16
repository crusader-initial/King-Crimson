# Second-Me-Lite

这是 `Second-Me` 的轻量化重构版本，专注于核心的 RAG 对话功能，并采用远程服务架构。

## 特性

*   **导入 (Ingestion)**: 上传文本文档，自动切片并生成向量存储到 PostgreSQL。
*   **文件管理**: 支持文件上传、删除，包含格式验证、重复检查、文件存储等功能。
*   **对话 (Chat)**: 基于 RAG (检索增强生成) 的对话接口，调用远程 LLM API。
*   **架构**:
    *   Web 框架: FastAPI
    *   数据库: PostgreSQL (with PGVector)
    *   向量存储: PostgreSQL PGVector 扩展
    *   LLM: OpenAI 兼容接口 (Remote)

## 目录结构

```
Second-Me-Lite/
├── app/
│   ├── api/            # 路由定义
│   ├── core/           # 核心配置 (DB, Vector, Config)
│   ├── models/         # 数据库模型 (SQLAlchemy)
│   ├── services/       # 业务逻辑 (Chat, FileService)
│   └── main.py         # 应用入口
├── requirements.txt    # 依赖列表
└── .env.example        # 环境变量示例
```

## 快速开始

### 1. 环境准备

确保你已安装 Python 3.10+。

```bash
cd Second-Me-Lite
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的远程服务配置：

```bash
cp .env.example .env
```

*   **MYSQL_***: 配置你的远程 MySQL 数据库连接。
*   **CHROMA_***: 配置你的远程 ChromaDB 地址 (e.g. `http://localhost:8000`)。
*   **OPENAI_***: 配置你的 LLM API Key 和 Base URL。

### 3. 运行服务

```bash
uvicorn app.main:app --reload
```

服务将在 `http://localhost:8000` 启动。

### 4. API 使用指南

访问 Swagger UI 文档: `http://localhost:8000/docs`

#### 文件管理接口

*   **POST /api/file**: 文件上传接口
    *   支持格式: txt, pdf, md
    *   功能: 文件格式验证、重复检查（通过文件名和大小）、保存到磁盘、自动切片和生成向量
    *   请求: `multipart/form-data`，字段 `file`（文件）和可选的 `metadata`（JSON 字符串）
    *   响应: 返回文档信息和处理结果
    
*   **DELETE /api/file/{filename}**: 文件删除接口
    *   功能: 删除文件记录、相关 chunks、向量数据以及物理文件
    *   参数: `filename`（文件名）

#### 其他接口

*   **POST /api/chat**: 发送对话请求 `{"query": "你的问题"}`。
