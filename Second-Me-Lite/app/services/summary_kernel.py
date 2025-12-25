from app.services.L0.l0_generator import L0Generator
from app.core.schemas import FileInfo, SummarizerInput
from app.models.document import Document
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class SummaryKernel:
    """Summary 生成内核"""
    
    def __init__(self):
        self.generator = L0Generator()
        self.preferred_language = "zh_CN"
    
    def analyze(self, doc: Document, insight: str) -> Dict:
        """
        生成文档 summary
        
        Args:
            doc: Document 对象
            insight: 已生成的 insight（Overview + Breakdown 格式化后的文本）
            
        Returns:
            Dict: {"title": "...", "summary": "...", "keywords": [...]}
        """
        try:
            self.generator.preferred_language = self.preferred_language
            
            # 构建 FileInfo
            file_info = FileInfo(
                data_type=doc.mime_type,
                filename=doc.name,
                content="",
                file_content={"content": doc.raw_content} if doc.raw_content else None
            )
            
            # 构建 SummarizerInput
            summarizer_input = SummarizerInput(file_info=file_info,insight=insight)
            
            # 调用 LLM 生成 summary
            summary_result = self.generator.summarizer(summarizer_input)
            
            return summary_result
            
        except Exception as e:
            logger.error(f"生成 summary 失败: {str(e)}", exc_info=True)
            raise Exception(f"生成 summary 失败: {e}")

