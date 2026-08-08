"""Embedding 客户端：通过 OpenAI 兼容接口调用第三方模型。"""

import os
from pathlib import Path

from dotenv import load_dotenv
from httpx import Timeout
from openai import OpenAI


# 所有项目优先读取仓库根目录的统一配置。
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPOSITORY_ROOT = PROJECT_ROOT.parent.parent
ENV_PATH = REPOSITORY_ROOT / ".env"
LEGACY_ENV_PATH = PROJECT_ROOT / ".env"


def create_embedding_client() -> OpenAI:
    """读取环境变量并创建 Embedding 客户端。"""

    load_dotenv(ENV_PATH)
    # 迁移期间兼容旧配置；根目录已有的变量不会被这里覆盖。
    load_dotenv(LEGACY_ENV_PATH)

    api_key = os.getenv("EMBEDDING_API_KEY")
    base_url = os.getenv("EMBEDDING_BASE_URL")

    if not api_key:
        raise RuntimeError("缺少 EMBEDDING_API_KEY")
    if not base_url:
        raise RuntimeError("缺少 EMBEDDING_BASE_URL")

    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
        timeout=Timeout(
            float(os.getenv("LLM_READ_TIMEOUT_SECONDS", "60")),
            connect=float(os.getenv("LLM_CONNECT_TIMEOUT_SECONDS", "10")),
        ),
    )


def embed_text(text: str) -> list[float]:
    """将一段文本转换为向量。"""

    return embed_texts([text])[0]

def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量将多段文本转换为向量，并按输入顺序返回。"""

    if not texts:
        return []

    load_dotenv(ENV_PATH)
    load_dotenv(LEGACY_ENV_PATH)
    model = os.getenv("EMBEDDING_MODEL")

    if not model:
        raise RuntimeError("缺少 EMBEDDING_MODEL")

    client = create_embedding_client()
    response = client.embeddings.create(
        model=model,
        input=texts,
    )

    ordered_data = sorted(response.data, key=lambda item: item.index)
    return [item.embedding for item in ordered_data]
