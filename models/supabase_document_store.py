from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import json
from pathlib import Path
from typing import Optional
import streamlit as st

from .document import Document, DocumentStore, ProcessStatus


class SupabaseDocumentStore:
    """使用 Supabase Postgres 存储文档元数据。"""

    def __init__(self, url: str, key: str, table_name: str = "documents"):
        try:
            from supabase import Client, create_client
        except ImportError as exc:
            raise ImportError(
                "未安装 supabase 依赖，请先执行 `pip install supabase` 或安装 requirements.txt。"
            ) from exc

        self.table_name = table_name
        self.url = url
        self.key = key
        self.client: Client = create_client(url, key)
        self._documents_cache: Optional[list[Document]] = None
        from config import DATA_DIR
        self.snapshot_path = DATA_DIR / f"{table_name}_supabase_snapshot.json"

    def _table(self):
        return self.client.table(self.table_name)

    @staticmethod
    def _normalize_status(status) -> str:
        return getattr(status, "value", status)

    @staticmethod
    def _serialize_timestamp(value: str) -> str:
        """统一写入格式，兼容现有字符串时间。"""
        if not value:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return parsed.isoformat()
        except ValueError:
            return value

    @staticmethod
    def _deserialize_timestamp(value: Optional[str]) -> str:
        """统一页面展示格式。"""
        if not value:
            return ""

        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")

        candidates = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
        ]
        raw_value = str(value).replace("Z", "+00:00")

        try:
            parsed = datetime.fromisoformat(raw_value)
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

        for fmt in candidates:
            try:
                parsed = datetime.strptime(str(value), fmt)
                return parsed.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

        return str(value)

    @classmethod
    def _doc_from_row(cls, row: dict) -> Document:
        status_value = row.get("status", ProcessStatus.PROCESSING.value)
        try:
            status = ProcessStatus(status_value)
        except ValueError:
            status = ProcessStatus.PROCESSING

        return Document(
            doc_id=row.get("doc_id", ""),
            file_name=row.get("file_name", ""),
            file_path=row.get("file_path", ""),
            file_type=row.get("file_type", ""),
            upload_time=cls._deserialize_timestamp(row.get("upload_time")),
            status=status,
            chunk_count=row.get("chunk_count", 0) or 0,
            error_msg=row.get("error_msg"),
        )

    def _doc_to_payload(self, doc: Document) -> dict:
        return {
            "doc_id": doc.doc_id,
            "file_name": doc.file_name,
            "file_path": doc.file_path,
            "file_type": doc.file_type,
            "upload_time": self._serialize_timestamp(doc.upload_time),
            "status": self._normalize_status(doc.status),
            "chunk_count": doc.chunk_count,
            "error_msg": doc.error_msg,
        }

    def _save_snapshot(self, docs: list[Document]) -> None:
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.snapshot_path, "w", encoding="utf-8") as snapshot_file:
            json.dump(
                [doc.to_dict() for doc in docs],
                snapshot_file,
                ensure_ascii=False,
                indent=2,
            )

    def _load_snapshot(self) -> Optional[list[Document]]:
        if not self.snapshot_path.exists():
            return None
        try:
            with open(self.snapshot_path, "r", encoding="utf-8") as snapshot_file:
                data = json.load(snapshot_file)
            return [Document.from_dict(item) for item in data]
        except Exception:
            return None

    def _update_local_snapshot(self, docs: list[Document]) -> None:
        self._documents_cache = self._clone_docs(docs)
        self._save_snapshot(self._documents_cache)

    def refresh_from_remote(self) -> list[Document]:
        response = self._table().select("*").order("upload_time").execute()
        rows = getattr(response, "data", []) or []
        docs = [self._doc_from_row(row) for row in rows]
        self._update_local_snapshot(docs)
        return self._clone_docs(docs)

    @staticmethod
    def _clone_doc(doc: Document) -> Document:
        return Document.from_dict(doc.to_dict())

    @classmethod
    def _clone_docs(cls, docs: list[Document]) -> list[Document]:
        return [cls._clone_doc(doc) for doc in docs]

    def add(self, doc: Document):
        self._table().insert(self._doc_to_payload(doc)).execute()
        docs = self._documents_cache or self._load_snapshot() or []
        docs = [existing for existing in docs if existing.doc_id != doc.doc_id]
        docs.append(self._clone_doc(doc))
        self._update_local_snapshot(docs)

    def update(self, doc: Document):
        response = (
            self._table()
            .update(self._doc_to_payload(doc))
            .eq("doc_id", doc.doc_id)
            .execute()
        )
        if not getattr(response, "data", None):
            raise ValueError(f"文档不存在: {doc.doc_id}")
        docs = self._documents_cache or self._load_snapshot() or []
        updated = False
        for index, existing in enumerate(docs):
            if existing.doc_id == doc.doc_id:
                docs[index] = self._clone_doc(doc)
                updated = True
                break
        if not updated:
            docs.append(self._clone_doc(doc))
        self._update_local_snapshot(docs)

    def get_all(self) -> list:
        if self._documents_cache is not None:
            return self._clone_docs(self._documents_cache)
        snapshot_docs = self._load_snapshot()
        if snapshot_docs is not None:
            self._documents_cache = snapshot_docs
            return self._clone_docs(snapshot_docs)
        response = self._table().select("*").order("upload_time").execute()
        rows = getattr(response, "data", []) or []
        docs = [self._doc_from_row(row) for row in rows]
        self._update_local_snapshot(docs)
        return self._clone_docs(docs)

    def get_by_id(self, doc_id: str) -> Document:
        response = self._table().select("*").eq("doc_id", doc_id).limit(1).execute()
        rows = getattr(response, "data", []) or []
        if not rows:
            raise ValueError(f"文档不存在: {doc_id}")
        return self._doc_from_row(rows[0])

    def get_by_name(self, file_name: str) -> Optional[Document]:
        response = (
            self._table().select("*").eq("file_name", file_name).limit(1).execute()
        )
        rows = getattr(response, "data", []) or []
        if not rows:
            return None
        return self._doc_from_row(rows[0])

    def delete(self, doc_id: str):
        self._table().delete().eq("doc_id", doc_id).execute()
        docs = self._documents_cache or self._load_snapshot() or []
        docs = [existing for existing in docs if existing.doc_id != doc_id]
        self._update_local_snapshot(docs)


