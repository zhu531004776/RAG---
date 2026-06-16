# 文档解析器基类

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
import re

class BaseParser(ABC):
    """
    文档解析器抽象基类

    所有解析器必须实现parse方法，将文件内容解析为段落列表
    """

    @abstractmethod
    def parse(self, file_path: Path) -> List[str]:
        """
        解析文档并返回段落列表

        Args:
            file_path: 文件路径对象

        Returns:
            paragraphs: 段落文本列表，每个元素为一个段落
        """
        pass

    def _clean_text(self, text: str) -> str:
        """
        通用文本清理：去除多余空白字符

        Args:
            text: 原始文本

        Returns:
            清理后的文本
        """
        # 合并多个空白字符为单个空格
        text = re.sub(r'\s+', ' ', text)
        # 去除首尾空白
        return text.strip()

    def _split_paragraphs(self, text: str, min_length: int = 10) -> List[str]:
        """
        按段落分割文本

        Args:
            text: 待分割文本
            min_length: 最小段落长度，短于此长度的段落会被合并

        Returns:
            段落列表
        """
        # 按双换行或单换行分割
        paragraphs = re.split(r'\n\n+|\n+', text)
        result = []
        current = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current) + len(para) < min_length * 5:
                # 合并短段落
                current += " " + para if current else para
            else:
                if current:
                    result.append(current)
                current = para

        if current:
            result.append(current)

        return [p for p in result if p]
