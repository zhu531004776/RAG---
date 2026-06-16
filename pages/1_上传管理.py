# 文档上传管理页

import streamlit as st
from datetime import datetime, timedelta
from html import escape
import traceback
from pathlib import Path

from config import UPLOAD_DIR, ALLOWED_EXTENSIONS
from models.document import Document, DocumentStore, ProcessStatus
from models.supabase_document_store import create_document_store

# 页面配置必须是当前页面第一个 Streamlit 调用
st.set_page_config(layout="wide", page_title="文档上传管理")

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

PROCESSING_TIMEOUT_MINUTES = 10


def normalize_process_status(status) -> str:
    """统一状态值，兼容字符串和热重载前后的枚举实例。"""
    return getattr(status, "value", status)


def format_processing_error(error: Exception) -> str:
    """将底层异常转换为更易理解的失败原因。"""
    raw_message = str(error).strip()
    if not raw_message:
        return "文档处理失败，未返回具体错误信息。"

    lowered = raw_message.lower()

    if "client has been closed" in lowered:
        return "向量库连接已关闭，通常是页面刷新、应用重启或旧连接失效导致，请重新上传该文档。"

    if "permission denied" in lowered or "denied" in lowered:
        return "文件访问被拒绝，请检查文件是否被其他程序占用。"

    if "no such file" in lowered or "cannot find the file" in lowered:
        return "上传后的源文件不存在，可能是保存失败或文件被移动。"

    if "EOF marker not found" in raw_message or "Malformed PDF" in raw_message:
        return "PDF 文件损坏、加密，或当前解析器无法读取其内容。"

    if "文档解析后无有效内容" in raw_message:
        return "文档解析成功，但没有提取到可用文本内容。"

    if "文档切片后无有效片段" in raw_message:
        return "文档内容过少或格式异常，未能生成有效切片。"

    return f"文档处理异常：{raw_message}"


