# 解析器工厂

from pathlib import Path
from typing import List
from .base import BaseParser
from .pdf_parser import PDFParser
from .docx_parser import DocxParser
from .markdown_parser import MarkdownParser
from .txt_parser import TXTParser

class ParserFactory:
    """
    解析器工厂：根据文件扩展名返回对应解析器

    使用单例模式复用解析器实例
    """

    _parsers = {
        '.pdf': PDFParser(),
        '.docx': DocxParser(),
        '.md': MarkdownParser(),
        '.txt': TXTParser(),
    }

    @classmethod
    def get_parser(cls, file_ext: str) -> BaseParser:
        """
        获取对应文件格式的解析器

        Args:
            file_ext: 文件扩展名（如 '.pdf'）

        Returns:
            对应的解析器实例

        Raises:
            ValueError: 不支持的文件格式
        """
        file_ext = file_ext.lower()
        parser = cls._parsers.get(file_ext)
        if parser is None:
            supported = ', '.join(cls._parsers.keys())
            raise ValueError(f"不支持的文件格式: {file_ext}，支持的格式: {supported}")
        return parser

    @classmethod
    def supported_extensions(cls) -> List[str]:
        """返回所有支持的文件扩展名"""
        return list(cls._parsers.keys())

    @classmethod
    def is_supported(cls, file_ext: str) -> bool:
        """
        检查文件格式是否支持

        Args:
            file_ext: 文件扩展名

        Returns:
            True表示支持
        """
        return file_ext.lower() in cls._parsers
