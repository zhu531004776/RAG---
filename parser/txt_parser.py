# 纯文本(.txt)文档解析器

from pathlib import Path
from typing import List
import re
from .base import BaseParser

class TXTParser(BaseParser):
    """
    纯文本(.txt)文档解析器

    简单读取文本文件，按换行符分割为段落
    """

    def parse(self, file_path: Path) -> List[str]:
        """
        解析纯文本文件

        实现步骤：
        1. 以UTF-8编码读取文件
        2. 按换行符分割
        3. 合并过短段落

        Args:
            file_path: TXT文件路径

        Returns:
            paragraphs: 段落文本列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except Exception as e:
                raise RuntimeError(f"TXT文件读取失败: {file_path}, 错误: {e}")
        except Exception as e:
            raise RuntimeError(f"TXT文件读取失败: {file_path}, 错误: {e}")

        # 按双换行（或单换行）分割为段落
        paragraphs = [
            p.strip() for p in re.split(r'\n\n+|\n+', content)
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
