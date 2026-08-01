"""聊天模型客户端：封装普通响应和流式响应两种调用方式。

本模块只负责与聊天模型通信，不负责检索文档或构造 RAG 提示词。
这样命令行程序、单次问答程序都可以复用同一个模型客户端。
"""

import os
from collections.abc import Iterator
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# 所有项目优先读取仓库根目录的统一配置。
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPOSITORY_ROOT = PROJECT_ROOT.parent.parent
ENV_PATH = REPOSITORY_ROOT / ".env"
LEGACY_ENV_PATH = PROJECT_ROOT / ".env"


def load_chat_config() -> tuple[str, str, str]:
    """加载并校验聊天模型所需的环境变量。"""

    load_dotenv(ENV_PATH)
    # 迁移期间兼容旧配置；根目录已有的变量不会被这里覆盖。
    load_dotenv(LEGACY_ENV_PATH)

    # 当前项目的 Embedding 与聊天模型使用同一个兼容接口和 API Key。
    api_key = os.getenv("EMBEDDING_API_KEY")
    base_url = os.getenv("EMBEDDING_BASE_URL")
    model = os.getenv("CHAT_MODEL")

    missing = [
        name
        for name, value in (
            ("EMBEDDING_API_KEY", api_key),
            ("EMBEDDING_BASE_URL", base_url),
            ("CHAT_MODEL", model),
        )
        if not value
    ]

    if missing:
        raise RuntimeError(f"缺少环境变量: {', '.join(missing)}")

    # 帮助类型检查器理解：上面的校验通过后，三个值一定都是字符串。
    assert api_key is not None
    assert base_url is not None
    assert model is not None
    return api_key, base_url, model


def create_chat_client() -> tuple[OpenAI, str]:
    """创建 OpenAI 兼容客户端，同时返回聊天模型名称。"""

    api_key, base_url, model = load_chat_config()
    client = OpenAI(api_key=api_key, base_url=base_url)
    return client, model


def stream_answer(prompt: str) -> Iterator[str]:
    """流式生成答案，每次产出一小段模型文本。"""

    if not prompt.strip():
        raise ValueError("提示词不能为空")

    client, model = create_chat_client()
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        # RAG 问答强调忠于检索资料，因此降低输出随机性。
        temperature=0.1,
    )

    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content


def generate_answer(prompt: str) -> str:
    """生成完整答案，供不需要流式打印的调用方使用。"""

    answer = "".join(stream_answer(prompt)).strip()

    if not answer:
        raise RuntimeError("聊天模型返回了空答案")

    return answer
