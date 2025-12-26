-- 创建文档向量表（用于存储文档级别的嵌入向量）
-- 使用 pgvector 扩展存储向量数据

-- 确保 pgvector 扩展已安装
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建文档向量表
CREATE TABLE IF NOT EXISTS document_embedding (
    document_id INTEGER PRIMARY KEY,
    embedding vector(1024) NOT NULL,  -- bge-m3 模型的向量维度是 1024
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE CASCADE
);

-- 创建向量索引以加速相似度搜索（使用 HNSW 索引）
CREATE INDEX IF NOT EXISTS document_embedding_vector_idx 
ON document_embedding 
USING hnsw (embedding vector_cosine_ops);

-- 添加注释
COMMENT ON TABLE document_embedding IS '存储文档级别的嵌入向量，使用 pgvector 扩展';
COMMENT ON COLUMN document_embedding.document_id IS '关联到 document 表的 ID';
COMMENT ON COLUMN document_embedding.embedding IS '文档的嵌入向量（1024 维，使用 bge-m3 模型生成）';

