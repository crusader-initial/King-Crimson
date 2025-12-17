from pathlib import Path
from .base_processor import BaseFileProcessor
from .file_types import FileType
from .document_result import DocumentResult
import logging

logger = logging.getLogger(__name__)

try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("pypdf 未安装，PDF 处理功能不可用")


class PDFProcessor(BaseFileProcessor):
    """PDF 文件处理器"""
    
    SUPPORTED_TYPES = [FileType.PDF]

    @classmethod
    def _process_file(cls, path: Path, file_type: FileType) -> DocumentResult:
        """处理 PDF 文件"""
        if not PDF_AVAILABLE:
            raise ImportError("pypdf 未安装，无法处理 PDF 文件。请运行: pip install pypdf")
        
        try:
            reader = PdfReader(path)
            content_parts = []
            
            # 提取所有页面的文本
            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    text = page.extract_text()
                    if text.strip():
                        content_parts.append(text)
                except Exception as e:
                    logger.warning(f"提取 PDF 第 {page_num} 页失败: {str(e)}")
                    continue
            
            content = "\n\n".join(content_parts)
            
            if not content.strip():
                logger.warning(f"PDF 文件 {path} 未提取到文本内容")
            
            logger.info(f"成功处理 PDF 文件: {path}, 页数: {len(reader.pages)}")
            
            return DocumentResult(
                raw_content=content,
                mime_type=FileType.get_mime_type(file_type),
                file_type=file_type.value,
                file_path=str(path),
                file_size=cls._get_file_size(path),
                metadata={
                    "page_count": len(reader.pages),
                    "extracted_pages": len(content_parts)
                }
            )
        except Exception as e:
            logger.error(f"处理 PDF 文件失败: {path}, 错误: {str(e)}", exc_info=True)
            raise

