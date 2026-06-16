# 对话数据模型

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import datetime

@dataclass
class Source:
    """
    回答来源信息

    属性:
        doc_name: 文档名称
        chunk_index: 切片序号
    """
    doc_name: str
    chunk_index: int

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "doc_name": self.doc_name,
            "chunk_index": self.chunk_index
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Source":
        """从字典恢复"""
        return cls(
            doc_name=data["doc_name"],
            chunk_index=data["chunk_index"]
        )


@dataclass
class Message:
    """
    对话消息

    属性:
        role: 角色，"user" 或 "assistant"
        content: 消息内容
        sources: 参考来源列表（仅assistant消息有）
    """
    role: str
    content: str
    sources: Optional[List[Source]] = None
    no_relevant: bool = False

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "role": self.role,
            "content": self.content,
            "sources": [s.to_dict() for s in self.sources] if self.sources else None,
            "no_relevant": self.no_relevant
        }


@dataclass
class Answer:
    """
    RAG管道返回的回答结果

    属性:
        content: 回答内容
        sources: 参考来源列表
        no_relevant: 是否无相关内容
    """
    content: str
    sources: List[Source]
    no_relevant: bool = False


@dataclass
class Conversation:
    """
    对话会话

    属性:
        session_id: 会话ID
        messages: 消息列表
        created_at: 创建时间
    """
    session_id: str
    messages: List[Message] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def add_user_message(self, content: str):
        """添加用户消息"""
        self.messages.append(Message(role="user", content=content))

    def add_assistant_message(self, content: str, sources: List[Source] = None, no_relevant: bool = False):
        """添加助手消息"""
        self.messages.append(Message(
            role="assistant",
            content=content,
            sources=sources,
            no_relevant=no_relevant
        ))

    def get_history(self) -> List[Tuple[str, str]]:
        """
        获取对话历史，用于RAG管道

        Returns:
            [(question, answer), ...] 格式的历史
        """
        history = []
        for msg in self.messages:
            if msg.role == "user":
                history.append((msg.content, ""))
            elif msg.role == "assistant" and history:
                # 找到最后一个未配对的user消息
                for i in range(len(history) - 1, -1, -1):
                    if not history[i][1]:  # answer为空
                        history[i] = (history[i][0], msg.content)
                        break
        return history