@st.cache_resource(show_spinner=False)
@lru_cache(maxsize=4)
def _get_cached_document_store(
    use_supabase_doc_store: bool,
    supabase_url: str,
    supabase_key: str,
    supabase_documents_table: str,
) -> DocumentStore | SupabaseDocumentStore:
    if not use_supabase_doc_store:
        return DocumentStore()

    if not supabase_url or not supabase_key:
        return DocumentStore()

    return SupabaseDocumentStore(
        url=supabase_url,
        key=supabase_key,
        table_name=supabase_documents_table,
    )


def create_document_store() -> DocumentStore | SupabaseDocumentStore:
    """优先使用 Supabase，失败时回退到本地 JSON。"""
    import config

    use_supabase_doc_store = getattr(config, "USE_SUPABASE_DOC_STORE", False)
    supabase_url = getattr(config, "SUPABASE_URL", "")
    supabase_key = getattr(config, "SUPABASE_KEY", "")
    supabase_documents_table = getattr(config, "SUPABASE_DOCUMENTS_TABLE", "documents")

    if not use_supabase_doc_store:
        return _get_cached_document_store(
            use_supabase_doc_store,
            supabase_url,
            supabase_key,
            supabase_documents_table,
        )

    if not supabase_url or not supabase_key:
        return _get_cached_document_store(
            use_supabase_doc_store,
            supabase_url,
            supabase_key,
            supabase_documents_table,
        )

    try:
        store = _get_cached_document_store(
            use_supabase_doc_store,
            supabase_url,
            supabase_key,
            supabase_documents_table,
        )
        return store
    except Exception as exc:
        print(f"初始化 SupabaseDocumentStore 失败，已回退到本地 DocumentStore: {exc}")
        return DocumentStore()
