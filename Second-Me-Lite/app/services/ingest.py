from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.models.document import Document, Chunk
from app.core.vector import get_collection
import uuid

def process_upload(db: Session, file: UploadFile):
    # 1. Read file content
    content = file.file.read().decode("utf-8") # Assume text/md file for simplicity
    
    # 2. Create Document record
    doc = Document(filename=file.filename, content=content)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # 3. Chunking (Simple character split)
    chunk_size = 500
    overlap = 50
    chunks = []
    
    start = 0
    text_len = len(content)
    chunk_index = 0
    
    vector_ids = []
    vector_docs = []
    vector_metadatas = []
    
    while start < text_len:
        end = start + chunk_size
        chunk_text = content[start:end]
        
        # Save to DB
        db_chunk = Chunk(
            document_id=doc.id,
            content=chunk_text,
            chunk_index=chunk_index,
            metadata_json="{}"
        )
        db.add(db_chunk)
        chunks.append(db_chunk)
        
        # Prepare for Vector DB
        vector_ids.append(f"doc_{doc.id}_chunk_{chunk_index}")
        vector_docs.append(chunk_text)
        vector_metadatas.append({"document_id": doc.id, "filename": file.filename})
        
        start += (chunk_size - overlap)
        chunk_index += 1
        
    db.commit()
    
    # 4. Save to ChromaDB
    collection = get_collection()
    collection.add(
        ids=vector_ids,
        documents=vector_docs,
        metadatas=vector_metadatas
    )
    
    return {"document_id": doc.id, "chunks_count": len(chunks)}
