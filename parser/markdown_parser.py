# Markdown文档解析器

from pathlib import Path
from typing import List
import re
from .base import BaseParser

class MarkdownParser(BaseParser):
    """
    Markdown文档解析器

    读取Markdown文件后进行以下处理：
    1. 去除代码块（避免代码内容干扰）
    2. 去除行内代码
    3. 去除图片链接
    4. 保留链接文本
    5. 去除标题标记
    6. 去除加粗斜体标记
    7. 按双换行分割为段落
    """

    def parse(self, file_path: Path) -> List[str]:
        """
        解析Markdown文件，提取纯文本段落

        Args:
            file_path: Markdown文件路径

        Returns:
            paragraphs: 段落文本列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
        except Exception as e:
            raise RuntimeError(f"Markdown文件读取失败: {file_path}, 错误: {e}")

        # 去除代码块（避免代码内容干扰）
        md_content = re.sub(r'```.*?```', '', md_content, flags=re.DOTALL)
        # 去除行内代码
        md_content = re.sub(r'`[^`]+`', '', md_content)
        # 去除图片链接
        md_content = re.sub(r'!\[.*?\]\(.*?\)', '', md_content)
        # 去除链接，保留文本
        md_content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', md_content)
        # 去除标题标记（保留文字）
        md_content = re.sub(r'^#+\s+', '', md_content, flags=re.MULTILINE)
        # 去除加粗和斜体标记
        md_content = re.sub(r'\*\*([^\*]+)\*\*', r'\1', md_content)
        md_content = re.sub(r'\*([^\*]+)\*', r'\1', md_content)
        md_content = re.sub(r'__([^_]+)__', r'\1', md_content)
        md_content = re.sub(r'_([^_]+)_', r'\1', md_content)
        # 去除水平线
        md_content = re.sub(r'^[-*_]{3,}$', '', md_content, flags=re.MULTILINE)
        # 去除列表标记
        md_content = re.sub(r'^[\s]*[-*+]\s+', '', md_content, flags=re.MULTILINE)
        md_content = re.sub(r'^[\s]*\d+\.\s+', '', md_content, flags=re.MULTILINE)

        # 按双换行（或多个换行）分割为段落
        paragraphs = [
            p.strip() for p in re.split(r'\n\n+', md_content)
            if p.strip()
        ]

        # 合并过短的段落
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
