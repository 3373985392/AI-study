# Minimal RAG

一个不依赖 LangChain、LlamaIndex 等 RAG 框架的最小检索增强生成项目，用于从零理解 RAG 的完整数据链路。

项目当前使用 Vue 官方中文文档作为本地知识库，可以完成文档清洗、结构化切分、第三方 Embedding、向量持久化、混合检索、提示词构建以及带来源引用的流式回答。

## 工作流程

```text
本地 Markdown 文档
→ 加载与清洗
→ 按标题和 API 模式切分
→ 控制切片长度
→ Embedding 向量化
→ JSONL 持久化
→ 余弦相似度与标题加分检索
→ 拼接带编号来源的提示词
→ 聊天模型流式回答
```

## 已实现功能

- 加载本地 `.md` 和 `.txt` 文档
- 清理 Vue 文档中的标题锚点、API 包装标签和无用注释
- 识别文档标题、章节、子章节和 API 模式
- 保留完整代码块，避免按固定字符截断代码
- 将过长切片拆分到约 1200 字符以内，并保留段落重叠
- 批量调用 OpenAI 兼容的第三方 Embedding 接口
- 使用 JSONL 保存切片和向量，支持向量构建断点续传
- 使用 Python 标准库计算余弦相似度
- 根据文档标题、章节和 API 模式进行元数据加分
- 构造要求 `[来源 N]` 引用的 RAG 提示词
- 使用聊天模型流式生成带来源回答
- 通过 `cli-chat` 的 `/rag on` 命令进入交互式知识库问答

## 项目结构

```text
minimal-rag/
├─ docs/                    # 实际参与检索的知识库文档
├─ sources/                 # 外部资料原仓库及许可证，不直接参与检索
├─ data/
│  ├─ chunks.jsonl          # 清洗、切分后的文档切片
│  └─ vectors.jsonl         # 切片元数据及 Embedding 向量
├─ src/
│  ├─ document_loader.py    # 加载本地文档
│  ├─ document_cleaner.py   # 清洗 Markdown 与 Vue 专用包装标签
│  ├─ chunker.py            # 根据文档结构生成初始切片
│  ├─ chunk_resizer.py      # 拆分过长切片并处理段落重叠
│  ├─ chunk_store.py        # 将切片写入 JSONL
│  ├─ build_chunks.py       # 构建全部文档切片
│  ├─ embedding_client.py   # 第三方 Embedding 客户端
│  ├─ build_vectors.py      # 构建并持久化全部向量
│  ├─ retriever.py          # 余弦相似度与元数据混合检索
│  ├─ search.py             # 检索结果调试入口
│  ├─ prompt_builder.py     # 拼接资料、问题和引用规则
│  ├─ chat_client.py        # 普通与流式聊天模型调用
│  └─ ask.py                # 完整 RAG 问答入口
├─ eval_questions.md        # 自动检索评测问题
├─ requirements.txt         # Python 依赖
└─ README.md
```

## 环境要求

- Windows PowerShell
- Python 3.12
- OpenAI 兼容的 Embedding 和聊天模型接口
- 已在仓库根目录创建共享虚拟环境 `D:\myproject\.venv`

项目当前与 `cli-chat` 共用根目录虚拟环境，不需要在每个项目中重复创建 `.venv`。

## 安装依赖

在仓库根目录执行：

```powershell
cd D:\myproject
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\projects\minimal-rag\requirements.txt
```

## 配置模型

在仓库根目录复制统一环境变量模板：

```powershell
cd D:\myproject
Copy-Item .env.example .env
```

编辑根目录的 `.env`，其中与 RAG 相关的配置为：

```dotenv
EMBEDDING_API_KEY=你的_API_KEY
EMBEDDING_BASE_URL=你的_OpenAI_兼容接口地址
EMBEDDING_MODEL=text-embedding-v4
CHAT_MODEL=qwen3-max
```

不要将 `.env` 或 API Key 提交到 Git。

## 构建知识库

以下命令均在 `projects\minimal-rag` 中执行。

### 1. 清洗并切分文档

```powershell
python -m src.build_chunks
```

生成：

```text
data/chunks.jsonl
```

### 2. 生成并保存向量

```powershell
python -m src.build_vectors
```

生成：

```text
data/vectors.jsonl
```

向量构建支持检查点和内容摘要复用。文档内容、切分结果、Embedding 输入格式或模型发生变化后，应重新运行该命令。

## 测试检索

只执行检索，不调用聊天模型：

```powershell
python -m src.search "深层侦听器和普通侦听器有什么区别？" --top-k 5
```

输出包含综合分、向量分、标题加分、来源文件、章节及内容摘要，适合观察召回质量。

当前综合排序逻辑为：

```text
综合分 = 余弦相似度 + 元数据标题加分
```

## 完整 RAG 问答

```powershell
python -m src.ask "深层侦听器和普通侦听器有什么区别？" --top-k 3
```

回答会以流式方式输出，并要求关键结论使用以下格式引用检索资料：

```text
[来源 1]
```

资料不足时，提示词要求模型明确回答“根据现有资料无法确定”，而不是使用外部常识补全。

## 在 CLI Chat 中使用

`cli-chat` 通过独立适配层调用本项目。启动方式：

```powershell
cd D:\myproject\projects\cli-chat
python chat.py
```

交互命令：

```text
/rag on   开启本地知识库问答
/rag off  切回普通聊天
/clear    清空对话历史
/exit     退出程序
```

RAG 检索只使用当前问题，不会把整段聊天历史放入 Embedding 查询，避免旧话题干扰检索意图。

## 评测

[`eval_questions.md`](eval_questions.md) 保存了一组问题及预期来源。默认评测只调用
Embedding，计算 Recall@K 和 MRR：

```powershell
python -m src.evaluate --top-k 3
```

需要同时调用聊天模型验证 `[来源 N]` 引用编号时执行：

```powershell
python -m src.evaluate --top-k 3 --generate
```

评测会分别检查：

- 正确章节是否出现在 Top-K 中
- 排名靠前的切片是否足以回答问题
- 回答中的 `[来源 N]` 是否对应实际检索结果
- 资料不足的问题是否被模型明确拒答

## 数据来源

当前知识库来自 Vue 官方中文文档。原始资料和许可证保留在 `sources/`，实际参与检索的文档位于 `docs/`。使用或分发资料时应遵守原项目的 CC BY 4.0 许可证与署名要求。

## 设计原则

这个项目以学习 RAG 底层链路为目标，因此有意暂不使用 RAG 框架或向量数据库。当前 JSONL 与标准库实现适合小型知识库；当数据规模明显增大后，可以进一步引入批量评测、重排序模型、向量数据库和可安装的 Python 包结构。
