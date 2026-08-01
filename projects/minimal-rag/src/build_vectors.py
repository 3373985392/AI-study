"""向量构建脚本：批量生成 Embedding，并支持断点续传。"""

import hashlib
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.embedding_client import embed_texts


CHUNKS_PATH = Path("data/chunks.jsonl")
VECTORS_PATH = Path("data/vectors.jsonl")
BATCH_SIZE = 10


def load_jsonl(path: Path) -> list[dict]:
    """读取 JSONL 文件。"""

    if not path.exists():
        return []

    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def content_hash(content: str) -> str:
    """计算正文摘要，用于判断切片内容是否变化。"""

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def write_checkpoint(records: list[dict]) -> None:
    """原子写入当前进度，避免中断时损坏正式文件。"""

    temporary_path = VECTORS_PATH.with_suffix(".jsonl.tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Windows 的杀毒软件或文件索引可能会短暂占用目标文件，
    # 因此在替换失败时等待并重试。
    for attempt in range(6):
        try:
            temporary_path.replace(VECTORS_PATH)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.5 * (attempt + 1))


def main() -> None:
    """为所有尚未处理或已经变化的切片生成向量。"""

    load_dotenv()
    model = os.getenv("EMBEDDING_MODEL")

    if not model:
        raise RuntimeError("缺少 EMBEDDING_MODEL")

    chunks = load_jsonl(CHUNKS_PATH)
    existing = {
        record["chunk_id"]: record
        for record in load_jsonl(VECTORS_PATH)
    }

    completed: dict[str, dict] = {}
    pending: list[tuple[dict, str, str]] = []

    for chunk in chunks:
        embedding_input = build_embedding_text(chunk)
        digest = content_hash(embedding_input)
        previous = existing.get(chunk["chunk_id"])

        if (
            previous
            and previous.get("embedding_model") == model
            and previous.get("embedding_input_hash") == digest
        ):
            completed[chunk["chunk_id"]] = previous
        else:
            pending.append((chunk, digest, embedding_input))

    print("总切片数:", len(chunks))
    print("可复用向量:", len(completed))
    print("待生成向量:", len(pending))

    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start : start + BATCH_SIZE]
        vectors = embed_texts(
            [embedding_input for _, _, embedding_input in batch]
        )

        if len(vectors) != len(batch):
            raise RuntimeError("Embedding 返回数量与输入数量不一致")

        for (chunk, digest, _), vector in zip(batch, vectors):
            completed[chunk["chunk_id"]] = {
                **chunk,
                "embedding_input_hash": digest,
                "embedding_model": model,
                "vector_dimension": len(vector),
                "embedding": vector,
            }

        ordered_records = [
            completed[chunk["chunk_id"]]
            for chunk in chunks
            if chunk["chunk_id"] in completed
        ]
        write_checkpoint(ordered_records)

        print(
            f"已完成: {len(completed)}/{len(chunks)}"
        )

    print("向量文件:", VECTORS_PATH)

def build_embedding_text(chunk: dict) -> str:
    """组合标题、章节和正文，提升语义检索效果。"""

    parts = [
        f"文档标题: {chunk['document_title']}",
        f"章节: {chunk['section_title']}",
    ]

    if chunk["subsection_title"]:
        parts.append(f"子章节: {chunk['subsection_title']}")

    if chunk["api_mode"]:
        parts.append(f"API 模式: {chunk['api_mode']}")

    parts.append(f"正文:\n{chunk['content']}")
    return "\n".join(parts)


if __name__ == "__main__":
    main()