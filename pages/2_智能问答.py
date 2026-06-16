# 智能问答页

import streamlit as st
import traceback

from config import LLM_API_CONFIG
from llm import ArkResponsesLLM, OpenAICompatibleLLM
from models.document import ProcessStatus
from models.supabase_document_store import create_document_store


def normalize_process_status(status) -> str:
    """统一状态值，兼容字符串和热重载前后的枚举实例。"""
    return getattr(status, "value", status)


# 页面配置必须是当前页面第一个 Streamlit 调用
st.set_page_config(layout="wide", page_title="智能问答")

# 加载自定义CSS
def load_custom_css():
    try:
        with open(".streamlit/custom.css", "rb") as f:
            css_bytes = f.read()

        try:
            css_text = css_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            css_text = css_bytes.decode("gb18030")

        st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

load_custom_css()


def strip_inline_sources(text: str) -> str:
    """兼容旧消息，去掉正文中模型自行生成的来源行。"""
    marker = "参考来源："
    if marker not in text:
        return text

    prefix, _, _ = text.partition(marker)
    return prefix.rstrip()


@st.cache_resource
def get_persisted_vector_chunk_count() -> int:
    """轻量检查持久化知识库中是否存在切片，避免页面首屏加载Embedding模型。"""
    from chromadb import PersistentClient
    from config import VECTOR_DB_DIR

    client = PersistentClient(path=str(VECTOR_DB_DIR))
    try:
        collection = client.get_collection(name="documents")
    except Exception:
        return 0

    return collection.count()


@st.cache_resource
def get_cached_vector_store():
    """缓存向量库实例，避免重复加载Embedding模型。"""
    from config import EMBEDDING_MODEL, EMBEDDING_DEVICE, VECTOR_DB_DIR
    from vectorstore import VectorStore

    return VectorStore(
        embedding_model=EMBEDDING_MODEL,
        persist_directory=VECTOR_DB_DIR,
        device=EMBEDDING_DEVICE
    )


def format_sources(sources):
    """格式化来源展示：去重、改为从第1段开始编号。"""
    seen = set()
    formatted_items = []

    for source in sources:
        source_key = (source["doc_name"], source["chunk_index"])
        if source_key in seen:
            continue

        seen.add(source_key)
        display_chunk_index = source["chunk_index"] + 1
        formatted_items.append(
            f'{source["doc_name"]} - 第{display_chunk_index}段'
        )

    return "，".join(formatted_items)


def get_llm_config_signature() -> tuple:
    """生成当前 LLM 配置签名，用于检测热更新后的客户端漂移。"""
    return (
        LLM_API_CONFIG.get("api_type"),
        LLM_API_CONFIG.get("base_url"),
        LLM_API_CONFIG.get("model"),
        LLM_API_CONFIG.get("timeout"),
        LLM_API_CONFIG.get("temperature"),
    )


def clear_chat_history() -> None:
    """清空对话历史，不额外触发强制重跑。"""
    st.session_state.messages = []
    st.session_state.conversation_history = []

# 从持久化向量库恢复当前会话的检索能力
def ensure_vector_store():
    if 'vector_store' not in st.session_state:
        st.session_state.vector_store = None

    if st.session_state.vector_store is None:
        st.session_state.vector_store = get_cached_vector_store()

    return st.session_state.vector_store

# 页面头部
st.markdown("""
<div style="padding: 0.5rem 0 1rem 0;">
    <h1 style="font-size: 1.75rem; font-weight: 700; color: #1F2937; margin-bottom: 0.25rem;">
        💬 智能问答
    </h1>
    <p style="color: #6B7280; font-size: 0.9rem;">
        基于知识库内容进行智能问答，每条回答均附带参考来源
    </p>
</div>
""", unsafe_allow_html=True)

# 初始化会话状态
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

if 'rag_pipeline' not in st.session_state:
    st.session_state.rag_pipeline = None

if 'rag_pipeline_signature' not in st.session_state:
    st.session_state.rag_pipeline_signature = None

# 先读取已处理文档，再决定是否允许进入问答
if 'doc_store' not in st.session_state:
    st.session_state.doc_store = create_document_store()

completed_docs = [
    doc for doc in st.session_state.doc_store.get_all()
    if normalize_process_status(doc.status) == ProcessStatus.COMPLETED.value
]

