# RAG问答管道

from dataclasses import dataclass
import re
from typing import List, Optional, Tuple

from vectorstore import VectorStore, SearchResult
from llm import BaseLLM
from config import SYSTEM_PROMPT, NO_RELEVANT_CONTENT_MSG, TOP_K, NO_CONTENT_THRESHOLD

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


class RAGPipeline:
    """
    RAG问答管道

    职责：
    1. 接收用户提问
    2. 执行向量检索召回Top-K相关片段
    3. 拼装Prompt
    4. 调用大模型生成回答
    5. 返回格式化回答（含来源信息）
    """

    def __init__(
        self,
        vector_store: VectorStore,
        llm: BaseLLM,
        top_k: int = TOP_K,
        no_content_threshold: float = NO_CONTENT_THRESHOLD
    ):
        """
        初始化RAG管道

        Args:
            vector_store: 向量存储实例
            llm: 大模型接口实例
            top_k: 召回片段数量
            no_content_threshold: 无相关内容判定阈值（余弦距离）
        """
        self.vector_store = vector_store
        self.llm = llm
        self.top_k = top_k
        self.no_content_threshold = no_content_threshold

    def ask(
        self,
        question: str,
        conversation_history: Optional[List[Tuple[str, str]]] = None
    ) -> Answer:
        """
        执行问答

        实现流程：
        1. 向量检索获取Top-K相关片段
        2. 检查是否有相关内容（距离阈值）
        3. 如无相关内容，返回固定提示
        4. 如有相关内容，拼装Prompt并调用大模型
        5. 返回回答结果

        Args:
            question: 用户问题
            conversation_history: 历史对话 [(question, answer), ...]

        Returns:
            Answer对象
        """
        # 1. 向量检索
        search_results = self.vector_store.search(question, self.top_k)
        relevant_results = self._filter_relevant_results(search_results)

        # 2. 检查相关性
        if not relevant_results:
            return Answer(
                content=NO_RELEVANT_CONTENT_MSG,
                sources=[],
                no_relevant=True
            )

        # 3. 构建上下文
        context = self._build_context(relevant_results)

        # 4. 构建历史摘要
        history_summary = self._build_history_summary(conversation_history)

        # 5. 拼装Prompt
        prompt = self._build_prompt(question, context, history_summary)

        # 6. 调用大模型生成
        response = self.llm.generate(prompt, SYSTEM_PROMPT)

        # 7. 提取来源信息
        sources = self._build_sources(relevant_results)

        return Answer(
            content=self._strip_inline_sources(response),
            sources=sources,
            no_relevant=False
        )

    def _filter_relevant_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        过滤出与问题足够相关的检索结果。

        余弦距离越小越相关，这里只保留距离不超过阈值的结果。
        若全部结果都超过阈值，则视为无相关内容。

        Args:
            results: 检索结果列表

        Returns:
            相关结果列表
        """
        return [
            result for result in results
            if result.distance <= self.no_content_threshold
        ]

    def _build_context(self, results: List[SearchResult]) -> str:
        """
        构建上下文文本

        将检索结果格式化为统一的上下文段落

        Args:
            results: 检索结果列表

        Returns:
            格式化上下文字符串
        """
        context_parts = []
        for i, result in enumerate(results, 1):
            part = f"【片段{i}】\n"
            part += f"文档：{result.doc_name}\n"
            part += f"段落序号：{result.chunk_index}\n"
            part += f"内容：{result.content}\n"
            context_parts.append(part)

        return "\n---\n".join(context_parts)

    def _build_sources(self, results: List[SearchResult]) -> List[Source]:
        """按检索顺序生成去重后的来源列表。"""
        seen = set()
        sources = []

        for result in results:
            source_key = (result.doc_name, result.chunk_index)
            if source_key in seen:
                continue

            seen.add(source_key)
            sources.append(
                Source(
                    doc_name=result.doc_name,
                    chunk_index=result.chunk_index
                )
            )

        return sources

    def _strip_inline_sources(self, response: str) -> str:
        """
        移除模型在正文中自行追加的“参考来源”段落。

        来源由前端统一渲染，避免正文和页脚重复展示两份。
        """
        cleaned = re.sub(r"\n*参考来源[:：][\s\S]*$", "", response).strip()
        return cleaned or response.strip()

    def _build_history_summary(
        self,
        history: Optional[List[Tuple[str, str]]]
    ) -> str:
        """
        构建历史对话摘要

        将对话历史简化为简短摘要，供大模型理解上下文

        Args:
            history: 对话历史列表

        Returns:
            历史摘要字符串（无历史时返回空）
        """
        if not history:
            return "（暂无历史对话）"

        summary_parts = []
        for i, (q, a) in enumerate(history, 1):
            # 只保留问题和回答的首句，避免过长
            q_short = q.split('\n')[0][:100]
            a_short = a.split('\n')[0][:100] if len(a) > 50 else a
            summary_parts.append(f"第{i}轮：问：{q_short}，答：{a_short}")

        return "\n".join(summary_parts)

    def _build_prompt(
        self,
        question: str,
        context: str,
        history_summary: str
    ) -> str:
        """
        构建Prompt

        按照模板格式拼装各部分内容

        Args:
            question: 用户问题
            context: 检索到的上下文
            history_summary: 历史对话摘要

        Returns:
            完整的用户Prompt
        """
        return f"""【上下文信息】
{context}

【历史对话摘要】
{history_summary}

【当前问题】
{question}

【回答要求】
1. 只能基于上述上下文信息回答
2. 当上下文没有相关信息时，回复：「{NO_RELEVANT_CONTENT_MSG}」
3. 不要在回答正文或末尾重复输出“参考来源”字样，来源由界面统一展示
"""
