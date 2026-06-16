# 文档数据模型

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid
import json
from pathlib import Path

class ProcessStatus(Enum):
    """文档处理状态枚举"""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Document:
    """
    文档元数据模型

    属性:
        doc_id: 文档唯一标识（UUID）
        file_name: 文件名
        file_path: 存储路径
        file_type: 文件扩展名
        upload_time: 上传时间
        status: 处理状态
        chunk_count: 切片数量（处理完成后）
        error_msg: 错误信息（失败时）
    """
    doc_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    file_name: str = ""
    file_path: str = ""
    file_type: str = ""
    upload_time: str = ""
    status: ProcessStatus = ProcessStatus.PROCESSING
    chunk_count: int = 0
    error_msg: Optional[str] = None

    @classmethod
    def create(cls, file_name: str, file_path: str, file_type: str):
        """
        创建文档实例的工厂方法

        Args:
            file_name: 文件名
            file_path: 存储路径
            file_type: 文件扩展名

        Returns:
            Document实例
        """
        return cls(
            file_name=file_name,
            file_path=file_path,
            file_type=file_type,
            upload_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            status=ProcessStatus.PROCESSING
        )

    def to_dict(self) -> dict:
        """转换为字典，用于JSON序列化"""
        return {
            "doc_id": self.doc_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "upload_time": self.upload_time,
            "status": self.status.value,
            "chunk_count": self.chunk_count,
            "error_msg": self.error_msg
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Document":
        """从字典恢复实例"""
        data["status"] = ProcessStatus(data["status"])
        return cls(**data)


class DocumentStore:
    """
    文档存储管理器

    负责将文档元数据持久化到JSON文件
    """

    def __init__(self, store_path: Path = None):
        """
        初始化文档存储

        Args:
            store_path: 存储文件路径，默认为 data/documents.json
        """
        if store_path is None:
            from config import DATA_DIR
            store_path = DATA_DIR / "documents.json"

        self.store_path = store_path
        self._documents = []
        self._load()

    def _load(self):
        """从文件加载文档列表"""
        if self.store_path.exists():
            with open(self.store_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._documents = [Document.from_dict(d) for d in data]
        else:
            self._documents = []

    def _save(self):
        """保存文档列表到文件"""
        with open(self.store_path, 'w', encoding='utf-8') as f:
            data = [doc.to_dict() for doc in self._documents]
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add(self, doc: Document):
        """添加文档"""
        self._documents.append(doc)
        self._save()

    def update(self, doc: Document):
        """更新文档"""
        for i, d in enumerate(self._documents):
            if d.doc_id == doc.doc_id:
                self._documents[i] = doc
                self._save()
                return
        raise ValueError(f"文档不存在: {doc.doc_id}")

    def get_all(self) -> list:
        """获取所有文档"""
        return self._documents

    def get_by_id(self, doc_id: str) -> Document:
        """根据ID获取文档"""
        for doc in self._documents:
            if doc.doc_id == doc_id:
                return doc
        raise ValueError(f"文档不存在: {doc_id}")

    def get_by_name(self, file_name: str) -> Document:
        """根据文件名获取文档"""
        for doc in self._documents:
            if doc.file_name == file_name:
                return doc
        return None

    def delete(self, doc_id: str):
        """删除文档"""
        self._documents = [d for d in self._documents if d.doc_id != doc_id]
        self._save()
