from typing import Dict, List, Any, Optional
import json
import re
import traceback
import logging

from openai import OpenAI
import numpy as np

from app.core.config import settings
from app.services.L1.bio import ShadeInfo, ShadeMergeInfo, ShadeMergeResponse, ShadeTimeline, Note
from app.services.L1.prompt import (
    SHADE_INITIAL_PROMPT,
    PERSON_PERSPECTIVE_SHIFT_V2_PROMPT,
    SHADE_MERGE_PROMPT,
    SHADE_IMPROVE_PROMPT,
    SHADE_MERGE_DEFAULT_SYSTEM_PROMPT,
    PREFER_LANGUAGE_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

class ShadeGenerator:
    def __init__(self):
        self.preferred_language = "zh_CN"
        self.model_params = {
            "temperature": 0,
            "max_tokens": 3000,
            "top_p": 0.001,  # 设置为0.001而不是0，因为某些API不接受top_p=0
            "frequency_penalty": 0,
            "seed": 42,
            "presence_penalty": 0,
            "timeout": 45,
        }
        # 直接使用 config.py 中的配置，参考 L1Generator
        # 仅在此处补充 /v1，不影响其他服务
        base_url = settings.OPENAI_BASE_URL.rstrip('/')
        if not base_url.endswith('/v1'):
            base_url = base_url + '/v1'
        
        self.client = OpenAI(
            api_key=settings.CHAT_API_KEY,
            base_url=base_url,
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
            self.model_params["top_p"] = 0.001
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
                **self.model_params,
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
                        **self.model_params,
                        **kwargs
                    )
            
            # 重新抛出异常
            raise

    def _build_message(self, system_prompt: str, user_prompt: str) -> List[Dict[str, str]]:
        """构建LLM API调用的消息结构
        
        Args:
            system_prompt: 用于指导LLM行为的系统提示
            user_prompt: 包含实际查询的用户提示
            
        Returns:
            格式化的LLM API消息字典列表
        """
        raw_message = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        if self.preferred_language:
            raw_message.append(
                {
                    "role": "system",
                    "content": PREFER_LANGUAGE_SYSTEM_PROMPT.format(
                        language=self.preferred_language
                    ),
                }
            )
        return raw_message


    def __add_second_view_info(self, shade_info: ShadeInfo) -> ShadeInfo:
        """向shade信息添加第二人称视角信息
        
        Args:
            shade_info: 具有第三人称视角的ShadeInfo对象
            
        Returns:
            更新后的具有第二人称视角的ShadeInfo对象
        """
        user_prompt = f"""Domain Name: {shade_info.name}
Domain Description: {shade_info.desc_third_view}
Domain Content: {shade_info.content_third_view}
Domain Timelines: 
{
    "-".join([f"{timeline.create_time}, {timeline.desc_third_view}, {timeline.ref_memory_id}" for timeline in shade_info.timelines if timeline.is_new])
}
"""
        shift_perspective_message = self._build_message(PERSON_PERSPECTIVE_SHIFT_V2_PROMPT, user_prompt)
        response = self._call_llm_with_retry(shift_perspective_message)
        content = response.choices[0].message.content
        shift_pattern = r"\{.*\}"
        shift_perspective_result = self.__parse_json_response(content, shift_pattern)
        
        # 检查结果是否为None并提供默认值以避免TypeError
        if shift_perspective_result is None:
            logger.warning(f"解析视角转换结果失败，使用默认值: {content}")
            # 创建具有预期参数的默认映射
            shift_perspective_result = {
                "domainDesc": f"你有和{shade_info.name}相关的知识和经验 .",
                "domainContent": shade_info.content_third_view,
                "domainTimeline": []
            }
            
        # 现在可以安全地将shift_perspective_result作为kwargs传递
        shade_info.add_second_view(**shift_perspective_result)
        return shade_info


    def __parse_json_response(
        self, content: str, pattern: str, default_res: dict = None
    ) -> Dict[str, Any]:
        """解析LLM输出中的JSON响应
        
        Args:
            content: LLM的原始文本响应
            pattern: 用于提取JSON字符串的正则表达式模式
            default_res: 解析失败时返回的默认结果
            
        Returns:
            解析后的JSON字典，如果解析失败则返回default_res
        """
        matches = re.findall(pattern, content, re.DOTALL)
        if not matches:
            logger.error(f"No Json Found: {content}")
            return default_res
        try:
            json_res = json.loads(matches[0])
        except Exception as e:
            logger.error(f"Json Parse Error: {traceback.format_exc()}-{content}")
            return default_res
        return json_res


    def __shade_initial_postprocess(self, content: str) -> Optional[ShadeInfo]:
        """处理初始shade生成响应
        
        Args:
            content: LLM的原始响应文本
            
        Returns:
            ShadeInfo对象，如果处理失败则返回空字典
        """
        shade_generate_pattern = r"\{.*\}"
        shade_raw_info = self.__parse_json_response(content, shade_generate_pattern)

        if not shade_raw_info:
            logger.error(f"解析shade生成结果失败: {content}")
            return {}  # 返回空字典

        logger.info(f"Shade Generate Result: {shade_raw_info}")

        raw_shade_info = ShadeInfo(
            name=shade_raw_info.get("domainName", ""),
            aspect=shade_raw_info.get("aspect", ""),
            icon=shade_raw_info.get("icon", ""),
            descThirdView=shade_raw_info.get("domainDesc", ""),
            contentThirdView=shade_raw_info.get("domainContent", ""),
        )
        raw_shade_info.timelines = [
            ShadeTimeline.from_raw_format(timeline)
            for timeline in shade_raw_info.get("domainTimelines", [])
        ]
        raw_shade_info = self.__add_second_view_info(raw_shade_info)
        return raw_shade_info


    def _initial_shade_process(self, new_memory_list: List[Note]) -> Optional[ShadeInfo]:
        """处理从新记忆生成初始shade
        
        Args:
            new_memory_list: 用于生成shade的新记忆列表
            
        Returns:
            从记忆生成的新ShadeInfo对象
        """
        user_prompt = "\n\n".join([memory.to_str() for memory in new_memory_list])

        shade_generate_message = self._build_message(SHADE_INITIAL_PROMPT, user_prompt)

        response = self._call_llm_with_retry(shade_generate_message)
        content = response.choices[0].message.content

        logger.info(f"Shade Generate Result: {content}")
        return self.__shade_initial_postprocess(content)


    def _merge_shades_info(
        self, old_memory_list: List[Note], shade_info_list: List[ShadeInfo]
    ) -> ShadeInfo:
        """将多个shade合并为单个shade
        
        Args:
            old_memory_list: 现有记忆列表
            shade_info_list: 要合并的shade信息列表
            
        Returns:
            表示合并后shade的新ShadeInfo对象
        """
        user_prompt = "\n\n".join(
            [
                f"User Interest Domain {i} Analysis:\n{old_shade_info.to_str()}"
                for i, old_shade_info in enumerate(shade_info_list)
            ]
        )

        merge_shades_message = self._build_message(SHADE_MERGE_PROMPT, user_prompt)
        response = self._call_llm_with_retry(merge_shades_message)
        content = response.choices[0].message.content
        logger.info(f"Shade Generate Result: {content}")
        return self.__shade_merge_postprocess(content)


    def __shade_merge_postprocess(self, content: str) -> ShadeInfo:
        """处理shade合并响应
        
        Args:
            content: LLM的原始响应文本
            
        Returns:
            表示合并后shade的新ShadeInfo对象
            
        Raises:
            Exception: 如果解析shade生成结果失败
        """
        shade_merge_pattern = r"\{.*\}"
        shade_merge_info = self.__parse_json_response(content, shade_merge_pattern)
        if not shade_merge_info:
            raise Exception(f"Failed to parse the shade generate result: {content}")

        logger.info(f"Shade Merge Result: {shade_merge_info}")
        merged_shade_info = ShadeInfo(
            name=shade_merge_info.get("newInterestName", ""),
            aspect=shade_merge_info.get("newInterestAspect", ""),
            icon=shade_merge_info.get("newInterestIcon", ""),
            descThirdView=shade_merge_info.get("newInterestDesc", ""),
            contentThirdView=shade_merge_info.get("newInterestContent", ""),
        )

        merged_shade_info.timelines = [
            ShadeTimeline.from_raw_format(timeline)
            for timeline in shade_merge_info.get("newInterestTimelines", [])
        ]
        merged_shade_info = self.__add_second_view_info(merged_shade_info)
        return merged_shade_info


    def __shade_improve_postprocess(self, old_shade: ShadeInfo, content: str) -> ShadeInfo:
        """处理shade改进响应
        
        Args:
            old_shade: 要改进的原始ShadeInfo对象
            content: LLM的原始响应文本
            
        Returns:
            更新后的ShadeInfo对象
            
        Raises:
            Exception: 如果解析shade生成结果失败
        """
        shade_improve_pattern = r"\{.*\}"
        shade_improve_info = self.__parse_json_response(content, shade_improve_pattern)
        if not shade_improve_info:
            raise Exception(f"Failed to parse the shade generate result: {content}")

        logger.info(f"Shade Improve Result: {shade_improve_info}")
        old_shade.imporve_shade_info(**shade_improve_info)
        shade_info = self.__add_second_view_info(old_shade)
        return shade_info


    def _improve_shade_info(
        self, new_memory_list: List[Note], old_shade_info: ShadeInfo
    ) -> ShadeInfo:
        """使用新记忆改进现有shade信息
        
        Args:
            new_memory_list: 要合并的新记忆列表
            old_shade_info: 要改进的现有ShadeInfo对象
            
        Returns:
            更新后的ShadeInfo对象
        """
        recent_memories_str = "\n\n".join(
            [memory.to_str() for memory in new_memory_list]
        )

        user_prompt = f""" Original Shade Info:
{old_shade_info.to_str()}

Recent Memories:
{recent_memories_str}
"""
        shade_improve_message = self._build_message(SHADE_IMPROVE_PROMPT, user_prompt)
        response = self._call_llm_with_retry(shade_improve_message)
        content = response.choices[0].message.content
        logger.info(f"Shade Generate Result: {content}")
        return self.__shade_improve_postprocess(old_shade_info, content)


    def generate_shade(
        self,
        old_memory_list: List[Note],
        new_memory_list: List[Note],
        shade_info_list: List[ShadeInfo],
    ) -> Optional[ShadeInfo]:
        """基于记忆生成或更新shade
        
        每次传入的是聚类内的一批记忆，
        所以这里看起来只生成一个shade。
        
        Args:
            old_memory_list: 现有记忆列表
            new_memory_list: 要合并的新记忆列表
            shade_info_list: 现有ShadeInfo对象列表
            
        Returns:
            新的或更新后的ShadeInfo对象，如果生成失败则返回None
            
        Raises:
            Exception: 如果输入参数异常
        """
        logger.warning(f"shade_info_list: {shade_info_list}")
        logger.warning(f"old_memory_list: {old_memory_list}")
        logger.warning(f"new_memory_list: {new_memory_list}")
        
        if not (shade_info_list or old_memory_list):
            logger.info(f"Shades initial Process! Current shade have {len(new_memory_list)} memories!")
            new_shade = self._initial_shade_process(new_memory_list)
        elif shade_info_list and old_memory_list:
            if len(shade_info_list) > 1:
                logger.info(f"Merge shades Process! {len(shade_info_list)} shades need to be merged!")
                raw_shade = self._merge_shades_info(old_memory_list, shade_info_list)
            else:
                raw_shade = shade_info_list[0]
            logger.info(f"Update shade Process! Current shade should improve {len(new_memory_list)} memories!")
            new_shade = self._improve_shade_info(new_memory_list, raw_shade)
        else:
            # 意味着shade_info_list或old_memory_list为空，表明后端输入参数异常
            logger.error(traceback.format_exc())
            raise Exception("shade_info_list或old_memory_list为空！请检查输入！")

        # 检查new_shade是否为空字典（重点关注初始阶段）
        if not new_shade:
            return None

        return new_shade


class ShadeMerger:
    def __init__(self):
        # 直接使用 config.py 中的配置，参考 L1Generator
        # 仅在此处补充 /v1，不影响其他服务
        base_url = settings.OPENAI_BASE_URL.rstrip('/')
        if not base_url.endswith('/v1'):
            base_url = base_url + '/v1'
        
        self.client = OpenAI(
            api_key=settings.CHAT_API_KEY,
            base_url=base_url,
        )
        self.model_name = settings.CHAT_MODEL
        
        self.model_params = {
            "temperature": 0,
            "max_tokens": 3000,
            "top_p": 0.001,  # 设置为0.001而不是0，因为某些API不接受top_p=0
            "frequency_penalty": 0,
            "seed": 42,
            "presence_penalty": 0,
            "timeout": 45,
        }
        self.preferred_language = "zh_CN"
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
            self.model_params["top_p"] = 0.001
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
                **self.model_params,
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
                        **self.model_params,
                        **kwargs
                    )
            
            # 重新抛出异常
            raise

    def _build_user_prompt(self, shade_info_list: List[ShadeMergeInfo]) -> str:
        """从shade信息列表构建用户提示
        
        Args:
            shade_info_list: shade合并信息列表
            
        Returns:
            包含shade信息的格式化字符串
        """
        shades_str = "\n\n".join(
            [
                f"Shade ID: {shade.id}\n"
                f"Name: {shade.name}\n"
                f"Aspect: {shade.aspect}\n"
                f"Description Third View: {shade.desc_third_view}\n"
                f"Content Third View: {shade.content_third_view}\n"
                for shade in shade_info_list
            ]
        )

        return f"""Shades List:
{shades_str}
"""


    def _calculate_merged_shades_center_embed(
        self, shades: List[ShadeMergeInfo]
    ) -> List[float]:
        """计算合并后shades的中心嵌入向量
        
        Args:
            shades: 要合并的shades列表
            
        Returns:
            表示新中心嵌入向量的浮点数列表
            
        Raises:
            ValueError: 如果未找到有效shades或总聚类大小为0
        """
        if not shades:
            raise ValueError("No valid shades found for the given merge list.")

        total_embedding = np.zeros(len(shades[0].cluster_info["centerEmbedding"]))  # 假设center_embedding是固定长度的向量
        total_cluster_size = 0

        for shade in shades:
            cluster_size = shade.cluster_info["clusterSize"]
            center_embedding = np.array(shade.cluster_info["centerEmbedding"])
            total_embedding += cluster_size * center_embedding
            total_cluster_size += cluster_size

        if total_cluster_size == 0:
            raise ValueError("Total cluster size is zero, cannot compute the new center embedding.")

        new_center_embedding = total_embedding / total_cluster_size
        return new_center_embedding.tolist()


    def _build_message(self, system_prompt: str, user_prompt: str) -> List[Dict[str, str]]:
        """构建LLM API调用的消息结构
        
        Args:
            system_prompt: 用于指导LLM行为的系统提示
            user_prompt: 包含实际查询的用户提示
            
        Returns:
            格式化的LLM API消息字典列表
        """
        raw_message = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        if self.preferred_language:
            raw_message.append(
                {
                    "role": "system",
                    "content": PREFER_LANGUAGE_SYSTEM_PROMPT.format(
                        language=self.preferred_language
                    ),
                }
            )
        return raw_message


    def __parse_json_response(
        self, content: str, pattern: str, default_res: dict = None
    ) -> Any:
        """解析LLM输出中的JSON响应
        
        Args:
            content: LLM的原始文本响应
            pattern: 用于提取JSON字符串的正则表达式模式
            default_res: 解析失败时返回的默认结果
            
        Returns:
            解析后的JSON对象，如果解析失败则返回default_res
        """
        matches = re.findall(pattern, content, re.DOTALL)
        if not matches:
            logger.error(f"No Json Found: {content}")
            return default_res
        try:
            json_res = json.loads(matches[0])
        except Exception as e:
            logger.error(f"Json Parse Error: {traceback.format_exc()}-{content}")
            return default_res
        return json_res


    def merge_shades(self, shade_info_list: List[ShadeMergeInfo]) -> ShadeMergeResponse:
        """基于相似性合并多个shades
        
        Args:
            shade_info_list: 要评估合并的shade信息列表
            
        Returns:
            包含合并结果或错误信息的ShadeMergeResponse对象
        """
        try:
            for shade in shade_info_list:
                logger.info(f"shade: {shade}")

            # 如果只有一个或零个shade，无需合并，直接返回
            if len(shade_info_list) <= 1:
                logger.info(f"只有 {len(shade_info_list)} 个shade，无需合并决策")
                final_merge_shade_list = []
                if len(shade_info_list) == 1:
                    shade = shade_info_list[0]
                    if shade.cluster_info and "centerEmbedding" in shade.cluster_info:
                        final_merge_shade_list.append({
                            "shadeIds": [str(shade.id)],
                            "centerEmbedding": shade.cluster_info["centerEmbedding"]
                        })
                result = {"mergeShadeList": final_merge_shade_list}
                response = ShadeMergeResponse(result=result, success=True)
                return response

            user_prompt = self._build_user_prompt(shade_info_list)
            merge_decision_message = self._build_message(SHADE_MERGE_DEFAULT_SYSTEM_PROMPT, user_prompt)
            logger.info(f"Built merge_decision_message: {merge_decision_message}")

            response = self._call_llm_with_retry(merge_decision_message)
            content = response.choices[0].message.content
            logger.info(f"Shade Merge Decision Result: {content}")

            try:
                merge_shade_list = self.__parse_json_response(content, r"\[.*\]")
                logger.info(f"Parsed merge_shade_list: {merge_shade_list}")
            except Exception as e:
                raise Exception(f"Failed to parse the shade merge list: {content}") from e

            # 收集所有在合并组中的shade IDs
            merged_shade_ids = set()
            if merge_shade_list:
                for group in merge_shade_list:
                    if group:  # 确保group不为空
                        merged_shade_ids.update([str(shade_id) for shade_id in group])

            # 处理合并的组
            final_merge_shade_list = []
            if merge_shade_list:
                for group in merge_shade_list:
                    shade_ids = group
                    logger.info(f"处理shadeIds组: {shade_ids}")
                    if not shade_ids:
                        continue

                    # 根据shadeIds获取shades
                    shades = [shade for shade in shade_info_list if str(shade.id) in shade_ids]

                    if not shades:
                        logger.info(f"未找到shadeIds的有效shades: {shade_ids}。跳过此组。")
                        continue

                    # 计算新的聚类嵌入向量（中心向量）
                    new_cluster_embedd = self._calculate_merged_shades_center_embed(shades)
                    logger.info(f"Calculated new cluster embedding: {new_cluster_embedd}")

                    final_merge_shade_list.append({"shadeIds": shade_ids, "centerEmbedding": new_cluster_embedd})

            # 处理未合并的shade，每个单独成组
            for shade in shade_info_list:
                if str(shade.id) not in merged_shade_ids:
                    if shade.cluster_info and "centerEmbedding" in shade.cluster_info:
                        final_merge_shade_list.append({
                            "shadeIds": [str(shade.id)],
                            "centerEmbedding": shade.cluster_info["centerEmbedding"]
                        })
                    else:
                        logger.warning(f"Shade {shade.id} 没有cluster_info或centerEmbedding，跳过")

            result = {"mergeShadeList": final_merge_shade_list}
            response = ShadeMergeResponse(result=result, success=True)

        except Exception as e:
            logger.error(traceback.format_exc())
            response = ShadeMergeResponse(result=str(e), success=False)

        return response
