from copy import deepcopy
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
import logging
import os
from openai import OpenAI

from app.core.config import settings
from app.services.L1.bio import (
    Bio,
    Cluster,
    Note,
    ShadeInfo,
    ShadeMergeInfo,
    Memory,
    Todo,
    Chat,
)
from app.services.L1.topics_generator import TopicsGenerator
from app.services.L1.shade_generator import ShadeGenerator, ShadeMerger
from app.services.L1.status_bio_generator import StatusBioGenerator
from app.services.L1.prompt import (
    GLOBAL_BIO_SYSTEM_PROMPT,
    COMMON_PERSPECTIVE_SHIFT_SYSTEM_PROMPT,
    PREFER_LANGUAGE_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

DATE_TIME_FORMAT = "%Y-%m-%d"


class ConfidenceLevel(str, Enum):
    VERY_LOW = "VERY LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY HIGH"


IMPORTANCE_TO_CONFIDENCE = {
    1: ConfidenceLevel.VERY_LOW,
    2: ConfidenceLevel.LOW,
    3: ConfidenceLevel.MEDIUM,
    4: ConfidenceLevel.HIGH,
    5: ConfidenceLevel.VERY_HIGH,
}


class DailyTimeline:
    def __init__(self, id: int, dateTime: str, content: str, noteIds: List[int]):
        self.id = id
        self.date_time = dateTime
        self.content = content.strip()
        self.note_ids = noteIds


    def _desc_(self) -> str:
        """返回每日时间线的字符串表示
        
        Returns:
            str: 格式化的字符串表示
        """
        return f"- [{self.date_time}] {self.content}".strip()


    def to_dict(self) -> Dict[str, Any]:
        """将DailyTimeline对象转换为字典
        
        Returns:
            Dict[str, Any]: DailyTimeline的字典表示
        """
        return {
            "id": self.id,
            "dateTime": self.date_time,
            "content": self.content,
            "noteIds": self.note_ids,
        }


class MonthlyTimeline:
    def __init__(
        self, id: int, monthDate: str, title: str, dailyTimelines: List[Dict[str, Any]]
    ):
        self.id = id
        self.month_date = monthDate
        self.title = title
        daily_timelines = [
            DailyTimeline(**daily_timeline) for daily_timeline in dailyTimelines
        ]
        self.daily_timelines = sorted(
            daily_timelines,
            key=lambda x: datetime.strptime(x.date_time, DATE_TIME_FORMAT),
        )


    def _desc_(self) -> str:
        """返回每月时间线的字符串表示
        
        Returns:
            str: 格式化的字符串表示
        """
        return f"** {self.month_date} **\n" + "\n".join(
            [daily_timeline._desc_() for daily_timeline in self.daily_timelines]
        )


    def _preview_(self, preview_num: int = 0) -> str:
        """生成每月时间线的预览
        
        Args:
            preview_num: 预览中包含的每日时间线数量
            
        Returns:
            str: 每月时间线的预览字符串
        """
        preview_statement = f"[{self.month_date}] {self.title}\n"
        for daily_timeline in self.daily_timelines[:preview_num]:
            preview_statement += daily_timeline._desc_() + "\n"
        return preview_statement


    def to_dict(self) -> Dict[str, Any]:
        """将MonthlyTimeline对象转换为字典
        
        Returns:
            Dict[str, Any]: MonthlyTimeline的字典表示
        """
        return {
            "id": self.id,
            "monthDate": self.month_date,
            "title": self.title,
            "dailyTimelines": [
                daily_timeline.to_dict() for daily_timeline in self.daily_timelines
            ],
        }


class EntityWiki:
    def __init__(self, wikiText: str, monthlyTimelines: List[Dict[str, Any]]):
        self.wiki_text = wikiText
        self.monthly_timelines = [
            MonthlyTimeline(**monthly_timeline) for monthly_timeline in monthlyTimelines
        ]
        self.max_month_idx = (
            max([monthly_timeline.id for monthly_timeline in self.monthly_timelines])
            if self.monthly_timelines
            else 0
        )


    def to_dict(self) -> Dict[str, Any]:
        """将EntityWiki对象转换为字典
        
        Returns:
            Dict[str, Any]: EntityWiki的字典表示
        """
        return {
            "wikiText": self.wiki_text,
            "monthlyTimelines": [
                monthly_timeline.to_dict()
                for monthly_timeline in self.monthly_timelines
            ],
        }


class L1Generator:
    def __init__(self):
        self.preferred_language = "zh_CN"
        self.bio_model_params = {
            "temperature": 0,
            "max_tokens": 2000,
            "top_p": 0.001,  # 设置为0.001而不是0，因为某些API不接受top_p=0
            "frequency_penalty": 0,
            "seed": 42,
            "presence_penalty": 0,
            "timeout": 45,
        }
        # 直接使用 config.py 中的配置
        self.client = OpenAI(
            api_key=settings.CHAT_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self.model_name = settings.CHAT_MODEL
        self._top_p_adjusted = False  # 标记是否已调整top_p参数

    def _fix_top_p_param(self, error_message: str) -> bool:
        """如果API错误表明top_p参数无效，则修复它
        
        某些LLM提供商不接受top_p=0，需要在特定范围内取值。
        此函数检查错误是否与top_p相关，并将其调整为0.001，
        这足够接近0以保持确定性行为，同时满足API要求。
        
        Args:
            error_message: API响应的错误消息
            
        Returns:
            bool: 如果top_p已调整则返回True，否则返回False
        """
        if not self._top_p_adjusted and "top_p" in error_message.lower():
            logger.warning("Fixing top_p parameter from 0 to 0.001 to comply with model API requirements")
            self.bio_model_params["top_p"] = 0.001
            self._top_p_adjusted = True
            return True
        return False

    def _call_llm_with_retry(self, messages: List[Dict[str, str]], **kwargs) -> Any:
        """调用LLM API，支持参数调整的自动重试
        
        此函数处理对语言模型的API调用，同时在发生错误时实现自动参数修复。
        如果API由于无效的top_p参数而拒绝调用，它将调整参数值并重试一次。
        
        Args:
            messages: API调用的消息列表
            **kwargs: 传递给API调用的其他参数
            
        Returns:
            语言模型的API响应对象
            
        Raises:
            Exception: 如果API调用在所有重试后失败或出现无关错误
        """
        try:
            return self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                **self.bio_model_params,
                **kwargs
            )
        except Exception as e:
            error_msg = str(e)
            logger.error(f"API Error: {error_msg}")
            
            # 如果需要，尝试修复top_p参数
            if hasattr(e, 'response') and hasattr(e.response, 'status_code') and e.response.status_code == 400:
                if self._fix_top_p_param(error_msg):
                    logger.info("使用调整后的top_p参数重试LLM API调用")
                    return self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        **self.bio_model_params,
                        **kwargs
                    )
            
            # 重新抛出异常
            raise

    def __build_message(
        self, system_prompt: str, user_prompt: str, language: str
    ) -> List[Dict[str, str]]:
        """构建LLM API调用的消息
        
        Args:
            system_prompt: 系统提示内容
            user_prompt: 用户提示内容
            language: 响应的首选语言
            
        Returns:
            List[Dict[str, str]]: 格式化的LLM消息
        """
        raw_message = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        if language:
            raw_message.append(
                {
                    "role": "system",
                    "content": PREFER_LANGUAGE_SYSTEM_PROMPT.format(language=language),
                }
            )
        return raw_message


    def _global_bio_generate(self, global_bio: Bio) -> Bio:
        """生成全局传记
        
        Args:
            global_bio: 要生成内容的Bio对象
            
        Returns:
            Bio: 包含生成内容的更新后的Bio对象
        """
        user_prompt = global_bio.to_str()

        system_prompt = GLOBAL_BIO_SYSTEM_PROMPT

        global_bio_message = self.__build_message(system_prompt, user_prompt, language=self.preferred_language)

        response = self._call_llm_with_retry(global_bio_message)
        third_perspective_result = response.choices[0].message.content
        global_bio.summary_third_view = third_perspective_result
        global_bio.content_third_view = global_bio.complete_content()
        global_bio = self._shift_perspective(global_bio)
        global_bio = self._assign_confidence_level(global_bio)

        return global_bio


    def _shift_perspective(self, global_bio: Bio) -> Bio:
        """将传记的视角转换为第二人称
        
        Args:
            global_bio: 要转换视角的Bio对象
            
        Returns:
            Bio: 视角转换后的更新后的Bio对象
        """
        system_prompt = COMMON_PERSPECTIVE_SHIFT_SYSTEM_PROMPT
        user_prompt = global_bio.summary_third_view

        shift_perspective_message = self.__build_message(
            system_prompt, user_prompt, language=self.preferred_language
        )

        response = self._call_llm_with_retry(shift_perspective_message)
        second_perspective_result = response.choices[0].message.content

        global_bio.summary_second_view = second_perspective_result
        global_bio.content_second_view = global_bio.complete_content(second_view=True)
        return global_bio


    def _assign_confidence_level(self, global_bio: Bio) -> Bio:
        """为传记中的shades分配置信度级别
        
        Args:
            global_bio: 要分配置信度级别的Bio对象
            
        Returns:
            Bio: 已分配置信度级别的更新后的Bio对象
        """
        level_n, interest_n = len(IMPORTANCE_TO_CONFIDENCE), len(global_bio.shades_list)
        level_list = [
            IMPORTANCE_TO_CONFIDENCE[level_n - int(i / interest_n * level_n)]
            for i in range(interest_n)
        ]
        for shade, level in zip(global_bio.shades_list, level_list):
            shade.confidence_level = level
        return global_bio


    def gen_global_biography(
        self, old_profile: Bio, cluster_list: List[Cluster]
    ) -> Bio:
        """生成用户的全局传记
        
        Args:
            old_profile: 之前的Bio对象
            cluster_list: 用于参考的聚类列表
            
        Returns:
            Bio: 更新后的全局传记
        """
        global_bio = deepcopy(old_profile)
        global_bio = self._global_bio_generate(global_bio)
        return global_bio


    def gen_shade_for_cluster(
        self,
        old_memory_list: List[Note],
        new_memory_list: List[Note],
        shade_info_list: List[ShadeInfo],
    )-> Optional[ShadeInfo]:
        """为聚类生成shade
        
        Args:
            old_memory_list: 之前的笔记列表
            new_memory_list: 新的笔记列表
            shade_info_list: shade信息列表
            
        Returns:
            生成的shade
        """
        shade_generator = ShadeGenerator()

        shade = shade_generator.generate_shade(
            old_memory_list=old_memory_list,
            new_memory_list=new_memory_list,
            shade_info_list=shade_info_list,
        )
        return shade


    def merge_shades(self, shade_info_list: List[ShadeMergeInfo]):
        """合并多个shades
        
        Args:
            shade_info_list: shade合并信息列表
            
        Returns:
            合并后的shade结果
        """
        shade_merger = ShadeMerger()
        return shade_merger.merge_shades(shade_info_list)


    def gen_status_biography(
        self, cur_time: str, notes: List[Note], todos: List[Todo], chats: List[Chat]
    ):
        """生成用户的状态传记
        
        Args:
            cur_time: 当前时间字符串
            notes: 笔记列表
            todos: 待办事项列表
            chats: 聊天记录列表
            
        Returns:
            生成的状态传记
        """
        status_bio_generator = StatusBioGenerator()
        return status_bio_generator.generate_status_bio(notes, todos, chats)


    def gen_topics_for_shades(
        self,
        old_cluster_list: List[Cluster],
        old_outlier_memory_list: List[Memory],
        new_memory_list: List[Memory],
        cophenetic_distance: float = 1.0,
        outlier_cutoff_distance: float = 0.5,
        cluster_merge_distance: float = 0.5,
    ):
        """为shades生成主题
        
        Args:
            old_cluster_list: 之前的聚类列表
            old_outlier_memory_list: 之前的异常值记忆列表
            new_memory_list: 新的记忆列表
            cophenetic_distance: 共表型聚类的距离阈值
            outlier_cutoff_distance: 异常值检测的距离阈值
            cluster_merge_distance: 聚类合并的距离阈值
            
        Returns:
            为shades生成的主题
        """
        topics_generator = TopicsGenerator()
        return topics_generator.generate_topics_for_shades(
            old_cluster_list,
            old_outlier_memory_list,
            new_memory_list,
            cophenetic_distance,
            outlier_cutoff_distance,
            cluster_merge_distance,
        )


    def generate_topics(self, notes_list: List[Note]):
        """从笔记列表生成主题
        
        Args:
            notes_list: 用于生成主题的笔记列表
            
        Returns:
            生成的主题
        """
        topics_generator = TopicsGenerator()
        return topics_generator.generate_topics(notes_list)
