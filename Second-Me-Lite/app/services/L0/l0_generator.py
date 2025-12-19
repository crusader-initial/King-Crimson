
from typing import Any, Dict, List
import json
import time
import traceback
import logging

from openai import OpenAI
import tiktoken

# 导入存在的工具函数和类
from app.core.utils import (
    equidistant_filter,
    DataType,
    select_language_desc,
    cal_upperbound,
    TokenTextSplitter,
    TokenParagraphSplitter,
    chunk_filter,
    get_safe_content_turncate,
    get_summarize_title_keywords,
)
from app.core.schemas import FileInfo, SummarizerInput, InsighterInput
from app.core.config import settings
from app.services.L0.prompts import (
    INSIGHT_DOC_OVERVIEW as insight_doc_overview,
    INSIGHT_DOC_BREAKDOWN as insight_doc_breakdown,
    NOTE_SUMMARY_PROMPT,
)

# 使用标准 logging
logger = logging.getLogger(__name__)

class L0Generator:
    def __init__(self, preferred_language="ch_zh"):
        """初始化 L0Generator，设置语言偏好
        
        参数:
            preferred_language: 用于生成的语言，默认为 English
        """
        self.preferred_language = preferred_language

        # 初始化 tokenizer
        self._tokenizer = tiktoken.get_encoding("cl100k_base")  # OpenAI 默认 tokenizer

        self.lf_prompt_doc_overview = insight_doc_overview
        self.lf_prompt_doc_breakdown = insight_doc_breakdown

        self.max_retries_summarize = 2
        self.timeout_summarize = 30

        # 直接使用 config.py 中的配置
        self.client = OpenAI(
            api_key=settings.CHAT_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self.model_name = settings.CHAT_MODEL

    def _insighter_doc(
        self,
        bio: Dict[str, str],
        content: str,
        max_retries: int,
        request_timeout: int,
        file_content: Dict[str, Any],
        max_tokens: int = 3000,
        filter=None,
    ) -> tuple[str, str]:
        """处理文档内容以生成洞察
        
        参数:
            bio: 包含用户传记信息的字典
            content: 文档的文本内容或提示信息
            max_retries: API 调用的最大重试次数
            request_timeout: API 调用的超时时间（秒）
            file_content: 包含文档内容的字典
            max_tokens: 生成的最大 token 数
            filter: 用于过滤文档块的函数
            
        返回:
            包含 (insight, title) 的元组
        """
        user_info = """# Hint # 
                    "{hint}"

                    # Content #
                    "{content}"

                    # User Instruction #
                    "{user_input}"
                    """
        user_input = "Here are some content and their hint. Please follow the WorkFlow and do your best. Ensure that your response is in a parseable JSON format.  "
        language_desc = select_language_desc(self.preferred_language)
        
        # 如果未提供 filter，使用默认的 equidistant_filter
        if filter is None:
            filter = equidistant_filter

        segment_list = [self.lf_prompt_doc_overview, self.lf_prompt_doc_breakdown]
        messages_list = []
        max_retry_list = []
        alarm_mesg_list = []
        
        # 提取模型名称（去除openai/前缀），避免重复处理
        model_name_clean = self.model_name.replace("openai/", "")
        
        # 预处理文档内容：正确处理字符串或列表类型
        raw_content = file_content.get("content", "") if file_content else ""
        if isinstance(raw_content, list):
            doc_content_raw = "\n".join(raw_content)
        elif isinstance(raw_content, str):
            doc_content_raw = raw_content
        else:
            doc_content_raw = str(raw_content) if raw_content else ""
        
        # 如果内容为空，记录警告
        if not doc_content_raw.strip():
            logger.warning("文档内容为空，可能导致生成结果不准确")
        
        for i in range(len(segment_list)):
            doc_parser_prompt = segment_list[i]
            raw_text = doc_parser_prompt + user_input + user_info + language_desc
            upper_bound = cal_upperbound(
                model_limit=7000 + max_tokens,
                generage_limit=max_tokens,
                tolerance=500,
                raw=raw_text,
            )
            
            # 分块和截断配置
            chunk_size = 512
            chunk_num = upper_bound // chunk_size + 1

            # 创建文本分割器
            text_splitter = TokenTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=0,
                model_name=model_name_clean,
            )

            # 将文档内容分割成多个块
            content_chunks = text_splitter.split_text(doc_content_raw)
            
            # 从多个块中筛选出最相关的块
            filtered_content = chunk_filter(
                content_chunks, 
                filter, 
                filtered_chunks_n=chunk_num, 
                separator="\n", 
                spacer="\n"
            )
            
            # 截断内容以确保不超过token限制
            doc_content_final = get_safe_content_turncate(
                filtered_content, 
                model_name=model_name_clean, 
                max_tokens=upper_bound
            )

            # 格式化用户输入内容
            user_content = user_info.format(
                hint=content, 
                content=doc_content_final, 
                user_input=user_input
            )
            
            # 替换prompt中的占位符（如果存在）
            if "__global_bio__" in doc_parser_prompt:
                doc_parser_prompt = doc_parser_prompt.replace(
                    "__about_me__", bio.get("about_me", "")
                ).replace(
                    "__global_bio__", bio.get("global_bio", "")
                ).replace(
                    "__status_bio__", bio.get("status_bio", "")
                )

            # 构建消息列表
            messages = [
                {"role": "system", "content": doc_parser_prompt},
                {"role": "user", "content": user_content + language_desc},
            ]
            messages_list.append(messages)

        results = []
        for messages in messages_list:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.0,
                timeout=request_timeout,
                response_format={"type": "json_object"},
            )
            results.append(json.loads(response.choices[0].message.content))
        try:
            title = results[0].get("Title")
            overview = results[0].get("Overview")
            breakdown = results[1].get("Breakdown", {})

            tmpl = "{}\n{}"

            formated_breakdown = ""
            for subtitle, key_points in breakdown.items():
                formated_breakdown += f"\n**{subtitle}**\n"

                if not isinstance(key_points, list):
                    raise RuntimeError(
                        f"Unexpected generated result: {json.dumps(breakdown)}"
                    )

                for key_point in key_points:
                    if isinstance(key_point, list) and len(key_point) == 2:
                        formated_breakdown += f"- **{key_point[0]}**: {key_point[1]}\n"
                    else:
                        raise RuntimeError(
                            f"Unexpected generated result in key_points: {json.dumps(breakdown)} expected a list of length 2."
                        )

            insight = tmpl.format(overview, formated_breakdown)

            return insight, title

        except Exception as e:
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Unexpected error: {e}")

    def insighter(self, inputs: InsighterInput) -> Dict[str, str]:
        """从文档输入生成洞察
        
        参数:
            inputs: 包含文件和传记信息的结构化输入参数
            
        返回:
            包含 title 和 insight 的字典
        """
        try:
            datatype = DataType(inputs.file_info.data_type)
        except ValueError:
            logger.warning(
                "Unsupported dataType: %s. Processing as DOCUMENT by default",
                inputs.file_info.data_type,
            )
            datatype = DataType.DOCUMENT

        logger.info("input filename=%s", inputs.file_info.filename)
        logger.info(
            "input content=%s (first 100 characters)",
            inputs.file_info.content.strip()[:100],
        )

        bio = {
            "global_bio": inputs.bio_info.global_bio.split("### Conclusion ###")[
                -1
            ].strip("\n ")
            if inputs.bio_info.global_bio
            else "User has no biography right now",
            "status_bio": inputs.bio_info.status_bio.split(
                "** User Activities Overview **"
            )[-1]
            .strip("** Physical and mental health status **")[0]
            .strip("\n")
            if inputs.bio_info.status_bio
            else "",
            "about_me": inputs.bio_info.about_me.strip("\n")
            if inputs.bio_info.about_me
            else "",
        }

        text_len = len(self._tokenizer.encode(inputs.file_info.content))

        if text_len > 20 or inputs.file_info.file_content:
            if datatype == DataType.IMAGE:
                insight, title = self._insighter_image(
                    bio=bio,
                    content=inputs.file_info.content,
                    max_retries=self.max_retries_summarize,
                    request_timeout=30,
                    file_content=inputs.file_info.file_content,
                )
            elif datatype == DataType.AUDIO:
                insight, title = self._insighter_audio(
                    bio=bio,
                    content=inputs.file_info.content,
                    max_retries=self.max_retries_summarize,
                    request_timeout=45,
                    file_content=inputs.file_info.file_content,
                )
            else:
                insight, title = self._insighter_doc(
                    bio=bio,
                    content=inputs.file_info.content,
                    max_retries=self.max_retries_summarize,
                    request_timeout=45,
                    file_content=inputs.file_info.file_content,
                )
        else:
            logger.warning("less than 20 characters, use filename as title")
            title, insight = inputs.file_info.content, inputs.file_info.content
            if inputs.file_info.filename:
                logger.info("use filename as title")
                title = inputs.file_info.filename

        t1 = time.time()
        logger.warning(
            "Insighter: title=%s, summary=%s",
            title,
            insight,
        )

        return {
            "title": title,
            "insight": insight,
        }

    def __serial_summary_filter(
        self, summaries: List[str], chunks_list: List[List[str]], separator: str = "", filtered_chunks_n: int = 6
    ) -> List[str]:
        """过滤并组合摘要和相关块
        
        参数:
            summaries: 摘要字符串列表
            chunks_list: 包含文本块的列表的列表
            separator: 用于连接块和摘要的字符串
            filtered_chunks_n: 要过滤的最大块数
            
        返回:
            组合后的内容字符串列表
        """
        # 当块长度为 0 时跳过摘要，否则将摘要与一些相邻块组合
        use_contents = []
        for summary, chunks in zip(summaries, chunks_list):
            # 当块数超过 filtered_chunks_n-1 时，这不是最终摘要轮次
            if len(chunks) > filtered_chunks_n - 1:
                use_content = separator.join([summary, *chunks[:5]])
            # 当块数在 0 和 filtered_chunks_n-1 之间时，这是最终轮次
            elif len(chunks) > 0:
                use_content = separator.join([summary, *chunks])
            else:
                # 当块数为 0 时，摘要已完成，跳过此轮次以避免使用资源
                continue
            use_contents.append(use_content)
        return use_contents

    def _summarize_title_abstract_keywords(
        self,
        content: str or List[str],
        filename: str,
        file_type: str,
        request_timeout: int,
        max_retries: int,
        preferred_language: str,
        filter=None,
    ) -> tuple[str, str, List[str]] or List[tuple[str, str, List[str]]]:
        """从内容生成标题、摘要和关键词
        
        参数:
            content: 要摘要的字符串或字符串列表
            filename: 正在摘要的文件名
            file_type: 文件类型（文档、图像、音频等）
            request_timeout: API 调用的超时时间（秒）
            max_retries: API 调用的最大重试次数
            preferred_language: 用于生成的语言
            filter: 用于过滤内容块的函数
            
        返回:
            包含 (title, summary, keywords) 的单个元组或元组列表
        """
        # 如果未提供 filter，使用默认的 equidistant_filter
        if filter is None:
            filter = equidistant_filter
            
        upper_limit = 8192
        filtered_chunks_n = 14
        max_tokens = 512

        if isinstance(content, str):
            inputs = [content]
        else:
            inputs = content

        filename = filename or ""
        if not filename:
            filename_desc = ""
        else:
            filename_desc = f"Filename: {filename}\n"

        def get_text_generate(_requests):
            language_desc = ""
            prompt = NOTE_SUMMARY_PROMPT.replace("{language_desc}", language_desc)
            messages = [
                [
                    {"role": "user", "content": prompt.format(**_request)},
                    {
                        "role": "system",
                        "content": f"""User Preferred Language: {preferred_language}, you should use this language to generate the title, summary.
                    Don't to start the summary section with sentences like "This document", "This text" or "This article", but describe the content directly.""",
                    },
                ]
                for _request in _requests
            ]

            logger.info("generate inputs: %s", _requests)

            responses = [
                self.client.chat.completions.create(
                    model=self.model_name,
                    messages=msg,
                    max_tokens=max_tokens,
                    temperature=0.0,
                    timeout=request_timeout,
                )
                for msg in messages
            ]

            return responses

        spliter = TokenParagraphSplitter(chunk_size=512, chunk_overlap=0)
        if filter is self.__serial_summary_filter:
            # 串行细粒度全文摘要
            chunks_list = [spliter.split_text(each) for each in inputs]
            # 所需的最大摘要次数 [K 个摘要可以处理包含 5K+1 个块的文档]
            max_summary_times = int(
                (max([len(chunks) for chunks in chunks_list]) + 4) / 5
            )
            results = [() for i in range(len(inputs))]
            # 使用第一个块内容初始化摘要
            # 如果块长度为 0，则设置为空字符串
            summaries = [chunks[0] if len(chunks) > 0 else "" for chunks in chunks_list]
            # 当块长度为 1 时，设置为 [""]，需要一个摘要
            # 当块长度为 0 时，设置为空列表，不需要摘要
            chunks_list = [
                [] if len(chunks) == 0 else ([""] if len(chunks) == 1 else chunks[1:])
                for chunks in chunks_list
            ]
            for i in range(max_summary_times):
                use_contents = self.__serial_summary_filter(summaries, chunks_list)
                requests = [
                    {
                        "content": use_content,
                        "file_type": file_type,
                        "filename_desc": filename_desc,
                    }
                    for use_content in use_contents
                ]
                responses = get_text_generate(requests)
                tmp_results = get_summarize_title_keywords(responses)
                for doc_id, chunks in enumerate(chunks_list):
                    index = 0
                    # 参与此轮摘要的文档
                    if len(chunks) > 0:
                        # 更新结果（标题、摘要、关键词）
                        results[doc_id] = tmp_results[index]
                        # 更新摘要列表
                        summaries[doc_id] = tmp_results[index][1]
                        # 更新待摘要的块列表
                        chunks_list[doc_id] = chunks_list[doc_id][5:]
                        index += 1
        else:
            requests = []
            for each in inputs:
                splits = spliter.split_text(each)
            # 基于采样的全文摘要方法
            # 保留开头和结尾，可以跳过中间部分。结尾对于公司签名和信息很有用，减少模型幻觉
            # 同时在结尾保留一个额外的块，以避免最终块过短导致信息不足的问题
            use_content = chunk_filter(
                splits,
                filter,
                filtered_chunks_n=filtered_chunks_n,
                separator="\n",
                spacer="\n……\n……\n……\n",
            )

            requests.append(
                {
                    "content": get_safe_content_turncate(
                        use_content,
                        self.model_name.replace("openai/", ""),
                        max_tokens=upper_limit,
                    ),
                    "file_type": file_type,
                    "filename_desc": filename_desc,
                }
            )
            responses = get_text_generate(requests)
            results = get_summarize_title_keywords(responses)

        logger.debug("results: %s", results)
        if isinstance(content, str):
            return results[0]
        else:
            return results

    def summarizer(self, inputs: SummarizerInput) -> Dict[str, Any]:
        """从文档输入生成摘要
        
        参数:
            inputs: 包含文件信息和洞察的结构化输入参数
            
        返回:
            包含 title、summary 和 keywords 的字典
        """
        bottom_summary_len = 200

        datatype = inputs.file_info.data_type
        filename = inputs.file_info.filename
        md = inputs.file_info.content  # hint

        inner_content = inputs.file_info.file_content.get("content")
        insight = inputs.insight

        md = md + "\n" + inner_content

        md = f"insight: {insight}\ncontent: {md}"

        try:
            datatype = DataType(datatype)
        except ValueError:
            logger.warning("Unsupported dataType: %s. Processing as DOCUMENT by default", datatype)
            datatype = DataType.DOCUMENT

        logger.info("input filename=%s", filename)
        logger.info("input content=%s (first 100 characters)", md.strip()[:100])
        t0 = time.time()
        bottom_summary = self._tokenizer.decode(
            self._tokenizer.encode(insight)[:bottom_summary_len]
        )

        if len(self._tokenizer.encode(md)) > 20:
            title, summary, keywords = self._summarize_title_abstract_keywords(
                md,
                filename=filename,
                file_type=datatype.value,
                request_timeout=self.timeout_summarize,
                max_retries=self.max_retries_summarize,
                preferred_language=self.preferred_language,
            )
            if not (title or summary or keywords):
                logger.warning("summary failed, use insight as summary")
                title, summary, keywords = filename, bottom_summary, []
                if filename:
                    title = filename
        else:
            logger.warning("less than 20 characters, use filename as title")
            title, summary, keywords = md, md, []
            if filename:
                title = filename

        t1 = time.time()
        logger.warning(
            "MarkdownChunkAPI summarize_title_abstract_keywords(): time spent %.2f seconds, title=%s, summary=%s",
            t1 - t0,
            title,
            summary,
        )

        return {"title": title, "summary": summary, "keywords": keywords}
