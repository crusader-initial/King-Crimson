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
│   └── services/       # 业务逻辑 (Chat, FileService)
├── run.py              # 应用入口和启动脚本
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

### 3. 数据库迁移

确保 PostgreSQL 数据库已安装 pgvector 扩展，然后执行以下 SQL 脚本创建向量表：

```bash
# 创建文档级别的向量表
psql -U postgres -d second_me_lite -f migrations/create_document_embedding_table.sql

# 创建 chunk 级别的向量表
psql -U postgres -d second_me_lite -f migrations/create_chunk_embedding_table.sql
```

或者直接在 PostgreSQL 客户端中执行以下迁移文件中的 SQL 语句：
- `migrations/create_document_embedding_table.sql` - 文档级别的向量表
- `migrations/create_chunk_embedding_table.sql` - chunk 级别的向量表

**注意**: 
- 文档向量表 (`document_embedding`) 用于存储文档级别的嵌入向量
- Chunk 向量表 (`chunk_embedding`) 用于存储 chunk 级别的嵌入向量
- 两者都使用 HuggingFace BAAI/bge-m3 模型生成，向量维度为 1024
- 所有向量数据都存储在 PostgreSQL 的 pgvector 扩展中

### 4. 运行服务

```bash
python run.py
```

服务将在 `http://localhost:8001` 启动。

### 5. API 使用指南

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

*   **POST /api/documents/analyze**: 批量分析所有未分析的文档接口
    *   功能: 自动查找状态为 INITIALIZED 或 FAILED 的文档进行分析
    *   响应: 返回分析结果统计

*   **POST /api/documents/chunks/process**: 批量处理所有文档的 chunks
    *   功能: 为所有文档生成 chunks 并保存到数据库
    *   响应: 返回处理结果统计

*   **POST /api/documents/{document_id}/chunk/embedding**: 为指定文档的所有 chunks 处理 embeddings
    *   功能: 为指定文档的所有 chunks 生成嵌入向量
    *   参数: `document_id`（文档ID）
    *   响应: 返回处理的 chunks 统计信息
    *   说明:
        - 为文档的所有 chunks 批量生成嵌入向量（使用 HuggingFace BAAI/bge-m3 模型）
        - 向量存储到 PostgreSQL 的 `chunk_embedding` 表中（使用 pgvector 扩展）
        - 同时更新 `chunk` 表的 `has_embedding` 状态为 `true`
        - 向量维度为 1024（bge-m3 模型的维度）

*   **POST /api/documents/{document_id}/embedding**: 处理文档级别的嵌入向量
    *   功能: 为指定文档生成文档级别的嵌入向量（使用文档的 raw_content，使用 HuggingFace BAAI/bge-m3 模型）
    *   参数: `document_id`（文档ID）
    *   响应: 返回文档ID和嵌入向量长度
    *   说明: 
        - 如果文档内容过长，会自动分块处理，然后对分块的 embeddings 求平均
        - 向量存储到 PostgreSQL 的 `document_embedding` 表中（使用 pgvector 扩展）
        - 向量维度为 1024（bge-m3 模型的维度）

#### 用户管理接口

*   **POST /api/loads/login**: 登录或创建用户接口（根据手机号）
    *   功能: 根据手机号登录或创建用户，如果用户存在则返回用户信息，不存在则创建新用户
    *   请求体: JSON 格式
        ```json
        {
            "user_mobile": "13800138000（必填）",
            "name": "用户名（可选，创建新用户时使用）"
        }
        ```
    *   响应: 返回用户信息，包含 `is_new_user` 字段标识是否为新创建的用户
    
*   **GET /api/loads/{load_id}**: 根据用户ID获取用户信息
    *   功能: 根据用户ID获取用户详细信息
    *   参数: `load_id`（用户ID）
    *   响应: 返回用户详细信息
    
*   **PUT /api/loads/{load_id}**: 更新用户信息
    *   功能: 根据用户ID更新用户信息（支持部分更新）
    *   参数: `load_id`（用户ID）
    *   请求体: JSON 格式，所有字段可选
        ```json
        {
            "name": "新用户名",
            "description": "新描述",
            "email": "new@example.com"
        }
        ```
    *   响应: 返回更新结果

#### 状态传记接口

*   **POST /api/l1/status_bio/generate**: 生成状态传记
    *   功能: 根据角色ID获取该角色的所有文档，自动生成状态传记并存储到数据库
    *   请求体: JSON 格式
        ```json
        {
            "role_id": "角色ID（必填）"
        }
        ```
    *   响应: 返回生成的状态传记内容，包括：
        - `content`: 第二视角内容
        - `content_third_view`: 第三视角内容
        - `summary`: 第二视角摘要
        - `summary_third_view`: 第三视角摘要
        - `shades`: 特征列表（包含名称、方面、图标、描述和内容等）
    *   说明: 
        - 该接口会获取指定 `role_id` 的所有文档（包含L0数据）
        - 基于这些文档自动生成状态传记
        - 生成的状态传记会存储到 `status_biography` 表中，并关联到指定的 `role_id`
        - 如果该 `role_id` 已存在状态传记，会先删除旧的再创建新的

*   **PUT /api/status-biography/{role_id}**: 创建或更新状态传记（upsert）
    *   功能: 根据角色ID创建或更新状态传记记录
    *   参数: `role_id`（角色ID，即 `loads.id`，因为 `role.id` 和 `role.uuid` 都使用 `loads.id`）
    *   请求体: JSON 格式，所有字段可选
        ```json
        {
            "content": "状态传记内容",
            "content_third_view": "第三方视角内容",
            "summary": "摘要",
            "summary_third_view": "第三方视角摘要"
        }
        ```
    *   响应: 返回操作结果

#### L1传记接口

*   **PUT /api/l1-bios/{role_id}**: 创建或更新L1传记（upsert，按角色ID）
    *   功能: 根据角色ID创建或更新L1传记记录
    *   参数: `role_id`（角色ID，即 `loads.id`，因为 `role.id` 和 `role.uuid` 都使用 `loads.id`）
    *   请求体: JSON 格式
        ```json
        {
            "content_third_view": "第三方视角内容"
        }
        ```
    *   响应: 返回操作结果

*   **POST /api/l1-bios/{role_id}/version**: 创建新的L1传记版本（按角色ID）
    *   功能: 为指定角色创建新版本的L1传记记录
    *   参数: `role_id`（角色ID）
    *   请求体: JSON 格式
        ```json
        {
            "content_third_view": "第三方视角内容"
        }
        ```
    *   响应: 返回创建结果

#### 其他接口

*   **POST /api/chat**: 发送对话请求 `{"query": "你的问题"}`。
