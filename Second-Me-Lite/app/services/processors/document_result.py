from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class DocumentResult:
    """文档处理结果数据类"""
    raw_content: str  # 提取的原始内容
    mime_type: str  # MIME 类型
    file_type: str  # 文件类型（pdf, text, md）
    file_path: str  # 文件路径
    file_size: int  # 文件大小（字节）
    metadata: Optional[dict] = None  # 额外的元数据

