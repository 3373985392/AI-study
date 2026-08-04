"""可被命令行与 Web 接口共同复用的聊天服务。

本模块只负责配置、上下文裁剪和模型流式调用，不保存任何用户会话。
调用方负责持有自己的历史记录，因此未来多个浏览器用户之间不会串话。
"""

import os
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from app.rag_bridge import stream_rag_answer


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SYSTEM_PROMPT = "你是一个简洁、准确的中文助手。"
MAX_HISTORY_ROUNDS = 10
RAG_TOP_K = 3
ALLOWED_HISTORY_ROLES = {"user", "assistant"}

Message = dict[str, str]


@dataclass(frozen=True)
class ChatSettings:
    """普通聊天模型的必要连接配置。"""

    api_key: str
    base_url: str
    model: str


def load_chat_settings() -> ChatSettings:
    """从仓库根目录加载配置，并集中报告缺失项。"""

    load_dotenv(REPOSITORY_ROOT / ".env")
    # 迁移期间兼容 cli-chat 目录内的旧配置，且不覆盖根目录已有变量。
    load_dotenv(REPOSITORY_ROOT / "projects" / "cli-chat" / ".env")

    values = {
        "LLM_API_KEY": os.getenv("LLM_API_KEY"),
        "LLM_BASE_URL": os.getenv("LLM_BASE_URL"),
        "LLM_MODEL": os.getenv("LLM_MODEL"),
    }
    missing = [name for name, value in values.items() if not value]

    if missing:
        raise RuntimeError(f"缺少环境变量: {', '.join(missing)}")

    return ChatSettings(
        api_key=values["LLM_API_KEY"] or "",
        base_url=values["LLM_BASE_URL"] or "",
        model=values["LLM_MODEL"] or "",
    )


def normalize_history(history: Iterable[Message]) -> list[Message]:
    """复制并校验外部会话历史，拒绝注入 system 等特殊角色。"""

    normalized: list[Message] = []

    for message in history:
        role = message.get("role")
        content = message.get("content")

        if role not in ALLOWED_HISTORY_ROLES:
            raise ValueError("历史消息角色只能是 user 或 assistant")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("历史消息内容不能为空")

        normalized.append({"role": role, "content": content})

    return normalized


class ChatService:
    """统一封装普通聊天和 RAG 聊天的流式输出。"""

    def __init__(
        self,
        client: OpenAI,
        model: str,
        *,
        max_history_rounds: int = MAX_HISTORY_ROUNDS,
        rag_top_k: int = RAG_TOP_K,
    ) -> None:
        if max_history_rounds < 1:
            raise ValueError("max_history_rounds 必须大于或等于 1")

        self.client = client
        self.model = model
        self.max_history_rounds = max_history_rounds
        self.rag_top_k = rag_top_k

    @classmethod
    def from_environment(cls) -> "ChatService":
        """使用环境变量创建生产聊天服务。"""

        settings = load_chat_settings()
        client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)
        return cls(client=client, model=settings.model)

    def stream_reply(
        self,
        user_input: str,
        history: Iterable[Message] = (),
        *,
        rag_enabled: bool = False,
    ) -> Iterator[str]:
        """根据当前问题逐段返回回答文本，不在服务内部保存会话。"""

        question = user_input.strip()

        if not question:
            raise ValueError("问题不能为空")

        if rag_enabled:
            yield from stream_rag_answer(question, top_k=self.rag_top_k)
            return

        normalized_history = normalize_history(history)
        # 为当前新问题预留一轮，只携带最近的上下文，限制请求体持续膨胀。
        history_limit = (self.max_history_rounds - 1) * 2
        recent_history = (
            normalized_history[-history_limit:] if history_limit else []
        )
        request_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *recent_history,
            {"role": "user", "content": question},
        ]

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=request_messages,
            stream=True,
        )

        received_content = False
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                received_content = True
                yield content

        if not received_content:
            raise RuntimeError("模型返回了空答案")

    def append_exchange(
        self,
        history: Iterable[Message],
        user_input: str,
        assistant_answer: str,
    ) -> list[Message]:
        """追加一轮完整问答，并保留配置允许的最大历史轮数。"""

        question = user_input.strip()
        answer = assistant_answer.strip()

        if not question:
            raise ValueError("问题不能为空")
        if not answer:
            raise ValueError("助手回答不能为空")

        updated_history = [
            *normalize_history(history),
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
        return updated_history[-self.max_history_rounds * 2 :]