def mark_stale_processing_docs(doc_store: DocumentStore) -> int:
    """
    将长时间停留在处理中状态的文档自动标记为失败。

    当前上传处理已是同步流程，若文档长期停留在处理中，通常意味着：
    1. 旧版本后台线程没有正确回写状态
    2. 处理过程中页面刷新或应用重启
    3. 处理中断后只保存了初始 processing 状态
    """
    stale_count = 0
    now = datetime.now()

    for doc in doc_store.get_all():
        if normalize_process_status(doc.status) != ProcessStatus.PROCESSING.value:
            continue

        try:
            upload_dt = datetime.strptime(doc.upload_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            upload_dt = None

        if upload_dt and now - upload_dt > timedelta(minutes=PROCESSING_TIMEOUT_MINUTES):
            doc.status = ProcessStatus.FAILED
            if not doc.error_msg:
                doc.error_msg = (
                    f"处理超时：该文档已连续处于“处理中”超过 {PROCESSING_TIMEOUT_MINUTES} 分钟。"
                    "通常是因为旧版本后台处理未成功回写状态，或处理中途页面刷新、应用重启导致。"
                    "请重新上传该文档。"
                )
            doc_store.update(doc)
            stale_count += 1

    return stale_count


def get_processing_duration_text(doc: Document) -> str:
    """返回处理中持续时长的展示文本。"""
    try:
        upload_dt = datetime.strptime(doc.upload_time, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return "处理中"

    delta = datetime.now() - upload_dt
    total_seconds = max(int(delta.total_seconds()), 0)

    if total_seconds < 60:
        return f"处理中 {total_seconds} 秒"

    minutes = total_seconds // 60
    if minutes < 60:
        return f"处理中 {minutes} 分钟"

    hours = minutes // 60
    remain_minutes = minutes % 60
    return f"处理中 {hours} 小时 {remain_minutes} 分钟"


def ensure_vector_store():
    """确保向量库已初始化。"""
    if st.session_state.vector_store is None:
        from vectorstore import VectorStore
        from config import EMBEDDING_MODEL, EMBEDDING_DEVICE, VECTOR_DB_DIR

        st.session_state.vector_store = VectorStore(
            embedding_model=EMBEDDING_MODEL,
            persist_directory=VECTOR_DB_DIR,
            device=EMBEDDING_DEVICE
        )

    return st.session_state.vector_store


def process_document_content(doc: Document) -> None:
    """处理指定文档并更新状态。"""
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"未找到源文件：{file_path}")

    from parser import ParserFactory
    parser = ParserFactory.get_parser(doc.file_type)
    paragraphs = parser.parse(file_path)
    if not paragraphs:
        raise ValueError("文档解析后无有效内容")

    from chunker import TextChunker
    from config import CHUNK_MIN_LENGTH, CHUNK_MAX_LENGTH, CHUNK_OVERLAP
    chunker = TextChunker(
        min_length=CHUNK_MIN_LENGTH,
        max_length=CHUNK_MAX_LENGTH,
        overlap=CHUNK_OVERLAP
    )
    chunks = chunker.chunk(paragraphs, doc.file_name)
    if not chunks:
        raise ValueError("文档切片后无有效片段")

    vector_store = ensure_vector_store()
    vector_store.delete_by_doc_name(doc.file_name)
    vector_store.add_chunks(chunks)

    doc.chunk_count = len(chunks)
    doc.status = ProcessStatus.COMPLETED
    doc.error_msg = None
    st.session_state.doc_store.update(doc)


def retry_failed_document(doc_id: str) -> None:
    """重新处理失败文档，并刷新当前记录的上传时间与状态。"""
    doc = st.session_state.doc_store.get_by_id(doc_id)
    doc.upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    doc.status = ProcessStatus.PROCESSING
    doc.chunk_count = 0
    doc.error_msg = None
    st.session_state.doc_store.update(doc)

    try:
        process_document_content(doc)
        st.session_state.upload_feedback_messages.append(
            ("success", f"✅ 文件 {doc.file_name} 重新上传并处理完成")
        )
    except Exception as e:
        doc.status = ProcessStatus.FAILED
        doc.error_msg = format_processing_error(e)
        st.session_state.doc_store.update(doc)
        st.session_state.upload_feedback_messages.append(
            ("error", f"重新上传失败：{doc.error_msg}")
        )

# 页面头部
st.markdown("""
<div style="padding: 0.5rem 0 1.5rem 0;">
    <h1 style="font-size: 1.75rem; font-weight: 700; color: #1F2937; margin-bottom: 0.25rem;">
        📁 文档上传管理
    </h1>
    <p style="color: #6B7280; font-size: 0.9rem;">
        上传和管理知识库文档，支持 PDF、Word、Markdown、TXT 格式
    </p>
</div>
""", unsafe_allow_html=True)

# 初始化会话状态
if 'doc_store' not in st.session_state:
    st.session_state.doc_store = create_document_store()

if 'vector_store' not in st.session_state:
    st.session_state.vector_store = None
if 'upload_uploader_key' not in st.session_state:
    st.session_state.upload_uploader_key = 0
if 'upload_feedback_messages' not in st.session_state:
    st.session_state.upload_feedback_messages = []

stale_count = mark_stale_processing_docs(st.session_state.doc_store)
if stale_count:
    st.warning(f"检测到 {stale_count} 个长时间处于“处理中”的文档，已自动标记为失败，并写入失败原因。")

for level, message in st.session_state.upload_feedback_messages:
    getattr(st, level)(message)
st.session_state.upload_feedback_messages = []

# 上传区域
st.markdown("#### 📤 上传文档")
uploaded_files = st.file_uploader(
    "拖拽文件到此处或点击上传",
    type=["pdf", "docx", "md", "txt"],
    accept_multiple_files=True,
    label_visibility="collapsed",
    key=f"upload_files_{st.session_state.upload_uploader_key}"
)

# 处理上传文件
if uploaded_files:
    feedback_messages = []
    for uploaded_file in uploaded_files:
        doc = None
        file_ext = Path(uploaded_file.name).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            feedback_messages.append((
                "error",
                f"不支持的文件格式: {file_ext}，仅支持: {', '.join(ALLOWED_EXTENSIONS)}"
            ))
            continue

        existing_names = [d.file_name for d in st.session_state.doc_store.get_all()]
        if uploaded_file.name in existing_names:
            feedback_messages.append(("warning", f"文件 {uploaded_file.name} 已存在，跳过"))
            continue

        try:
            # 保存文件
            file_path = UPLOAD_DIR / uploaded_file.name
            
            # 检查目录是否可写
            if not UPLOAD_DIR.exists():
                raise PermissionError(f"上传目录不存在: {UPLOAD_DIR}")
            
            try:
                test_file = UPLOAD_DIR / ".temp_write_test"
                test_file.write_text("test")
                test_file.unlink()
            except PermissionError:
                raise PermissionError(f"上传目录无写入权限: {UPLOAD_DIR}")
            
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # 创建文档记录
            doc = Document.create(
                file_name=uploaded_file.name,
                file_path=str(file_path),
                file_type=file_ext
            )
            st.session_state.doc_store.add(doc)

            with st.spinner(f"正在处理文档：{uploaded_file.name}"):
                process_document_content(doc)

            feedback_messages.append(("success", f"✅ 文件 {uploaded_file.name} 上传成功，处理完成"))

        except Exception as e:
            friendly_error = format_processing_error(e)
            if doc is not None:
                try:
                    doc.status = ProcessStatus.FAILED
                    doc.error_msg = friendly_error
                    st.session_state.doc_store.update(doc)
                except Exception:
                    pass
            feedback_messages.append(("error", f"文件上传失败：{friendly_error}"))
            traceback.print_exc()

    st.session_state.upload_uploader_key += 1
    for level, message in feedback_messages:
        getattr(st, level)(message)

# 文档列表
st.markdown("---")
st.markdown("### 📋 文档列表")
docs = st.session_state.doc_store.get_all()

if docs:
    # 表头
    col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 1, 1, 3, 1.5])
    col1.markdown("**文档名称**")
    col2.markdown("**上传时间**")
    col3.markdown("**切片数**")
    col4.markdown("**状态**")
    col5.markdown("**失败原因**")
    col6.markdown("**操作**")
    st.divider()

    for doc in reversed(docs):
        col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 1, 1, 3, 1.5])
        col1.text(doc.file_name)
        col2.text(doc.upload_time)
        col3.text(str(doc.chunk_count) if doc.chunk_count else "-")

        normalized_status = normalize_process_status(doc.status)

        status_map = {
            ProcessStatus.COMPLETED.value: ("✅", "完成"),
            ProcessStatus.PROCESSING.value: ("⏳", "处理中"),
            ProcessStatus.FAILED.value: ("❌", "失败")
        }
        icon, label = status_map.get(normalized_status, ("❓", "未知"))
        col4.markdown(f"{icon} {label}")

        if normalized_status == ProcessStatus.FAILED.value and doc.error_msg:
            safe_reason = escape(doc.error_msg, quote=True)
            col5.markdown(
                f"""
                <div class="failure-reason-cell" title="{safe_reason}">
                    {safe_reason}
                </div>
                """,
                unsafe_allow_html=True,
            )
            col6.button(
                "重新上传",
                key=f"retry_{doc.doc_id}",
                use_container_width=False,
                type="primary",
                on_click=retry_failed_document,
                args=(doc.doc_id,),
            )
        elif normalized_status == ProcessStatus.PROCESSING.value:
            col5.write("-")
            col6.write("-")
        else:
            col5.write("-")
            col6.write("-")

    if st.button("🔄 刷新列表"):
        if hasattr(st.session_state.doc_store, "refresh_from_remote"):
            st.session_state.doc_store.refresh_from_remote()
        st.rerun()
else:
    st.info("暂无上传文档，请上传文档开始使用")

# 统计
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    st.metric("文档总数", len(docs))
with col2:
    completed = sum(
        1 for d in docs
        if normalize_process_status(d.status) == ProcessStatus.COMPLETED.value
    )
    st.metric("已处理", completed)

# 导航
st.markdown("---")
if st.button("💬 进入智能问答", use_container_width=True):
    st.switch_page("pages/2_智能问答.py")
