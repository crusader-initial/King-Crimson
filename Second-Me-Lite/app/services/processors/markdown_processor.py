from pathlib import Path
from .base_processor import BaseFileProcessor
from .file_types import FileType
from .document_result import DocumentResult
import logging

logger = logging.getLogger(__name__)


class MarkdownProcessor(BaseFileProcessor):
    """Markdown 文件处理器"""
    
    SUPPORTED_TYPES = [FileType.MARKDOWN]

    @classmethod
    def _process_file(cls, path: Path, file_type: FileType) -> DocumentResult:
        """处理 Markdown 文件"""
        try:
            # Markdown 文件通常使用 UTF-8 编码
            encodings = ['utf-8', 'gbk', 'gb2312']
            content = None
            encoding_used = None
            
            for encoding in encodings:
                try:
                    with open(path, 'r', encoding=encoding) as f:
                        content = f.read()
                        encoding_used = encoding
                        break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                raise ValueError(f"无法使用常见编码读取文件: {path}")
            
            logger.info(f"成功读取 Markdown 文件: {path}, 编码: {encoding_used}")
            
            return DocumentResult(
                raw_content=content,
                mime_type=FileType.get_mime_type(file_type),
                file_type=file_type.value,
                file_path=str(path),
                file_size=cls._get_file_size(path),
                metadata={"encoding": encoding_used}
            )
        except Exception as e:
            logger.error(f"处理 Markdown 文件失败: {path}, 错误: {str(e)}", exc_info=True)
            raise

