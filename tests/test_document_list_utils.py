import unittest

from models.document import Document, ProcessStatus
from document_list_utils import (
    DEFAULT_DOCUMENTS_PAGE_SIZE,
    filter_documents_by_name,
    paginate_documents,
    sort_documents_for_display,
)


def build_document(index: int, file_name: str) -> Document:
    return Document(
        doc_id=f"doc-{index}",
        file_name=file_name,
        file_path=f"/tmp/{file_name}",
        file_type=".txt",
        upload_time=f"2026-06-{index:02d} 10:00:00",
        status=ProcessStatus.COMPLETED,
        chunk_count=index,
    )


class DocumentListUtilsTest(unittest.TestCase):
    def test_filter_documents_by_name_is_case_insensitive(self):
        docs = [
            build_document(1, "产品需求文档.md"),
            build_document(2, "Technical-Design.md"),
            build_document(3, "会议纪要.txt"),
        ]

        filtered_docs = filter_documents_by_name(docs, "design")

        self.assertEqual([doc.file_name for doc in filtered_docs], ["Technical-Design.md"])

    def test_paginate_documents_returns_expected_second_page(self):
        docs = [build_document(index, f"文档-{index:02d}.txt") for index in range(1, 16)]

        page_docs, current_page, total_pages, total_items = paginate_documents(
            docs,
            page=2,
            page_size=DEFAULT_DOCUMENTS_PAGE_SIZE,
        )

        self.assertEqual(current_page, 2)
        self.assertEqual(total_pages, 2)
        self.assertEqual(total_items, 15)
        self.assertEqual(len(page_docs), 5)
        self.assertEqual(page_docs[0].file_name, "文档-11.txt")
        self.assertEqual(page_docs[-1].file_name, "文档-15.txt")

    def test_paginate_documents_clamps_page_after_search(self):
        docs = [build_document(index, f"测试文档-{index:02d}.txt") for index in range(1, 13)]
        filtered_docs = filter_documents_by_name(docs, "01")

        page_docs, current_page, total_pages, total_items = paginate_documents(
            filtered_docs,
            page=2,
            page_size=DEFAULT_DOCUMENTS_PAGE_SIZE,
        )

        self.assertEqual(current_page, 1)
        self.assertEqual(total_pages, 1)
        self.assertEqual(total_items, 1)
        self.assertEqual([doc.file_name for doc in page_docs], ["测试文档-01.txt"])

    def test_sort_documents_for_display_orders_by_upload_time_desc(self):
        docs = [
            build_document(1, "最早文档.txt"),
            build_document(3, "最新文档.txt"),
            build_document(2, "中间文档.txt"),
        ]

        sorted_docs = sort_documents_for_display(docs)

        self.assertEqual(
            [doc.file_name for doc in sorted_docs],
            ["最新文档.txt", "中间文档.txt", "最早文档.txt"],
        )


if __name__ == "__main__":
    unittest.main()
