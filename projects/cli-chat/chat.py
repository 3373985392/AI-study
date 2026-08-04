from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)

from app.chat_service import ChatService


def print_request_error(error: Exception, *, rag_enabled: bool) -> None:
    """把模型 SDK 异常转换成适合终端用户阅读的中文提示。"""

    prefix = "RAG 请求失败" if rag_enabled else "请求失败"

    if isinstance(error, AuthenticationError):
        message = "API Key 无效或没有模型访问权限。"
    elif isinstance(error, RateLimitError):
        message = "请求过于频繁或额度不足，请稍后重试。"
    elif isinstance(error, APITimeoutError):
        message = "模型响应超时，请检查网络后重试。"
    elif isinstance(error, APIConnectionError):
        message = "无法连接模型服务，请检查网络和接口地址。"
    elif isinstance(error, APIStatusError):
        message = f"模型服务返回 HTTP {error.status_code} 错误。"
    else:
        message = f"发生未知错误：{error}"

    print(f"\n{prefix}：{message}")


def main() -> None:
    """维护单个终端会话，并把模型工作委托给共享聊天服务。"""

    service = ChatService.from_environment()
    history = []
    rag_enabled = False

    try:
        while True:
            user_input = input("\n你：").strip()

            if not user_input:
                continue

            if user_input.lower() in {"/exit", "/quit"} or user_input in {
                "/退出",
                "/再见",
            }:
                print("助手：再见！")
                break

            if user_input.lower() == "/rag on":
                rag_enabled = True
                print("助手：RAG 知识库模式已开启。")
                continue

            if user_input.lower() == "/rag off":
                rag_enabled = False
                print("助手：已切回普通聊天模式。")
                continue

            if user_input == "/clear":
                history = []
                print("助手：对话记忆已清空。")
                continue

            label = "助手（RAG）：" if rag_enabled else "助手："
            print(label, end="", flush=True)
            assistant_parts = []

            try:
                for content in service.stream_reply(
                    user_input,
                    history,
                    rag_enabled=rag_enabled,
                ):
                    assistant_parts.append(content)
                    print(content, end="", flush=True)
                print()
            except Exception as error:
                print_request_error(error, rag_enabled=rag_enabled)
                continue

            # 只有完整回答成功后才写入历史，避免把半截响应带到下一次请求。
            history = service.append_exchange(
                history,
                user_input,
                "".join(assistant_parts),
            )
    except (KeyboardInterrupt, EOFError):
        print("\n\n助手：已退出。")


if __name__ == "__main__":
    main()
