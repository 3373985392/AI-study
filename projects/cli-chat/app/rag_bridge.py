"""cli-chat 与 minimal-rag 之间的适配层。

RAG 的实现仍由 minimal-rag 负责；本文件只把它暴露成 cli-chat
可以消费的流式函数，避免把检索细节混进命令行交互循环。
"""

import sys
from pathlib import Path


# 当前两个项目是并列目录。集中在适配层处理路径，后续改成可安装包时只需修改这里。
PROJECTS_ROOT = Path(__file__).resolve().parent.parent.parent
RAG_PROJECT_ROOT = PROJECTS_ROOT / "minimal-rag"

if not RAG_PROJECT_ROOT.exists():
    raise RuntimeError(f"找不到 minimal-rag 项目: {RAG_PROJECT_ROOT}")

if str(RAG_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_PROJECT_ROOT))

from src.ask import stream_rag_answer  # noqa: E402


__all__ = ["stream_rag_answer"]
