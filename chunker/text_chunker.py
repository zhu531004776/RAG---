# 文本切片器

from dataclasses import dataclass
from typing import List
import re

@dataclass
class TextChunk:
    """
    文本切片数据结构

    属性:
        content: 切片原文内容
        doc_name: 所属文档名称
        chunk_index: 切片在文档内的序号
        original_para_idx: 对应原文档的段落序号
    """
    content: str
    doc_name: str
    chunk_index: int
    original_para_idx: int

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "content": self.content,
            "doc_name": self.doc_name,
            "chunk_index": self.chunk_index,
            "original_para_idx": self.original_para_idx
        }


class TextChunker:
    """
    文本切片器：基于段落边界+字符长度控制的混合切片

    切片策略：
    1. 优先按段落边界切分，保障语义完整
    2. 单段落超过最大长度时，按句子边界截断
    3. 相邻切片保持一定重叠，保持语义连贯
    """

    def __init__(
        self,
        min_length: int = 200,
        max_length: int = 300,
        overlap: int = 50
    ):
        """
        初始化切片器

        Args:
            min_length: 单切片最小字符数
            max_length: 单切片最大字符数
            overlap: 相邻切片重叠字符数
        """
        self.min_length = min_length
        self.max_length = max_length
        self.overlap = overlap

    def chunk(self, paragraphs: List[str], doc_name: str) -> List[TextChunk]:
        """
        执行文本切片

        实现逻辑：
        1. 遍历段落，累积文本直到达到最大长度
        2. 如果累积文本长度达到最小长度，保存为一个切片
        3. 保持相邻切片间overlap长度的重叠
        4. 单段落过长时按句子边界切分

        Args:
            paragraphs: 段落文本列表
            doc_name: 文档名称

        Returns:
            chunks: TextChunk列表
        """
        chunks = []
        chunk_index = 0
        current_text = ""
        current_para_idx = 0

        for para_idx, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                continue

            # 如果单个段落就超过最大长度，按句子截断
            if len(para) > self.max_length:
                # 先保存当前累积的文本
                if len(current_text) >= self.min_length:
                    chunks.append(TextChunk(
                        content=current_text,
                        doc_name=doc_name,
                        chunk_index=chunk_index,
                        original_para_idx=current_para_idx
                    ))
                    chunk_index += 1
                    # 保留overlap作为下一个切片的开头
                    current_text = current_text[-self.overlap:] if len(current_text) > self.overlap else ""
                    current_para_idx = para_idx

                # 按句子截断超长段落
                sentences = self._split_into_sentences(para)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue

                    if len(current_text) + len(sentence) <= self.max_length:
                        current_text += sentence
                    else:
                        # 保存当前切片
                        if len(current_text) >= self.min_length:
                            chunks.append(TextChunk(
                                content=current_text,
                                doc_name=doc_name,
                                chunk_index=chunk_index,
                                original_para_idx=current_para_idx
                            ))
                            chunk_index += 1
                            # 保留overlap
                            current_text = current_text[-self.overlap:] if len(current_text) > self.overlap else ""

                        current_text += sentence
                        current_para_idx = para_idx
            else:
                # 普通段落，尝试累积
                if len(current_text) + len(para) <= self.max_length:
                    current_text += " " + para if current_text else para
                else:
                    # 保存当前切片
                    if len(current_text) >= self.min_length:
                        chunks.append(TextChunk(
                            content=current_text,
                            doc_name=doc_name,
                            chunk_index=chunk_index,
                            original_para_idx=current_para_idx
                        ))
                        chunk_index += 1
                        # 保留overlap
                        current_text = current_text[-self.overlap:] if len(current_text) > self.overlap else ""

                    current_text += " " + para if current_text else para
                    current_para_idx = para_idx

        # 处理最后剩余的文本
        if len(current_text) >= self.min_length:
            chunks.append(TextChunk(
                content=current_text,
                doc_name=doc_name,
                chunk_index=chunk_index,
                original_para_idx=current_para_idx
            ))

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        按句子边界分割文本

        句子结束符：。！？.!?（支持中英文）

        Args:
            text: 待分割文本

        Returns:
            句子列表
        """
        # 按句子结束符分割，保留分割符
        pattern = r'([。！？.!?]+)'
        parts = re.split(pattern, text)

        # 合并句子和其后的结束符
        sentences = []
        for i in range(0, len(parts) - 1, 2):
            sentence = parts[i].strip()
            separator = parts[i + 1] if i + 1 < len(parts) else ""
            if sentence:
                sentences.append(sentence + separator)

        # 处理最后一部分（如果没有结束符）
        if len(parts) % 2 == 1 and parts[-1].strip():
            sentences.append(parts[-1].strip())

        return [s for s in sentences if s.strip()]
