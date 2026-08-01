"""向量检索模块：计算查询与文档切片的余弦相似度。"""

import json
import math
from pathlib import Path

from src.embedding_client import embed_text


# 使用绝对项目路径，避免从 cli-chat 等其他目录调用时找不到向量文件。
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VECTORS_PATH = PROJECT_ROOT / "data" / "vectors.jsonl"


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """计算两个等长向量的余弦相似度。"""

    if len(left) != len(right):
        raise ValueError(
            f"向量维度不一致: {len(left)} != {len(right)}"
        )

    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return dot_product / (left_norm * right_norm)


def load_vector_records() -> list[dict]:
    """从 JSONL 文件加载向量记录。"""

    return [
        json.loads(line)
        for line in VECTORS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """返回与查询最相似的前 top_k 个切片。"""

    query_vector = embed_text(query)
    results: list[dict] = []

    for record in load_vector_records():
        vector_score = cosine_similarity(
            query_vector,
            record["embedding"],
        )
        bonus = metadata_bonus(query, record)
        score = vector_score + bonus

        results.append(
            {
                "score": score,
                "chunk_id": record["chunk_id"],
                "source_file": record["source_file"],
                "document_title": record["document_title"],
                "section_title": record["section_title"],
                "subsection_title": record["subsection_title"],
                "api_mode": record["api_mode"],
                "content": record["content"],
                "vector_score": vector_score,
                "metadata_bonus": bonus,
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]

def metadata_bonus(query: str, record: dict) -> float:
    """当查询明确包含标题或 API 模式时给予额外分数。"""

    normalized_query = query.lower()
    bonus = 0.0

    fields = [
        ("document_title", 0.03),
        ("section_title", 0.15),
        ("subsection_title", 0.10),
        ("api_mode", 0.05),
    ]

    for field, weight in fields:
        value = record.get(field, "").strip().lower()
        if value and value in normalized_query:
            bonus += weight

    return min(bonus, 0.25)
