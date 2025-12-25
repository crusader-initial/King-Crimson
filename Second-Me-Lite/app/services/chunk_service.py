from typing import List
from sqlalchemy.orm import Session
from app.models.document import Chunk
from app.core.utils import TokenTextSplitter
import logging
import traceback

logger = logging.getLogger(__name__)


class DocumentChunker:
    """文档分块器"""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        """
        初始化文档分块器
        
        Args:
            chunk_size: 分块大小（字符数）
            overlap: 重叠大小（字符数）
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        # 使用 TokenTextSplitter 进行文本分割
        self.text_splitter = TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            encoding_name="cl100k_base"
        )
    
    def split(self, content: str) -> List[Chunk]:
        """
        将文本分割成多个块
        
        Args:
            content: 要分割的文本
            
        Returns:
            Chunk 对象列表（注意：这些 Chunk 对象还没有 document_id，需要在保存前设置）
        """
        try:
            if not content:
                logger.warning("Empty content provided")
                return []

            logger.info(f"Starting to split content of length {len(content)}")

            # use LangChain splitter
            texts = self.text_splitter.split_text(content)

            chunks = [
                Chunk(
                    id=None,
                    document_id=None,
                    content=text,
                    has_embedding=False,
                    tags=None,
                    topic=None,
                )
                for text in texts
            ]

            logger.info(f"Split completed, created {len(chunks)} chunks")
            return chunks

        except Exception as e:
            logger.error(f"Error in split method: {str(e)}")
            logger.error(traceback.format_exc())
            raise


class ChunkService:
    """Chunk 服务类，用于保存和管理 Chunk"""
    
    def __init__(self, db: Session = None, repository=None):
        """
        初始化 ChunkService
        
        Args:
            db: 数据库会话，如果为 None，则需要在调用 save_chunk 时提供
            repository: Repository 实例，如果为 None，则使用 DocumentRepository
        """
        self.db = db
        if repository is None:
            from app.services.document_repository import DocumentRepository
            self._repository = DocumentRepository()
        else:
            self._repository = repository
    
    def save_chunk(self, chunk: Chunk) -> None:
        """
        Save document chunk to database
        Args:
            chunk (Chunk): Chunk object to save
        Raises:
            Exception: Error when saving fails
        """
        try:
            # Create Chunk instance (in our case, Chunk is already the SQLAlchemy model)
            # We create a new instance to ensure clean state
            chunk_model = Chunk(
                document_id=chunk.document_id,
                content=chunk.content,
                tags=chunk.tags,
                topic=chunk.topic,
            )
            # Save to database using repository
            self._repository.save_chunk(chunk_model)
            logger.debug(f"Saved chunk for document {chunk.document_id}")
        except Exception as e:
            logger.error(f"Error saving chunk: {str(e)}")
            raise

