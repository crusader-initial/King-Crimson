from pathlib import Path
from typing import Optional
import logging
from .file_types import FileType, UnsupportedFileType
from .base_processor import BaseFileProcessor
from .document_result import DocumentResult
from .text_processor import TextProcessor
from .pdf_processor import PDFProcessor
from .markdown_processor import MarkdownProcessor

logger = logging.getLogger(__name__)


class ProcessorFactory:
    """文件处理器工厂类"""
    
    # 注册所有可用的处理器
    _processors = {
        FileType.TEXT: TextProcessor,
        FileType.PDF: PDFProcessor,
        FileType.MARKDOWN: MarkdownProcessor,
    }

    @classmethod
    def get_processor(cls, file_type: FileType) -> BaseFileProcessor:
        """根据文件类型获取对应的处理器"""
        processor = cls._processors.get(file_type)
        if processor is None:
            raise UnsupportedFileType(f"No processor available for file type: {file_type}")
        return processor

    @classmethod
    def auto_detect_and_process(cls, file_path: str) -> DocumentResult:
        """
        自动检测文件类型并处理
        :param file_path: 文件路径
        :return: DocumentResult 对象
        """
        logger.info("可用处理器: %s", list(cls._processors.keys()))
        path = Path(file_path)
        
        # 使用 BaseFileProcessor 的类型检测方法
        file_type = BaseFileProcessor._detect_type(path, None)
        
        # 获取对应的处理器并处理
        processor = cls.get_processor(file_type)
        return processor.process(file_path)