if not completed_docs:
    st.warning("⚠️ 请先在「文档上传管理」页上传并处理文档后，再进行问答")
    if st.button("前往文档上传管理"):
        st.switch_page("pages/1_上传管理.py")
    st.stop()

try:
    vector_chunk_count = get_persisted_vector_chunk_count()
except Exception as e:
    st.error(f"恢复知识库索引失败: {e}")
    st.stop()

if vector_chunk_count <= 0:
    st.warning("⚠️ 已检测到处理完成的文档，但知识库索引为空，请前往「文档上传管理」重新处理文档后再进行问答")
    if st.button("前往文档上传管理"):
        st.switch_page("pages/1_上传管理.py")
    st.stop()

# 知识库状态
chunk_count = sum(doc.chunk_count for doc in completed_docs)
doc_names = [doc.file_name for doc in completed_docs]
st.markdown(f"""
<div style="background: white; border-radius: 12px; padding: 0.75rem 1rem; margin-bottom: 1rem; border: 1px solid #E5E7EB;">
    📚 知识库状态：{len(doc_names)} 个文档，{chunk_count} 个切片
</div>
""", unsafe_allow_html=True)

# 聊天消息展示
if not st.session_state.messages:
    st.info("👋 您好！请在下方输入问题，我会基于知识库内容为您解答。")
else:
    for message in st.session_state.messages:
        if message['role'] == 'user':
            with st.chat_message("user"):
                st.write(message['content'])
        else:
            with st.chat_message("assistant"):
                st.write(strip_inline_sources(message['content']))
                if message.get('sources'):
                    st.caption(f"📎 参考来源：{format_sources(message['sources'])}")
                if message.get('no_relevant'):
                    st.warning("⚠️ 当前知识库中无相关内容")

# 问答输入
st.markdown("---")
question = st.chat_input("请输入您的问题...")

if question:
    st.session_state.messages.append({'role': 'user', 'content': question})
    with st.chat_message("user"):
        st.write(question)

    with st.spinner("🤔 思考中..."):
        try:
            vector_store = ensure_vector_store()

            if (
                st.session_state.rag_pipeline is None
                or st.session_state.rag_pipeline.vector_store is not vector_store
                or st.session_state.rag_pipeline_signature != get_llm_config_signature()
            ):
                from rag import RAGPipeline

                if LLM_API_CONFIG["api_type"] == "ark_responses":
                    llm = ArkResponsesLLM(
                        base_url=LLM_API_CONFIG["base_url"],
                        api_key=LLM_API_CONFIG["api_key"],
                        model=LLM_API_CONFIG["model"],
                        timeout=LLM_API_CONFIG.get("timeout", 60),
                        temperature=LLM_API_CONFIG.get("temperature", 0.3),
                    )
                else:
                    llm = OpenAICompatibleLLM(
                        base_url=LLM_API_CONFIG["base_url"],
                        api_key=LLM_API_CONFIG["api_key"],
                        model=LLM_API_CONFIG["model"],
                        timeout=LLM_API_CONFIG.get("timeout", 60),
                        temperature=LLM_API_CONFIG.get("temperature", 0.3)
                    )
                st.session_state.rag_pipeline = RAGPipeline(
                    vector_store=vector_store,
                    llm=llm
                )
                st.session_state.rag_pipeline_signature = get_llm_config_signature()
            answer = st.session_state.rag_pipeline.ask(
                question,
                st.session_state.conversation_history
            )

            st.session_state.messages.append({
                'role': 'assistant',
                'content': answer.content,
                'sources': [{'doc_name': s.doc_name, 'chunk_index': s.chunk_index} for s in answer.sources],
                'no_relevant': answer.no_relevant
            })

            st.session_state.conversation_history.append((question, answer.content))
            with st.chat_message("assistant"):
                st.write(strip_inline_sources(answer.content))
                if answer.sources:
                    formatted_sources = format_sources(
                        [{'doc_name': s.doc_name, 'chunk_index': s.chunk_index} for s in answer.sources]
                    )
                    st.caption(f"📎 参考来源：{formatted_sources}")
                if answer.no_relevant:
                    st.warning("⚠️ 当前知识库中无相关内容")

        except Exception as e:
            st.error(f"生成回答失败: {e}")
            traceback.print_exc()

# 侧边栏功能
st.sidebar.markdown("### 🎛️ 功能")
st.sidebar.button(
    "🗑️ 清空对话历史",
    use_container_width=True,
    on_click=clear_chat_history,
)
