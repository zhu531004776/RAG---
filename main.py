# 轻量级RAG知识库 - Streamlit入口

import streamlit as st

# 加载自定义CSS
def load_custom_css():
    """加载自定义CSS样式"""
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

# 页面配置
st.set_page_config(
    page_title="轻量级RAG知识库",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 加载CSS
load_custom_css()

# 初始化向量存储（全局单例）
@st.cache_resource
def init_vector_store():
    """初始化向量存储"""
    from vectorstore import VectorStore
    from config import EMBEDDING_MODEL, EMBEDDING_DEVICE, VECTOR_DB_DIR

    return VectorStore(
        embedding_model=EMBEDDING_MODEL,
        persist_directory=VECTOR_DB_DIR,
        device=EMBEDDING_DEVICE
    )


def render_header():
    """渲染页面头部"""
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0 2rem 0;">
        <h1 class="main-title">📚 轻量级RAG知识库</h1>
        <p style="color: #6B7280; font-size: 1.1rem; margin-top: 0.5rem;">
            智能文档问答 · 向量检索 · 来源追溯
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_feature_cards():
    """渲染功能特性卡片"""
    st.markdown("### ✨ 核心特性")

    col1, col2, col3, col4 = st.columns(4)

    features = [
        {"icon": "📄", "title": "多格式支持", "desc": "PDF、Word、Markdown、TXT"},
        {"icon": "🔍", "title": "智能检索", "desc": "向量语义精准匹配"},
        {"icon": "📎", "title": "来源追溯", "desc": "答案附带参考来源"},
        {"icon": "💬", "title": "多轮对话", "desc": "上下文连贯理解"},
    ]

    for col, feature in zip([col1, col2, col3, col4], features):
        with col:
            st.markdown(f"""
            <div class="feature-card" style="text-align: center; padding: 1.25rem;">
                <div style="font-size: 2rem; margin-bottom: 0.75rem;">{feature['icon']}</div>
                <div style="font-weight: 600; color: #1F2937; margin-bottom: 0.25rem;">{feature['title']}</div>
                <div style="color: #6B7280; font-size: 0.85rem;">{feature['desc']}</div>
            </div>
            """, unsafe_allow_html=True)


def render_navigation():
    """渲染导航卡片"""
    st.markdown("---")
    st.markdown("### 🚀 开始使用")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("""
        <div class="nav-card" style="border: 2px solid transparent;">
            <div class="nav-card-icon">📁</div>
            <div class="nav-card-title">文档上传管理</div>
            <div class="nav-card-desc">上传和管理知识库文档，支持批量处理</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("进入文档上传管理", type="primary", use_container_width=True, key="nav_upload"):
            st.switch_page("pages/1_上传管理.py")

    with col2:
        st.markdown("""
        <div class="nav-card" style="border: 2px solid transparent;">
            <div class="nav-card-icon">💬</div>
            <div class="nav-card-title">智能问答</div>
            <div class="nav-card-desc">基于知识库内容进行智能问答</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("进入智能问答", type="secondary", use_container_width=True, key="nav_chat"):
            st.switch_page("pages/2_智能问答.py")


def render_usage_tips():
    """渲染使用提示"""
    st.markdown("---")
    st.markdown("### 📖 使用流程")

    col1, col2, col3 = st.columns(3)

    tips = [
        {"step": "1", "title": "上传文档", "desc": "在文档管理页上传PDF、Word等格式文件", "icon": "📤"},
        {"step": "2", "title": "自动处理", "desc": "系统自动解析、切片并向量化存储", "icon": "⚙️"},
        {"step": "3", "title": "智能问答", "desc": "进入问答页，基于知识库内容提问", "icon": "🔮"},
    ]

    for col, tip in zip([col1, col2, col3], tips):
        with col:
            st.markdown(f"""
            <div style="background: white; border-radius: 12px; padding: 1.25rem; border: 1px solid #E5E7EB;">
                <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
                    <span style="font-size: 1.5rem;">{tip['icon']}</span>
                    <span style="background: linear-gradient(135deg, #4F46E5, #7C3AED); color: white; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.8rem; font-weight: 600;">
                        步骤 {tip['step']}
                    </span>
                </div>
                <div style="font-weight: 600; color: #1F2937; margin-bottom: 0.25rem;">{tip['title']}</div>
                <div style="color: #6B7280; font-size: 0.85rem;">{tip['desc']}</div>
            </div>
            """, unsafe_allow_html=True)


def render_footer():
    """渲染页脚"""
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #9CA3AF; padding: 1rem 0;">
        <p style="margin-bottom: 0.25rem;">轻量级RAG知识库 MVP v1.0</p>
        <p style="font-size: 0.8rem;">基于 Streamlit + ChromaDB + OpenAI 构建</p>
    </div>
    """, unsafe_allow_html=True)


def render_home_page():
    """渲染主页"""
    # 渲染页面
    render_header()
    render_feature_cards()
    render_navigation()
    render_usage_tips()
    render_footer()


def main():
    """应用入口"""
    navigation = st.navigation([
        st.Page(render_home_page, title="主页", icon="🏠", default=True),
        st.Page("pages/1_上传管理.py", title="上传管理", icon="📁"),
        st.Page("pages/2_智能问答.py", title="智能问答", icon="💬")
    ])
    navigation.run()


main()
