from collections import defaultdict
from typing import Any, Dict, List, Optional, Union
import copy
import itertools
import json
import math
import traceback
import logging

from openai import OpenAI
from scipy.cluster.hierarchy import fcluster, linkage
import numpy as np

from app.core.config import settings
from app.services.L1.bio import Cluster, Memory, Note

logger = logging.getLogger(__name__)

# 从 prompt.py 导入 prompt 常量
from app.services.L1.prompt import (
    SYS_COMB,
    USR_COMB,
    TOPICS_TEMPLATE_SYS,
    TOPICS_TEMPLATE_USR,
)

# find_connected_components 函数实现
def find_connected_components(cluster_list, distance):
    """查找连接的组件 - 基于距离阈值查找可以连接的聚类
    
    使用简单的连通性检查：如果两个聚类中心之间的距离小于阈值，则认为它们连通。
    通过传递闭包找到所有连通的聚类组。
    
    Args:
        cluster_list: 聚类列表
        distance: 距离阈值
        
    Returns:
        连接的聚类组列表，每个组包含可以合并的聚类
    """
    if len(cluster_list) <= 1:
        return []
    
    n = len(cluster_list)
    # 构建邻接矩阵：如果两个聚类距离小于阈值，则连通
    adjacency = [[False] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(i + 1, n):
            # 计算聚类中心之间的欧氏距离
            dist = np.linalg.norm(cluster_list[i].cluster_center - cluster_list[j].cluster_center)
            if dist < distance:
                adjacency[i][j] = True
                adjacency[j][i] = True
    
    # 使用深度优先搜索找到所有连通组件
    visited = [False] * n
    connected_groups = []
    
    def dfs(node, group):
        visited[node] = True
        group.append(node)
        for neighbor in range(n):
            if not visited[neighbor] and adjacency[node][neighbor]:
                dfs(neighbor, group)
    
    for i in range(n):
        if not visited[i]:
            group = []
            dfs(i, group)
            if len(group) > 1:  # 只返回包含多个聚类的组
                connected_groups.append([cluster_list[idx] for idx in group])
    
    return connected_groups


class TopicsGenerator:
    def __init__(self):
        """使用默认参数和配置初始化TopicsGenerator"""
        self.default_cophenetic_distance = 1.0
        self.default_outlier_cutoff_distance = 0.5
        self.default_cluster_merge_distance = 0.5
        self.topic_params = {
            "temperature": 0,
            "max_tokens": 1500,
            "top_p": 0,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "timeout": 30,
            "response_format": {"type": "json_object"},
        }
        # 直接使用 config.py 中的配置，参考 L1Generator
        self.client = OpenAI(
            api_key=settings.CHAT_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self.model_name = settings.CHAT_MODEL
        logger.info(f"使用模型: {self.model_name}")
        self.threshold = 0.85
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
            self.topic_params["top_p"] = 0.001
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
                **self.topic_params,
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
                        **self.topic_params,
                        **kwargs
                    )
            
            # 重新抛出异常
            raise

    def __find_nearest_cluster(self, cluster_list: List[Cluster], memory: Memory) -> tuple:
        """
        基于嵌入向量距离找到与记忆最近的聚类
        
        Args:
            cluster_list: 要搜索的聚类列表
            memory: 要查找最近聚类的记忆
            
        Returns:
            包含(最近聚类, 到聚类的距离)的元组
        """
        distances = [
            np.linalg.norm(memory.embedding - cluster.cluster_center)
            for cluster in cluster_list
        ]
        nearest_cluster_idx = np.argmin(distances)
        return cluster_list[nearest_cluster_idx], distances[nearest_cluster_idx]


    def __merge_closed_clusters(
        self, cluster_list: List[Cluster], cluster_merge_distance: float
    ) -> tuple:
        """
        基于距离阈值合并彼此接近的聚类
        
        Args:
            cluster_list: 要检查合并的聚类列表
            cluster_merge_distance: 合并聚类的距离阈值
            
        Returns:
            包含(合并的聚类ID列表, 合并的聚类列表)的元组
        """
        connected_clusters_list: List[List[Cluster]] = find_connected_components(
            cluster_list, cluster_merge_distance
        )
        connected_clusters_list = [cc for cc in connected_clusters_list if len(cc) > 1]
        merge_cluster_ids_list, merge_cluster_list = [], []
        for connected_clusters in connected_clusters_list:
            merge_cluster_ids = [cluster.cluster_id for cluster in connected_clusters]
            merge_cluster_ids_list.append(merge_cluster_ids)
            merge_cluster_list.append(self.__merge_clusters(connected_clusters))
        return merge_cluster_ids_list, merge_cluster_list


    def __merge_clusters(self, connected_clusters: List[Cluster]) -> Cluster:
        """
        将连接的聚类列表合并为单个聚类
        
        Args:
            connected_clusters: 要合并的聚类列表
            
        Returns:
            新的合并后的聚类
        """
        new_cluster = Cluster(clusterId=connected_clusters[0].cluster_id, is_new=True)
        for cluster in connected_clusters:
            new_cluster.extend_memory_list(cluster.memory_list)
        new_cluster.merge_list = [
            cluster.cluster_id for cluster in connected_clusters if not cluster.is_new
        ]
        return new_cluster


    def _clusters_update_strategy(
        self,
        cluster_list: List[Cluster],
        outlier_memory_list: List[Memory],
        new_memory_list: List[Memory],
        cophenetic_distance: float,
        outlier_cutoff_distance: float,
        cluster_merge_distance: float,
    ) -> tuple:
        """
        使用新记忆更新现有聚类并处理异常值
        
        Args:
            cluster_list: 现有聚类列表
            outlier_memory_list: 之前运行的异常值记忆列表
            new_memory_list: 要处理的新记忆列表
            cophenetic_distance: 层次聚类的距离阈值
            outlier_cutoff_distance: 确定异常值的距离阈值
            cluster_merge_distance: 合并聚类的距离阈值
            
        Returns:
            包含(更新的聚类, 新的异常值记忆)的元组
        """
        updated_cluster_ids = set()

        for memory in new_memory_list:
            if memory.embedding is None:
                continue
            nearest_cluster, distance = self.__find_nearest_cluster(
                cluster_list, memory
            )
            if distance < outlier_cutoff_distance:
                nearest_cluster.add_memory(memory)
                updated_cluster_ids.add(nearest_cluster.cluster_id)
            else:
                outlier_memory_list.append(memory)

        merge_cluster_ids_list, merge_cluster_list = self.__merge_closed_clusters(
            cluster_list, cluster_merge_distance
        )
        updated_cluster_list = [
            cluster
            for cluster in cluster_list
            if cluster.cluster_id in list(updated_cluster_ids)
        ]
        updated_cluster_list = [
            cluster
            for cluster in updated_cluster_list
            if cluster.cluster_id not in list(itertools.chain(*merge_cluster_ids_list))
        ]

        # 使用updated_cluster_list初始计算size_threshold
        size_threshold = math.sqrt(max([cluster.size for cluster in cluster_list]))

        # 合并updated_cluster_list和merge_cluster_list
        cluster_list = updated_cluster_list + merge_cluster_list

        # 如果合并后的cluster_list不为空，重新计算size_threshold
        if cluster_list:
            size_threshold = math.sqrt(max([cluster.size for cluster in cluster_list]))
        else:
            logger.info(
                "cluster_list after updated is empty, use size_threshold from raw cluster list"
            )

        if outlier_memory_list:
            (
                outlier_cluster_list,
                new_outlier_memory_list,
            ) = self._clusters_initial_strategy(
                outlier_memory_list, cophenetic_distance, size_threshold
            )
        else:
            outlier_cluster_list, new_outlier_memory_list = [], []

        return cluster_list + outlier_cluster_list, new_outlier_memory_list


    def _clusters_initial_strategy(
        self,
        memory_list: List[Memory],
        cophenetic_distance: float,
        size_threshold: int = None,
    ) -> tuple:
        """
        对没有现有聚类的记忆进行初始聚类策略
        
        Args:
            memory_list: 要聚类的记忆列表
            cophenetic_distance: 层次聚类的距离阈值
            size_threshold: 有效聚类的最小大小阈值
            
        Returns:
            包含(生成的聚类, 异常值记忆)的元组
        """
        for memory in memory_list:
            logger.info(f"memory embedding shape: {memory.embedding.shape}")
            logger.info(f"memory: {memory}")
        memory_embeddings = [memory.embedding for memory in memory_list]

        logger.info(f"memory_embeddings: {memory_embeddings}")

        if len(memory_embeddings) == 1:
            clusters = np.array([1])
        else:
            linked = linkage(memory_embeddings, method="ward")
            clusters = fcluster(linked, cophenetic_distance, criterion="distance")
        
        labels = clusters.tolist()

        cluster_dict = {}

        for memory, label in zip(memory_list, labels):
            if label not in cluster_dict:
                cluster_dict[label] = Cluster(clusterId=label, is_new=True)
            cluster_dict[label].add_memory(memory)

        cluster_list: List[Cluster] = self.__remove_immature_clusters(
            cluster_dict, size_threshold
        )
        # 对于初始策略，我们需要移除聚类边界附近的一些节点，保留聚类的主要组成部分
        for cluster in cluster_list:
            cluster.prune_outliers_from_cluster()
        in_cluster_memory_list = [
            memory.memory_id
            for cluster in cluster_list
            for memory in cluster.memory_list
        ]
        outlier_memory_list = [
            memory
            for memory in memory_list
            if memory.memory_id not in in_cluster_memory_list
        ]

        logger.info(f"cluster_list: {cluster_list}")
        logger.info(f"outlier_memory_list: {outlier_memory_list}")

        return cluster_list, outlier_memory_list


    def __remove_immature_clusters(self, cluster_list: dict, size_threshold: int = None) -> List[Cluster]:
        """
        移除过小的（不成熟的）聚类
        
        Args:
            cluster_list: 将聚类ID映射到Cluster对象的字典
            size_threshold: 低于此大小的聚类被视为不成熟的大小阈值
            
        Returns:
            满足大小阈值的聚类列表
        """
        if not size_threshold:
            max_cluster_size = max(cluster.size for cluster in cluster_list.values())
            size_threshold = math.sqrt(max_cluster_size)
        cluster_list = [
            cluster
            for _, cluster in cluster_list.items()
            if cluster.size >= size_threshold
        ]
        return cluster_list


    def generate_topics_for_shades(
        self,
        old_cluster_list,
        old_outlier_memory_list,
        new_memory_list,
        cophenetic_distance,
        outlier_cutoff_distance,
        cluster_merge_distance,
    ) -> dict:
        """
        通过更新现有聚类或创建新聚类为shades生成主题聚类
        
        Args:
            old_cluster_list: 现有聚类列表
            old_outlier_memory_list: 之前运行的异常值记忆列表
            new_memory_list: 要处理的新记忆列表
            cophenetic_distance: 层次聚类的距离阈值
            outlier_cutoff_distance: 确定异常值的距离阈值
            cluster_merge_distance: 合并聚类的距离阈值
            
        Returns:
            包含更新的聚类列表和异常值记忆列表的字典
        """
        cophenetic_distance = cophenetic_distance or self.default_cophenetic_distance
        outlier_cutoff_distance = (
            outlier_cutoff_distance or self.default_outlier_cutoff_distance
        )
        cluster_merge_distance = (
            cluster_merge_distance or self.default_cluster_merge_distance
        )

        new_memory_list = [Memory(**memory) for memory in new_memory_list]
        new_memory_list = [
            memory for memory in new_memory_list if memory.embedding is not None
        ]

        old_cluster_list = [Cluster(**cluster) for cluster in old_cluster_list]
        old_outlier_memory_list = [
            Memory(**memory) for memory in old_outlier_memory_list
        ]

        if not old_cluster_list:
            # 初始策略
            cluster_list, outlier_memory_list = self._clusters_initial_strategy(
                new_memory_list, cophenetic_distance
            )
        else:
            # 更新策略
            cluster_list, outlier_memory_list = self._clusters_update_strategy(
                old_cluster_list,
                old_outlier_memory_list,
                new_memory_list,
                cophenetic_distance,
                outlier_cutoff_distance,
                cluster_merge_distance,
            )

        logger.info(f"cluster_list num: {len(cluster_list)}")
        logger.info(
            f"in cluster memory num: {sum([len(cluster.memory_list) for cluster in cluster_list])}"
        )
        logger.info(f"outlier_memory_list num: {len(outlier_memory_list)}")

        return {
            "clusterList": [cluster.to_json() for cluster in cluster_list],
            "outlierMemoryList": [memory.to_json() for memory in outlier_memory_list],
        }


    def generate_topics(self, notes_list: List[Note]) -> dict:
        """
        从笔记列表生成主题
        
        Args:
            notes_list: 要处理的Note对象列表
            
        Returns:
            包含主题数据的字典
        """
        logger.info(f"notes_lst length: {len(notes_list)}")
        for i, note in enumerate(notes_list):
            logger.info(f"\nNote {i + 1}:")
            logger.info(f"  ID: {note.id}")
            logger.info(f"  Title: {note.title}")
            logger.info(f"  Content: {note.content[:200]}...")  # 仅显示前200个字符
            logger.info(f"  Create Time: {note.create_time}")
            logger.info(f"  Memory Type: {note.memory_type}")
            logger.info(f"  Number of chunks: {len(note.chunks)}")
            for j, chunk in enumerate(note.chunks):
                logger.info(f"    Chunk {j + 1}:")
                logger.info(f"      ID: {chunk.id}")
                logger.info(f"      Document ID: {chunk.document_id}")
                logger.info(
                    f"      Content: {chunk.content[:100]}..."
                )  # 仅显示前100个字符
                logger.info(f"      Has embedding: {chunk.embedding is not None}")
                if chunk.embedding is not None:
                    logger.info(f"      Embedding shape: {chunk.embedding.shape}")

        # 笔记清理预处理
        tmpTopics = self._cold_start(notes_list)

        return tmpTopics


    def _cold_start(self, notes_list: List[Note]) -> dict:
        """
        对笔记列表执行冷启动聚类
        
        Args:
            notes_list: 要处理的Note对象列表
            
        Returns:
            包含聚类数据的字典
        """
        embedding_matrix, clean_chunks, all_note_ids = self.__build_embedding_chunks(
            notes_list
        )
        logger.info(
            f"embedding_matrix shape: {len(embedding_matrix)}, clean_chunks length: {len(clean_chunks)}"
        )

        if len(embedding_matrix) == 0:
            logger.warning("No chunks found in the notes_lst")
            return None

        cluster_data = self.__cold_clusters(clean_chunks, embedding_matrix)
        return cluster_data


    def __cold_clusters(self, clean_chunks: List, embedding_matrix: List) -> dict:
        """
        使用层次聚类从头生成聚类
        
        Args:
            clean_chunks: 要处理的清理后的chunks列表
            embedding_matrix: chunks的嵌入向量矩阵
            
        Returns:
            包含聚类数据的字典
        """
        chunks_with_topics = self.__generate_topic_from_chunks(clean_chunks)
        if len(embedding_matrix) <= 1:
            # 直接使用当前chunk形成单个聚类
            chunk = chunks_with_topics[0]
            cluster_data = {}
            cluster_data[
                "0"
            ] = {  # 使用从0到len(cluster_data)的标准化cluster_id存储聚类数据
                "indices": [0],
                "docIds": [chunk.document_id],
                "contents": [chunk.content],
                "embedding": [chunk.embedding],
                "chunkIds": [chunk.id],
                "tags": chunk.tags,
                "topic": chunk.topic,
                "topicId": 0,
                "recTimes": 0,
            }
            return cluster_data

        Z = linkage(embedding_matrix, method="complete", metric="cosine")
        clusters = self.__collect_cluster_indices(Z, self.threshold)
        cluster_data = self.__gen_cluster_data(clusters, chunks_with_topics)

        return cluster_data


    def __collect_cluster_indices(self, Z: np.ndarray, threshold: float) -> dict:
        """
        从链接矩阵收集每个聚类的叶子索引
        
        Args:
            Z: 来自层次聚类的链接矩阵
            threshold: 形成聚类的距离阈值
            
        Returns:
            将聚类ID映射到每个聚类中点索引列表的字典
        """
        clusters = defaultdict(list)
        n = Z.shape[0] + 1
        cluster_id = n
        for i, merge in enumerate(Z):
            left, right, dist, _ = merge
            if dist < threshold:
                if left < n:
                    clusters[cluster_id].append(int(left))
                else:
                    clusters[cluster_id].extend(clusters.pop(left))

                if right < n:
                    clusters[cluster_id].append(int(right))
                else:
                    clusters[cluster_id].extend(clusters.pop(right))

                cluster_id += 1

        # 将cluster_id更改为0~len(clusters)
        new_cluster_id = 0
        new_clusters = {}
        for tmp_id, indices in clusters.items():
            new_clusters[new_cluster_id] = indices
            new_cluster_id += 1
        return new_clusters


    def __gen_cluster_data(self, clusters: dict, chunks_with_topics: List) -> dict:
        """
        从聚类索引和chunks生成详细的聚类数据
        
        Args:
            clusters: 将聚类ID映射到点索引列表的字典
            chunks_with_topics: 包含主题信息的chunks列表
            
        Returns:
            包含每个聚类详细信息的字典
        """
        cluster_data = {}
        docIds = [chunk.document_id for chunk in chunks_with_topics]
        contents = [chunk.content for chunk in chunks_with_topics]
        embeddings = [chunk.embedding for chunk in chunks_with_topics]
        tags = [chunk.tags for chunk in chunks_with_topics]
        topics = [chunk.topic for chunk in chunks_with_topics]
        chunkIds = [chunk.id for chunk in chunks_with_topics]
        topic_id = 0
        for cid, indices in clusters.items():
            c_tags = [tags[i] for i in indices]
            c_topics = [topics[i] for i in indices]

            # 假设gen_cluster_topic已修改为处理列表
            new_tags, new_topic = self.__gen_cluster_topic(c_tags, c_topics)
            cluster_data[cid] = {
                "indices": indices,
                "docIds": [docIds[i] for i in indices],
                "contents": [contents[i] for i in indices],
                "embedding": [embeddings[i] for i in indices],
                "chunkIds": [chunkIds[i] for i in indices],
                "tags": new_tags,
                "topic": new_topic,
                "topicId": topic_id,
                "recTimes": 0,
            }
            topic_id += 1
        return cluster_data


    def __gen_cluster_topic(self, c_tags: List, c_topics: List) -> tuple:
        """
        为聚类生成组合主题和标签
        
        Args:
            c_tags: 聚类中chunks的标签列表
            c_topics: 聚类中chunks的主题列表
            
        Returns:
            包含(new_tags, new_topic)的元组
        """
        messages = [
            {"role": "system", "content": SYS_COMB},
            {"role": "user", "content": USR_COMB.format(topics=c_topics, tags=c_tags)},
        ]
        res = self._call_llm_with_retry(messages)
        new_topic, new_tags = self.__parse_response(
            res.choices[0].message.content, "topic", "tags"
        )

        return new_tags, new_topic


    def __generate_topic_from_chunks(self, chunks: List) -> List:
        """
        为每个chunk生成主题和关键词
        
        Args:
            chunks: 要生成主题的chunks列表
            
        Returns:
            添加了主题和标签信息的chunks列表
        """
        chunks = copy.deepcopy(chunks)
        max_retries = 3  # 最大重试次数

        for chunk in chunks:
            for attempt in range(max_retries):
                try:
                    tmp_msg = [
                        {
                            "role": "system",
                            "content": TOPICS_TEMPLATE_SYS,
                        },
                        {
                            "role": "user",
                            "content": TOPICS_TEMPLATE_USR.format(chunk=chunk.content),
                        },
                    ]
                    logger.info(f"Attempt {attempt + 1}/{max_retries}")
                    logger.info(
                        f"Request messages: {json.dumps(tmp_msg, ensure_ascii=False)}"
                    )

                    answer = self._call_llm_with_retry(tmp_msg)
                    content = answer.choices[0].message.content
                    logger.info(f"Generated content: {content}")

                    topic, tags = self.__parse_response(content, "topic", "tags")
                    chunk.topic = topic
                    chunk.tags = tags
                    break  # 成功尝试后退出重试循环

                except Exception as e:
                    logger.warning(f"尝试 {attempt + 1} 失败: {str(e)}")
                    if attempt == max_retries - 1:  # 最后一次尝试失败
                        logger.error(
                            f"所有尝试都失败，chunk: {traceback.format_exc()}"
                        )
                        # 使用默认值或移除chunk
                        chunk.topic = "Unknown Topic"  # 设置默认值
                        chunk.tags = ["unclassified"]  # 设置默认值
                        # 或者: chunks.remove(chunk)  # 移除chunk

            return chunks


    def __parse_response(self, content: str, key1: str, key2: str) -> tuple:
        """
        解析JSON响应以提取特定值
        
        Args:
            content: 要解析的JSON字符串
            key1: 要提取的第一个键（通常是'topic'）
            key2: 要提取的第二个键（通常是'tags'）
            
        Returns:
            包含两个键值的元组
        """
        spl = key1 + '":'
        b = '{"' + spl + "".join(content.split(spl)[1:])
        c = b.split("}")[0] + "}"
        res_dict = json.loads(c)

        return res_dict[key1], res_dict[key2]


    def __build_embedding_chunks(self, notes_list: List[Note]) -> tuple:
        """
        从笔记列表构建嵌入向量矩阵和清理chunks
        
        Args:
            notes_list: 要处理的Note对象列表
            
        Returns:
            包含(embedding_matrix, clean_chunks, all_note_ids)的元组
        """
        all_chunks = [chunk for note in notes_list for chunk in note.chunks]
        all_chunks = [chunk for chunk in all_chunks if chunk.embedding is not None]
        all_note_ids = [note.id for note in notes_list]
        clean_chunks = []
        clean_ids = []
        clean_notes_lst = []
        # 使用内容chunk
        for note_id in all_note_ids:
            tmp_chunks_set = [
                chunk for chunk in all_chunks if chunk.document_id == note_id
            ]
            if len(tmp_chunks_set) == 0:
                continue
            elif len(tmp_chunks_set) == 1:
                clean_chunks.append(tmp_chunks_set[0])
                clean_ids.append(note_id)
                clean_notes_lst.append(
                    [note for note in notes_list if note.id == note_id][0]
                )
            else:
                clean_ids.append(note_id)
                clean_notes_lst.append(
                    [note for note in notes_list if note.id == note_id][0]
                )
                for chunk in tmp_chunks_set:
                    clean_chunks.append(chunk)

        # 形成嵌入向量矩阵
        embedding_matrix = [clean_chunk.embedding for clean_chunk in clean_chunks]

        return embedding_matrix, clean_chunks, all_note_ids
