from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from collections import Counter
from enum import Enum
import numpy as np
import json
import logging

# 导入数据库相关
from app.core.database import DatabaseSession
from app.models.l1 import L1Version, L1Bio, L1Shade, L1Cluster, L1ChunkTopic
from app.models.status_biography import StatusBiography

# 导入服务
from app.services.document_service import DocumentService
from app.services.L1.l1_generator import L1Generator

# 导入数据模型
from app.services.L1.bio import (
    Note,
    Bio,
    ShadeInfo,
    ShadeMergeInfo,
    Cluster,
    Chunk,
    Memory,
    Todo,
    Chat
)

logger = logging.getLogger(__name__)
document_service = DocumentService()


@dataclass
class L1GenerationResult:
    """L1生成结果数据类"""
    bio: Any  # Bio对象
    clusters: Dict[str, Any]  # 聚类结果
    chunk_topics: Dict[str, Any]  # Chunk topics结果
    role_id: Optional[str] = None  # 角色ID，从文档中提取
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典以便序列化"""
        def convert_value(v):
            if hasattr(v, 'to_dict'):
                return convert_value(v.to_dict())
            elif hasattr(v, 'to_json'):
                return convert_value(v.to_json())
            elif isinstance(v, Enum):
                return v.value
            elif isinstance(v, dict):
                return {k: convert_value(val) for k, val in v.items()}
            elif isinstance(v, (list, tuple)):
                return [convert_value(item) for item in v]
            elif isinstance(v, np.ndarray):
                return v.tolist()
            else:
                return v
        
        return {
            "bio": convert_value(self.bio),
            "clusters": convert_value(self.clusters),
            "chunk_topics": convert_value(self.chunk_topics)
        }


def extract_notes_from_documents(documents, db) -> tuple[List[Note], list]:
    """从文档中提取Note对象和记忆列表

    Args:
        documents: 包含L0数据的文档列表
        db: 数据库会话

    Returns:
        tuple: (notes_list, memory_list)
            - notes_list: Note对象列表
            - memory_list: 用于聚类的记忆字典列表
    """
    notes_list = []
    memory_list = []

    for doc in documents:
        doc_id = doc.get("id")
        doc_embedding = document_service.get_document_embedding(db, doc_id)
        chunks = document_service.get_document_chunks(db, doc_id)
        all_chunk_embeddings = document_service.get_chunk_embeddings_by_document_id(
            db, doc_id
        )

        if not doc_embedding:
            logger.warning(f"Document {doc_id} missing document embedding")
            continue
        if not chunks:
            logger.warning(f"Document {doc_id} missing chunks")
            continue
        if not all_chunk_embeddings:
            logger.warning(f"Document {doc_id} missing chunk embeddings")
            continue

        # 确保create_time是字符串格式
        create_time = doc.get("create_time")
        if isinstance(create_time, datetime):
            create_time = create_time.strftime("%Y-%m-%d %H:%M:%S")

        # 构建Note对象
        note = Note(
            noteId=doc_id,
            content=doc.get("raw_content", ""),
            createTime=create_time,
            memoryType="TEXT",
            embedding=np.array(doc_embedding),
            chunks=[
                Chunk(
                    id=f"{chunk.id}",
                    document_id=doc_id,
                    content=chunk.content,
                    embedding=np.array(all_chunk_embeddings.get(chunk.id))
                    if all_chunk_embeddings.get(chunk.id)
                    else None,
                    tags=chunk.tags if hasattr(chunk, "tags") else None,
                    topic=chunk.topic if hasattr(chunk, "topic") else None,
                )
                for chunk in chunks
                if all_chunk_embeddings.get(chunk.id)
            ],
            title=doc.get("title", ""),
            summary=doc.get("summary", ""),
            insight=doc.get("insight", ""),
            tags=doc.get("keywords", []),
        )
        notes_list.append(note)
        memory_list.append({"memoryId": str(doc_id), "embedding": doc_embedding})

    return notes_list, memory_list


def generate_l1_from_l0(role_id: Optional[str] = None) -> L1GenerationResult:
    """从L0数据生成L1级别的知识表示
    
    Args:
        role_id: 可选的角色ID，如果提供则只处理该角色的文档
    
    Returns:
        L1GenerationResult: L1生成结果
    """
    l1_generator = L1Generator()

    # 1. 准备数据
    with DatabaseSession.session() as db:
        documents = document_service.list_documents_with_l0(db, role_id=role_id)
        logger.info(f"找到 {len(documents)} 个包含L0数据的文档" + (f" (role_id={role_id})" if role_id else ""))

        # 2. 提取笔记和记忆
        notes_list, memory_list = extract_notes_from_documents(documents, db)

    if not notes_list or not memory_list:
        logger.error("未找到有效的文档进行处理")
        return None

    try:
        # 3. 生成L1数据
        # 3.1 生成主题
        clusters = l1_generator.gen_topics_for_shades(old_cluster_list=[], old_outlier_memory_list=[], new_memory_list=memory_list)
        logger.info(f"生成聚类: {bool(clusters)}")

        # 3.2 生成chunk topics
        chunk_topics = l1_generator.generate_topics(notes_list)
        logger.info(f"生成chunk topics: {bool(chunk_topics)}")

        # 在l1_manager.py中添加日志
        logger.info(f"chunk_topics内容: {chunk_topics}")

        # 3.3 为每个聚类生成特征并合并它们
        shades, shade_cluster_map = generate_shades(clusters, l1_generator, notes_list)
        shades_merge_infos = convert_from_shades_to_merge_info(shades, shade_cluster_map)

        logger.info(f"生成了 {len(shades)} 个shades")
        merged_shades = l1_generator.merge_shades(shades_merge_infos)
        logger.info(f"合并shades成功: {merged_shades.success}")
        logger.info(f"合并后的shades数量: {len(merged_shades.merge_shade_list) if merged_shades.success else 0}")

        # 将 merge_shade_list 转换为 ShadeInfo 字典列表
        # merge_shade_list 包含 {"shadeIds": [...], "centerEmbedding": [...]}
        # 需要根据 shadeIds 从原始 shades 中找到对应的 shade 信息
        shades_for_bio = convert_merge_shade_list_to_shades(
            merged_shades.merge_shade_list if merged_shades.success else [],
            shades
        )

        # 3.4 生成全局传记
        bio = l1_generator.gen_global_biography(
            old_profile=Bio(shadesList=shades_for_bio),
            cluster_list=clusters.get("clusterList", []),
        )
        logger.info(f"生成全局传记: {bio}")

        # 4. 构建结果对象
        result = L1GenerationResult(bio=bio, clusters=clusters, chunk_topics=chunk_topics, role_id=role_id)

        logger.info(f"L1生成成功完成，role_id: {role_id}")
        return result

    except Exception as e:
        logger.error(f"L1生成过程中出错: {str(e)}", exc_info=True)
        raise


def generate_shades(clusters, l1_generator, notes_list):
    shades = []
    shade_cluster_map = {}  # 保存 shade 和 cluster 的映射关系
    if clusters and "clusterList" in clusters:
        for idx, cluster in enumerate(clusters.get("clusterList", []), start=1):
            cluster_memory_ids = [str(m.get("memoryId")) for m in cluster.get("memoryList", [])]
            logger.info(f"Processing cluster with {len(cluster_memory_ids)} memories")

            cluster_notes = [
                note for note in notes_list 
                if str(note.id) in cluster_memory_ids
            ]
            if cluster_notes:
                shade = l1_generator.gen_shade_for_cluster([], cluster_notes, [])
                if shade:
                    # 为新生成的 shade 分配临时 ID（基于索引）
                    if shade.id is None:
                        shade.id = idx
                    shades.append(shade)
                    # 保存 shade 和对应 cluster 的映射关系
                    shade_cluster_map[shade.id] = cluster
                    logger.info(f"Generated shade for cluster: {shade.name if hasattr(shade, 'name') else 'Unknown'}, id: {shade.id}")
    return shades, shade_cluster_map

    
def convert_from_shades_to_merge_info(shades: List[ShadeInfo], shade_cluster_map: Dict[int, Dict] = None) -> List[ShadeMergeInfo]:
    """将ShadeInfo对象转换为ShadeMergeInfo对象"""
    if shade_cluster_map is None:
        shade_cluster_map = {}
    
    result = []
    for shade in shades:
        cluster_info = None
        if shade.id in shade_cluster_map:
            cluster = shade_cluster_map[shade.id]
            # 构建 cluster_info 字典，包含 shade_generator.py 中需要的字段
            cluster_info = {
                "clusterId": cluster.get("clusterId"),
                "centerEmbedding": cluster.get("centerEmbedding", []),
                "clusterSize": len(cluster.get("memoryList", [])),
                "memoryList": cluster.get("memoryList", [])
            }
        
        result.append(ShadeMergeInfo(
            id=shade.id,
            name=shade.name,
            aspect=shade.aspect,
            icon=shade.icon,
            desc_third_view=shade.desc_third_view,
            content_third_view=shade.content_third_view,
            desc_second_view=shade.desc_second_view,
            content_second_view=shade.content_second_view,
            cluster_info=cluster_info
        ))
    return result


def convert_merge_shade_list_to_shades(merge_shade_list: List[Dict[str, Any]], shades: List[ShadeInfo]) -> List[Dict[str, Any]]:
    """将 merge_shade_list 转换为 ShadeInfo 字典列表
    
    Args:
        merge_shade_list: merge_shades 返回的合并决策列表，格式为 [{"shadeIds": [...], "centerEmbedding": [...]}, ...]
        shades: 原始的 ShadeInfo 对象列表
        
    Returns:
        ShadeInfo 字典列表，可以直接用于创建 Bio 对象
    """
    if not merge_shade_list:
        return []
    
    # 创建 shade_id 到 shade 对象的映射
    shade_dict = {shade.id: shade for shade in shades}
    
    shades_for_bio = []
    for merge_group in merge_shade_list:
        shade_ids = merge_group.get("shadeIds", [])
        if not shade_ids:
            continue
        
        # 如果只有一个 shade，直接使用它
        if len(shade_ids) == 1:
            shade_id = int(shade_ids[0]) if isinstance(shade_ids[0], str) else shade_ids[0]
            if shade_id in shade_dict:
                shade = shade_dict[shade_id]
                # 使用 to_json() 方法转换为字典格式
                shades_for_bio.append(shade.to_json())
            else:
                logger.warning(f"未找到 shade_id={shade_id} 对应的 shade")
        else:
            # 如果多个 shades 合并，使用第一个 shade 作为代表
            # 注意：这里可能需要实际执行合并操作，但为了简化，先使用第一个
            shade_id = int(shade_ids[0]) if isinstance(shade_ids[0], str) else shade_ids[0]
            if shade_id in shade_dict:
                shade = shade_dict[shade_id]
                shades_for_bio.append(shade.to_json())
                logger.info(f"多个 shades {shade_ids} 合并，使用第一个 shade (id={shade_id}) 作为代表")
            else:
                logger.warning(f"未找到 shade_id={shade_id} 对应的 shade")
    
    return shades_for_bio


def store_status_bio(status_bio: Bio, role_id: Optional[str] = None) -> None:
    """将状态传记存储到数据库

    Args:
        status_bio (Bio): 生成的状态传记对象
        role_id: 可选的角色ID，如果提供则只删除和存储该角色的状态传记
    """
    try:
        with DatabaseSession.session() as session:
            # 删除旧的状态传记（如果存在）
            if role_id:
                session.query(StatusBiography).filter(StatusBiography.role_id == role_id).delete()
            else:
                session.query(StatusBiography).delete()

            # 插入新的状态传记
            new_bio = StatusBiography(
                role_id=role_id,
                content=status_bio.content_second_view,
                content_third_view=status_bio.content_third_view,
                summary=status_bio.summary_second_view,
                summary_third_view=status_bio.summary_third_view,
            )
            session.add(new_bio)
            session.commit()
    except Exception as e:
        logger.error(f"存储状态传记时出错: {str(e)}", exc_info=True)
        raise


def get_latest_status_bio() -> Optional[Any]:
    """获取最新的状态传记

    Returns:
        Optional[Any]: 状态传记的数据传输对象，如果未找到则返回None
        注意：需要定义StatusBioDTO类以进行正确的类型标注
    """
    try:
        with DatabaseSession.session() as session:
            # 获取最新的状态传记
            latest_bio = (
                session.query(StatusBiography)
                .order_by(StatusBiography.create_time.desc())
                .first()
            )

            if not latest_bio:
                return None

            # TODO: 当StatusBioDTO定义后转换为DTO
            # return StatusBioDTO.from_model(latest_bio)
            return latest_bio
    except Exception as e:
        logger.error(f"获取状态传记时出错: {str(e)}", exc_info=True)
        return None


def get_latest_global_bio() -> Optional[Any]:
    """获取最新的全局传记

    Returns:
        Optional[Any]: 全局传记的数据传输对象，如果未找到则返回None
        注意：需要定义GlobalBioDTO类以进行正确的类型标注
    """
    try:
        with DatabaseSession.session() as session:
            # 获取最新的L1数据版本
            latest_version = (
                session.query(L1Version).order_by(L1Version.version.desc()).first()
            )

            if not latest_version:
                return None

            # 获取此版本的bio数据
            bio = (
                session.query(L1Bio)
                .filter(L1Bio.version == latest_version.version)
                .first()
            )

            if not bio:
                return None

            # TODO: 当GlobalBioDTO定义后转换为DTO
            # return GlobalBioDTO.from_model(bio)
            return bio
    except Exception as e:
        logger.error(f"获取全局传记时出错: {str(e)}", exc_info=True)
        return None


def generate_and_store_status_bio(role_id: Optional[str] = None) -> Bio:
    """生成并存储状态传记

    Args:
        role_id: 可选的角色ID，如果提供则只生成和存储该角色的状态传记

    Returns:
        Bio: 生成的状态传记对象
    """
    # 生成状态传记
    status_bio = generate_status_bio(role_id=role_id)
    if status_bio:
        # 存储到数据库
        store_status_bio(status_bio, role_id=role_id)
    return status_bio


def generate_status_bio(role_id: Optional[str] = None) -> Bio:
    """生成状态传记

    Args:
        role_id: 可选的角色ID，如果提供则只生成该角色的状态传记

    Returns:
        Bio: 生成的状态传记
    """
    l1_generator = L1Generator()

    try:
        # 1. 获取所有文档并提取笔记
        with DatabaseSession.session() as db:
            documents = document_service.list_documents_with_l0(db, role_id=role_id)
            notes_list, _ = extract_notes_from_documents(documents, db)

        if not notes_list:
            error_msg = f"未找到有效的笔记用于生成状态传记" + (f" (role_id={role_id})" if role_id else "")
            logger.error(error_msg)
            return None

        # 2. 生成状态传记
        # 目前我们只使用笔记，todos和chats暂时为空列表
        current_time = datetime.now().strftime("%Y-%m-%d")
        status_bio = l1_generator.gen_status_biography(
            cur_time=current_time,
            notes=notes_list,
            todos=[],  # 暂时为空
            chats=[],  # 暂时为空
        )

        logger.info("状态传记生成成功")
        return status_bio

    except Exception as e:
        logger.error(f"生成状态传记时出错: {str(e)}", exc_info=True)
        raise


def store_l1_data(session, result: L1GenerationResult, role_id: Optional[str] = None) -> int:
    """将L1生成结果存储到数据库
    
    Args:
        session: 数据库会话
        result: L1GenerationResult对象
        role_id: 可选的角色ID，如果不提供则使用 result.role_id
        
    Returns:
        int: 版本号
    """
    # 使用传入的 role_id 或从 result 中获取
    if role_id is None:
        role_id = result.role_id if hasattr(result, 'role_id') else None
    
    # 检查 role_id 是否有效（数据库要求 role_id 不能为 NULL）
    if not role_id:
        error_msg = "role_id 是必需的，但未提供。请确保文档包含有效的 role_id。"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # 1. 存储版本
        version_number = __store_version(session, role_id)
        # 立即 flush，确保 L1Version 记录写入数据库，以便后续的外键约束检查通过
        session.flush()
        
        # 2. 存储bio
        __store_bio(session, result.bio, version_number, role_id)
        
        # 3. 存储shades
        if hasattr(result.bio, 'shades_list') and result.bio.shades_list:
            __store_shades(session, result.bio.shades_list, version_number, role_id)
        
        # 4. 存储clusters
        __store_clusters(session, result.clusters, version_number)
        
        # 5. 存储chunk topics
        __store_chunk_topics(session, result.chunk_topics, version_number)
        
        # 6. 提交事务
        session.commit()
        logger.info(f"L1数据已成功存储，版本号: {version_number}")
        
        return version_number
    except Exception as e:
        logger.error(f"存储L1数据时出错: {str(e)}", exc_info=True)
        session.rollback()  # 发生错误时回滚事务
        raise


def __store_version(session, role_id: Optional[str] = None) -> int:
    """存储L1版本记录"""
    # 获取全局最大版本号
    max_version = session.query(L1Version).order_by(L1Version.version.desc()).first()
    next_version = (max_version.version + 1) if max_version else 1
    
    # 创建新版本记录
    new_version = L1Version(
        version=next_version,
        status='active',
        description='L1 data generated from L0',
        role_id=role_id
    )
    session.add(new_version)
    return next_version


def __store_bio(session, bio: Bio, version: int, role_id: Optional[str] = None):
    """存储L1 bio记录"""
    new_bio = L1Bio(
        version=version,
        role_id=role_id,
        content=bio.content_second_view,
        content_third_view=bio.content_third_view,
        summary=bio.summary_second_view,
        summary_third_view=bio.summary_third_view
    )
    session.add(new_bio)


def __store_shades(session, shades: List[ShadeInfo], version: int, role_id: Optional[str] = None):
    """存储L1 shades记录"""
    for shade in shades:
        new_shade = L1Shade(
            version=version,
            role_id=role_id,
            name=shade.name,
            aspect=shade.aspect,
            icon=shade.icon,
            desc_third_view=shade.desc_third_view,
            content_third_view=shade.content_third_view,
            desc_second_view=shade.desc_second_view,
            content_second_view=shade.content_second_view
        )
        session.add(new_shade)


def __store_clusters(session, clusters: Dict[str, Any], version: int):
    """存储L1 clusters记录"""
    cluster_list = clusters.get("clusterList", [])
    for idx, cluster in enumerate(cluster_list):
        memory_list = cluster.get("memoryList", [])
        memory_ids = [str(m.get("memoryId", "")) for m in memory_list]
        
        # 获取聚类中心（如果有）
        cluster_center = None
        if "center" in cluster:
            cluster_center = json.dumps(cluster["center"])
        elif "clusterCenter" in cluster:
            cluster_center = json.dumps(cluster["clusterCenter"])
        
        new_cluster = L1Cluster(
            version=version,
            cluster_id=str(cluster.get("clusterId", f"cluster_{idx}")),
            memory_ids=json.dumps(memory_ids) if memory_ids else None,
            cluster_center=cluster_center
        )
        session.add(new_cluster)


def __store_chunk_topics(session, chunk_topics: Dict[str, Any], version: int):
    """存储L1 chunk topics记录"""
    # chunk_topics可能是一个字典，包含chunk_id到topic的映射
    # 或者是一个列表，包含多个chunk topic对象
    if isinstance(chunk_topics, dict):
        for chunk_id, topic_data in chunk_topics.items():
            if isinstance(topic_data, dict):
                topic = topic_data.get("topic", "")
                tags = topic_data.get("tags", [])
            else:
                topic = str(topic_data)
                tags = []
            
            new_chunk_topic = L1ChunkTopic(
                version=version,
                chunk_id=str(chunk_id),
                topic=topic if topic else None,
                tags=json.dumps(tags, ensure_ascii=False) if tags else None
            )
            session.add(new_chunk_topic)
    elif isinstance(chunk_topics, list):
        for item in chunk_topics:
            if isinstance(item, dict):
                chunk_id = item.get("chunk_id") or item.get("chunkId", "")
                topic = item.get("topic", "")
                tags = item.get("tags", [])
                
                new_chunk_topic = L1ChunkTopic(
                    version=version,
                    chunk_id=str(chunk_id),
                    topic=topic if topic else None,
                    tags=json.dumps(tags, ensure_ascii=False) if tags else None
                )
                session.add(new_chunk_topic)
