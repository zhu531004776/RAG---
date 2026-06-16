# PDF文档解析器

from pathlib import Path
from typing import List
import PyPDF2
from .base import BaseParser

class PDFParser(BaseParser):
    """
    PDF文档解析器

    使用PyPDF2库提取PDF文本内容，
    按换行符分割为段落
    """

    def parse(self, file_path: Path) -> List[str]:
        """
        解析PDF文件，提取文本内容

        实现步骤：
        1. 打开PDF文件
        2. 遍历每一页
        3. 提取页面文本
        4. 按换行符分割为段落

        Args:
            file_path: PDF文件路径

        Returns:
            paragraphs: 段落文本列表
        """
        paragraphs = []

        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)

                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if not text:
                        continue

                    # 按换行符分割，保留非空段落
                    page_paragraphs = [
                        p.strip() for p in text.split('\n')
                        if p.strip()
                    ]

                    # 合并过短的段落
                    merged = self._merge_short_paragraphs(page_paragraphs)
                    paragraphs.extend(merged)

        except Exception as e:
            raise RuntimeError(f"PDF解析失败: {file_path}, 错误: {e}")

        return paragraphs

    def _merge_short_paragraphs(self, paragraphs: List[str], min_length: int = 50) -> List[str]:
        """
        合并过短的段落，避免碎片化

        Args:
            paragraphs: 原始段落列表
            min_length: 最小段落长度

        Returns:
            合并后的段落列表
        """
        result = []
        current = ""

        for para in paragraphs:
            if len(para) < min_length and current:
                # 短段落合并到前一个
                current += " " + para
            else:
                if current:
                    result.append(current)
                current = para

        if current:
            result.append(current)

        return result
