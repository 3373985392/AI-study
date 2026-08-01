import os
from pathlib import Path

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from app.rag_bridge import stream_rag_answer


# 所有项目优先读取仓库根目录的统一配置。
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(REPOSITORY_ROOT / ".env")

# 迁移期间兼容旧配置；根目录已有的变量不会被这里覆盖。
load_dotenv(Path(__file__).resolve().parent / ".env")

api_key = os.getenv("LLM_API_KEY")
base_url = os.getenv("LLM_BASE_URL")
model = os.getenv("LLM_MODEL")

MAX_HISTORY_ROUNDS = 10
RAG_TOP_K = 3

if not all((api_key, base_url, model)):
    raise RuntimeError("缺少 LLM_API_KEY、LLM_BASE_URL 或 LLM_MODEL")

client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)

messages = [
    {
        "role": "system",
        "content": "你是一个简洁、准确的中文命令行助手。",
    }
]
rag_enabled = False

try:
    while True:
        user_input = input("\n你：").strip()

        if not user_input:
            continue

        if user_input.lower() in {"/exit", "/quit"} or user_input in {"/退出", "/再见",}:
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
            messages = messages[:1]
            print("助手：对话记忆已清空。")
            continue

        current_user_message = {
            "role": "user",
            "content": user_input,
        }

        if rag_enabled:
            print("助手（RAG）：", end="", flush=True)
            assistant_parts = []

            try:
                # 检索只针对当前问题；聊天历史不参与向量检索。
                for content in stream_rag_answer(user_input, top_k=RAG_TOP_K):
                    assistant_parts.append(content)
                    print(content, end="", flush=True)
                print()

            except AuthenticationError:
                print("\nRAG 请求失败：API Key 无效或没有模型访问权限。")
                continue

            except RateLimitError:
                print("\nRAG 请求失败：请求过于频繁或额度不足，请稍后重试。")
                continue

            except APITimeoutError:
                print("\nRAG 请求失败：模型响应超时，请检查网络后重试。")
                continue

            except APIConnectionError:
                print("\nRAG 请求失败：无法连接 Embedding 或聊天模型服务。")
                continue

            except APIStatusError as error:
                print(f"\nRAG 请求失败：模型服务返回 HTTP {error.status_code} 错误。")
                continue

            except Exception as error:
                print(f"\nRAG 请求失败：{error}")
                continue

            # 记录 RAG 问答，但下一次检索仍只使用新的当前问题。
            messages.append(current_user_message)
            messages.append({"role": "assistant", "content": "".join(assistant_parts)})
            messages = [messages[0], *messages[-MAX_HISTORY_ROUNDS * 2:]]
            continue

        previous_messages = messages[1:]

        previous_messages = previous_messages[
            -(MAX_HISTORY_ROUNDS - 1) * 2:
        ]

        request_messages = [
            messages[0],
            *previous_messages,
            current_user_message,
        ]

        print("助手：", end="", flush=True)
        assistant_parts = []

        try:
            stream = client.chat.completions.create(
                model=model,
                messages=request_messages,
                stream=True,
            )

            for chunk in stream:
                content = chunk.choices[0].delta.content

                if content:
                    assistant_parts.append(content)
                    print(content, end="", flush=True)

            print()

        except AuthenticationError:
            print("\n请求失败：API Key 无效或没有模型访问权限。")
            continue

        except RateLimitError:
            print("\n请求失败：请求过于频繁或额度不足，请稍后重试。")
            continue

        except APITimeoutError:
            print("\n请求失败：模型响应超时，请检查网络后重试。")
            continue

        except APIConnectionError:
            print("\n请求失败：无法连接模型服务，请检查网络和接口地址。")
            continue

        except APIStatusError as error:
            print(
                f"\n请求失败：模型服务返回 HTTP {error.status_code} 错误。"
            )
            continue

        except Exception as error:
            print(f"\n请求失败：发生未知错误：{error}")
            continue

        messages.append(current_user_message)

        messages.append(
            {
                "role": "assistant",
                "content": "".join(assistant_parts),
            }
        )

        messages = [
            messages[0],
            *messages[-MAX_HISTORY_ROUNDS * 2:],
        ]
except (KeyboardInterrupt, EOFError):
    print("\n\n助手：已退出。")
