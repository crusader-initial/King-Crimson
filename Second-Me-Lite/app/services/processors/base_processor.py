from pathlib import Path
from typing import Optional
import logging
from .file_types import FileType, UnsupportedFileType
from .document_result import DocumentResult

logger = logging.getLogger(__name__)


class BaseFileProcessor:
    """基础文件处理器"""
    
    SUPPORTED_TYPES = []  # 子类需要定义支持的文件类型

    @classmethod
    def _detect_type(
        cls, path: Path, expected_type: Optional[FileType] = None
    ) -> FileType:
        """检测文件类型"""
        if expected_type:
            return expected_type

        suffix = path.suffix.lower()
        mime_mapping = FileType.get_mime_mapping()

        if suffix not in mime_mapping:
            raise UnsupportedFileType(f"Unsupported file type: {suffix}")

        return mime_mapping[suffix]

    @classmethod
    def process(
        cls, file_path: str, expected_type: Optional[FileType] = None
    ) -> DocumentResult:
        """
        处理文件的主入口
        :param file_path: 文件路径
        :param expected_type: 期望的文件类型（可选）
        :return: DocumentResult 对象
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_type = cls._detect_type(path, expected_type)

        if file_type not in cls.SUPPORTED_TYPES:
            raise UnsupportedFileType(f"{cls.__name__} doesn't support {file_type}")

        return cls._process_file(path, file_type)

    @classmethod
    def _process_file(cls, path: Path, file_type: FileType) -> DocumentResult:
        """
        子类需要实现的具体处理逻辑
        :param path: 文件路径
        :param file_type: 文件类型
        :return: DocumentResult 对象
        """
        raise NotImplementedError("Subclass must implement _process_file method")

    @classmethod
    def _get_file_size(cls, path: Path) -> int:
        """获取文件大小"""
        return path.stat().st_size

