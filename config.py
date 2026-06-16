# RAG知识库配置文件

import os
from pathlib import Path
from dotenv import load_dotenv

# 某些部署环境会把 protobuf 升到过高版本，导致旧版依赖的 *_pb2.py 在运行时崩溃。
# 优先使用官方建议的 Python 实现兜底，避免「智能问答」页在导入 Chroma 相关依赖时直接报错。
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

# 加载环境变量
load_dotenv()

# ==================== 路径配置 ====================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
VECTOR_DB_DIR = DATA_DIR / "vector_db"

# 确保数据目录存在
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
VECTOR_DB_DIR.mkdir(exist_ok=True)

# ==================== 向量化模型配置 ====================
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DEVICE = "cpu"  # 可选: "cpu" 或 "cuda"（如有GPU）

# ==================== 切片配置 ====================
CHUNK_MIN_LENGTH = 200  # 单切片最小字符数
CHUNK_MAX_LENGTH = 300  # 单切片最大字符数
CHUNK_OVERLAP = 50      # 相邻切片重叠字符数

# ==================== 检索配置 ====================
TOP_K = 3  # 召回Top3最相关片段
NO_CONTENT_THRESHOLD = 0.8  # 无相关内容判定阈值（余弦距离越大越不相关）

# ==================== 大模型API配置 ====================
LLM_API_CONFIG = {
    "api_type": os.getenv("LLM_API_TYPE", "ark_responses"),
    "base_url": os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3/responses"),
    "api_key": os.getenv("ARK_API_KEY", ""),
    "model": os.getenv("ARK_MODEL", "deepseek-v4-flash-260425"),
    "timeout": int(os.getenv("LLM_TIMEOUT", "60")),
    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.3"))  # 生成温度，控制创造性
}

# ==================== Supabase 配置 ====================
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
SUPABASE_DOCUMENTS_TABLE = os.getenv("SUPABASE_DOCUMENTS_TABLE", "documents").strip()
USE_SUPABASE_DOC_STORE = os.getenv("USE_SUPABASE_DOC_STORE", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# ==================== 文件格式配置 ====================
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}

# ==================== 系统提示词 ====================
SYSTEM_PROMPT = """你是一个专业的知识库问答助手。你的职责是基于提供的上下文信息回答用户问题。

【核心约束】
1. 你只能使用以下提供的上下文信息来回答问题，严禁调用自身训练知识编造答案
2. 当上下文中没有相关信息时，必须明确回复：「当前知识库中无相关内容，无法解答」
3. 你的回答必须100%基于提供的上下文，不得添加任何未经证实的信息

【回答格式要求】
4. 不要在回答正文或末尾输出“参考来源”或来源列表，来源由界面统一展示
5. 回答内容应简洁明了，直接针对问题给出答案"""

# 无相关内容时的固定提示语
NO_RELEVANT_CONTENT_MSG = "当前知识库中无相关内容，无法解答"
