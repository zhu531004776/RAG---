from __future__ import annotations

from math import ceil

from models.document import Document

DEFAULT_DOCUMENTS_PAGE_SIZE = 10


def sort_documents_for_display(docs: list[Document]) -> list[Document]:
    """按上传时间倒序展示文档；无法解析时间时按原始字符串回退。"""
    return sorted(docs, key=lambda doc: doc.upload_time, reverse=True)


def filter_documents_by_name(docs: list[Document], keyword: str) -> list[Document]:
    """基于文档名称执行不区分大小写的模糊匹配。"""
    normalized_keyword = keyword.strip().lower()
    if not normalized_keyword:
        return list(docs)

    return [
        doc
        for doc in docs
        if normalized_keyword in doc.file_name.lower()
    ]


def paginate_documents(
    docs: list[Document], page: int, page_size: int = DEFAULT_DOCUMENTS_PAGE_SIZE
) -> tuple[list[Document], int, int, int]:
    """返回当前页数据、纠正后的页码、总页数和总条数。"""
    total_items = len(docs)
    total_pages = max(1, ceil(total_items / page_size)) if page_size > 0 else 1
    safe_page = min(max(page, 1), total_pages)

    start_index = (safe_page - 1) * page_size
    end_index = start_index + page_size
    return docs[start_index:end_index], safe_page, total_pages, total_items
