"""最小 RAG 问答入口：串联检索、提示词构建和流式回答。"""

import argparse
import os
import threading
from collections.abc import Iterator

from src.chat_client import stream_answer
from src.prompt_builder import build_prompt
from src.retriever import retrieve


class InsufficientKnowledgeError(RuntimeError):
    """当前知识库没有达到最低相关度的资料。"""


def stream_rag_answer(
    question: str,
    top_k: int = 3,
    *,
    on_sources=None,
    cancel_event: threading.Event | None = None,
) -> Iterator[str]:
    """检索与问题相关的资料，并流式产出带引用的回答。"""

    question = question.strip()

    if not question:
        raise ValueError("问题不能为空")

    if top_k < 1:
        raise ValueError("top_k 必须大于或等于 1")

    # 第一步：把当前问题向量化，并取回最相关的文档切片。
    results = retrieve(question, top_k=top_k)
    minimum_score = float(os.getenv("RAG_MIN_VECTOR_SCORE", "0.35"))
    results = [result for result in results if result["vector_score"] >= minimum_score]

    if not results:
        raise InsufficientKnowledgeError("根据现有 Vue 知识库无法确定")

    if on_sources:
        on_sources(results)

    # 第二步：给资料编号，并加入严格引用和资料不足时的回答规则。
    prompt = build_prompt(question, results)

    # 第三步：把完整提示词交给聊天模型，并逐段向调用方返回文本。
    for token in stream_answer(prompt):
        if cancel_event and cancel_event.is_set():
            break
        yield token


def main() -> None:
    """读取命令行问题，并在终端中实时打印 RAG 回答。"""

    parser = argparse.ArgumentParser(
        description="从本地 Vue 文档检索资料并生成带来源引用的回答",
    )
    parser.add_argument("question", help="需要查询的问题")
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="提供给聊天模型的检索切片数量，默认 3",
    )
    args = parser.parse_args()

    print("助手：", end="", flush=True)

    for content in stream_rag_answer(args.question, top_k=args.top_k):
        print(content, end="", flush=True)

    print()


if __name__ == "__main__":
    main()
