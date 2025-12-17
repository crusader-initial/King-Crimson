from enum import Enum
from typing import Dict


class FileType(Enum):
    """支持的文件类型"""
    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "md"

    @classmethod
    def get_mime_mapping(cls) -> Dict[str, "FileType"]:
        """获取文件扩展名到文件类型的映射"""
        return {
            ".pdf": cls.PDF,
            ".txt": cls.TEXT,
            ".md": cls.MARKDOWN,
        }

    @classmethod
    def get_mime_type(cls, file_type: "FileType") -> str:
        """获取文件类型的 MIME 类型"""
        mime_map = {
            cls.PDF: "application/pdf",
            cls.TEXT: "text/plain",
            cls.MARKDOWN: "text/markdown",
        }
        return mime_map.get(file_type, "application/octet-stream")


class UnsupportedFileType(Exception):
    """不支持的文件类型异常"""
    pass

