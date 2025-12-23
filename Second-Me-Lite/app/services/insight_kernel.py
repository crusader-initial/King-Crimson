from app.services.L0.l0_generator import L0Generator
from app.core.schemas import FileInfo, BioInfo, InsighterInput
from app.models.document import Document
from typing import Tuple, Dict
import logging

logger = logging.getLogger(__name__)

class InsightKernel:
    """Insight 生成内核"""
    
    def __init__(self):
        self.generator = L0Generator()
        self.preferred_language = "zh_CN"  # 默认使用中文语言
    
    def analyze(self, doc: Document, bio_info: BioInfo) -> Tuple[str, str, Dict]:
        """
        生成文档 insight
        
        Args:
            doc: Document 对象
            bio_info: BioInfo 对象
            
        Returns:
            tuple: (insight_text, title, insight_json)
            - insight_text: Overview + Breakdown（格式化后的文本）
            - title: 标题
            - insight_json: 完整的 JSON 结构（用于存储）
        """
        try:
            self.generator.preferred_language = self.preferred_language
            
            # 构建 FileInfo
            file_info = FileInfo(
                data_type=doc.mime_type,
                filename=doc.name,
                content=doc.raw_content or "",
                file_content={"content": doc.raw_content} if doc.raw_content else None
            )
            
            # 构建 InsighterInput
            insighter_input = InsighterInput(
                file_info=file_info,
                bio_info=bio_info
            )
            
            # 调用 LLM 生成 insight（两阶段）
            insight_result = self.generator.insighter(insighter_input)
            
            # 处理返回值：insighter() 返回 {"title": title, "insight": insight}
            title = insight_result.get("title", "")
            insight_text = insight_result.get("insight", "")
            insight_json = {"title": title, "insight": insight_text}
            
            return insight_text, title, insight_json
            
        except Exception as e:
            logger.error(f"生成 insight 失败: {str(e)}", exc_info=True)
            raise Exception(f"生成 insight 失败: {e}")

