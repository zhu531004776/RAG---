# 轻量级RAG知识库

轻量级检索增强生成（RAG）知识库的最小可行产品（MVP）。

## 功能特性

- 📁 支持 PDF、Word、Markdown、TXT 四种格式文档上传
- 🔍 基于向量检索的精准问答
- 📎 每条回答附带来源追溯信息
- 💬 支持多轮连续对话

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，并填入你的 OpenAI API Key：

```bash
copy .env.example .env
```

编辑 `.env` 文件：
```
OPENAI_API_KEY=sk-your-api-key-here
```

### 3. 启动应用

```bash
streamlit run main.py
```

应用将在浏览器中打开（默认地址：http://localhost:8501）

### 4. 使用流程

1. 进入「文档上传管理」上传文档
2. 等待文档处理完成（状态变为"✅"）
3. 进入「智能问答」开始提问

## 项目结构

```
RAG知识库/
├── main.py                 # Streamlit入口
├── config.py              # 配置文件
├── requirements.txt       # 依赖清单
│
├── parser/                 # 文档解析模块
│   ├── base.py           # 解析器基类
│   ├── pdf_parser.py     # PDF解析
│   ├── docx_parser.py    # Word解析
│   ├── markdown_parser.py # Markdown解析
│   ├── txt_parser.py     # TXT解析
│   └── factory.py         # 解析器工厂
│
├── chunker/               # 文本切片模块
│   └── text_chunker.py   # 切片逻辑
│
├── vectorstore/           # 向量存储模块
│   └── chroma_store.py   # Chroma封装
│
├── llm/                   # 大模型接口模块
│   ├── base.py           # 接口基类
│   └── openai_llm.py     # OpenAI兼容接口
│
├── rag/                   # RAG核心管道
│   └── pipeline.py       # 问答管道
│
├── models/                # 数据模型
│   ├── document.py       # 文档模型
│   └── conversation.py   # 对话模型
│
└── pages/                 # Streamlit页面
    ├── upload_page.py     # 文档上传页
    └── chat_page.py       # 智能问答页
```

## 技术栈

- **Web框架**: Streamlit
- **Embedding模型**: sentence-transformers/all-MiniLM-L6-v2
- **向量数据库**: Chroma
- **大模型接口**: OpenAI兼容API

## 注意事项

- 首次运行时会自动下载Embedding模型（约22MB）
- 建议使用Python 3.9或更高版本
- 确保网络连接正常（需访问HuggingFace下载模型）
