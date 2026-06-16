# Word文档(.docx)解析器

from pathlib import Path
from typing import List
from docx import Document
from .base import BaseParser

class DocxParser(BaseParser):
    """
    Word文档(.docx)解析器

    使用python-docx库提取Word文档中的段落文本，
    按段落元素遍历，保留文档结构
    """

    def parse(self, file_path: Path) -> List[str]:
        """
        解析Word文档，提取段落文本

        实现步骤：
        1. 打开docx文档
        2. 遍历每个段落元素
        3. 提取段落文本内容
        4. 过滤空段落

        Args:
            file_path: Word文件路径

        Returns:
            paragraphs: 段落文本列表
        """
        paragraphs = []

        try:
            doc = Document(file_path)

            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue

                # 过滤掉仅有格式但无实际内容的段落
                if len(text) < 2:
                    continue

                paragraphs.append(text)

        except Exception as e:
            raise RuntimeError(f"Word文档解析失败: {file_path}, 错误: {e}")

        # 合并连续过短的段落
        merged = self._merge_short_paragraphs(paragraphs)
        return merged

    def _merge_short_paragraphs(self, paragraphs: List[str], min_length: int = 50) -> List[str]:
        """
        合并过短的段落

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
                current += " " + para
            else:
                if current:
                    result.append(current)
                current = para

        if current:
            result.append(current)

        return result
