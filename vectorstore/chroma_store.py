# Chroma向量存储封装

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import uuid
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from chunker import TextChunk

@dataclass
class SearchResult:
    """
    检索结果数据结构

    属性:
        content: 原文片段
        doc_name: 文档名称
        chunk_index: 切片序号
        distance: 余弦距离（越小越相似）
    """
    content: str
    doc_name: str
    chunk_index: int
    distance: float


class VectorStore:
    """
    向量存储管理器

    职责：
    1. 管理Embedding模型生命周期
    2. 管理Chroma向量数据库
    3. 提供文档切片的向量化存储接口
    4. 提供语义检索接口
    """

    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        persist_directory: Optional[Path] = None,
        device: str = "cpu"
    ):
        """
        初始化向量存储

        Args:
            embedding_model: HuggingFace模型名称或本地路径
            persist_directory: 向量库持久化目录
            device: 运行设备 ("cpu" 或 "cuda")
        """
        # 初始化Embedding模型
        self.embedding_model = SentenceTransformer(
            embedding_model,
            device=device
        )

        # 初始化Chroma客户端
        if persist_directory:
            persist_directory = str(persist_directory)
            chroma_settings = Settings(
                persist_directory=persist_directory,
                anonymized_telemetry=False
            )
            self.client = chromadb.PersistentClient(path=persist_directory)
        else:
            self.client = chromadb.Client()

        self.collection_name = "documents"

        # 获取或创建Collection（使用余弦相似度）
        try:
            self.collection = self.client.get_collection(
                name=self.collection_name
            )
        except Exception:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )

    def add_chunks(self, chunks: List[TextChunk]) -> None:
        """
        添加文档切片到向量库

        实现步骤：
        1. 提取所有切片的原文文本
        2. 批量计算文本的Embedding向量
        3. 构建元数据（文档名、切片序号、段落序号）
        4. 批量添加到Chroma Collection

        Args:
            chunks: TextChunk列表
        """
        if not chunks:
            return

        # 准备数据
        texts = [chunk.content for chunk in chunks]
        embeddings = self.embedding_model.encode(texts)
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [
            {
                "content": chunk.content,
                "doc_name": chunk.doc_name,
                "chunk_index": chunk.chunk_index,
                "para_index": chunk.original_para_idx
            }
            for chunk in chunks
        ]

        # 添加到向量库
        self.collection.add(
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )

    def search(
        self,
        query_text: str,
        top_k: int = 3
    ) -> List[SearchResult]:
        """
        语义检索：查找与查询文本最相关的切片

        实现步骤：
        1. 将查询文本转换为Embedding向量
        2. 在向量库中搜索余弦相似度最高的Top-K结果
        3. 封装结果并返回

        Args:
            query_text: 用户查询文本
            top_k: 返回结果数量

        Returns:
            SearchResult列表，按相似度降序排列
        """
        # 查询向量化和搜索
        query_embedding = self.embedding_model.encode([query_text])

        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        # 封装结果
        search_results = []
        if results['documents'] and len(results['documents']) > 0:
            for i in range(len(results['documents'][0])):
                search_results.append(SearchResult(
                    content=results['documents'][0][i],
                    doc_name=results['metadatas'][0][i]['doc_name'],
                    chunk_index=results['metadatas'][0][i]['chunk_index'],
                    distance=results['distances'][0][i]
                ))

        return search_results

    def delete_by_doc_name(self, doc_name: str) -> None:
        """
        删除指定文档的所有切片

        Args:
            doc_name: 文档名称
        """
        # 获取该文档的所有条目
        results = self.collection.get(
            where={"doc_name": doc_name}
        )

        if results['ids']:
            self.collection.delete(ids=results['ids'])

    def get_all_doc_names(self) -> List[str]:
        """
        获取向量库中所有文档名称列表

        Returns:
            文档名称列表（去重）
        """
        # 获取所有数据再提取文档名
        try:
            results = self.collection.get(include=["metadatas"])
        except Exception:
            return []

        doc_names = set()
        for metadata in results.get('metadatas', []):
            if metadata:
                doc_names.add(metadata['doc_name'])

        return list(doc_names)

    def get_chunk_count(self) -> int:
        """
        获取向量库中切片总数

        Returns:
            切片数量
        """
        return self.collection.count()

    def clear(self) -> None:
        """清空向量库（慎用）"""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception:
            pass
