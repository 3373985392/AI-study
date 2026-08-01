import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

api_key = os.getenv("LLM_API_KEY")
base_url = os.getenv("LLM_BASE_URL")
model = os.getenv("LLM_MODEL")

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

try:
    while True:
        user_input = input("\n你：").strip()

        if not user_input:
            continue

        if user_input.lower() in {"/exit", "/quit"} or user_input in {"/退出", "/再见"}:
            print("助手：再见！")
            break

        if user_input == "/clear":
            messages = messages[:1]
            print("助手：对话记忆已清空。")
            continue

        messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        print("助手：", end="", flush=True)
        assistant_parts = []

        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
            )

            for chunk in stream:
                content = chunk.choices[0].delta.content

                if content:
                    assistant_parts.append(content)
                    print(content, end="", flush=True)

            print()

        except Exception as error:
            messages.pop()
            print(f"\n请求失败：{error}")
            continue

        messages.append(
            {
                "role": "assistant",
                "content": "".join(assistant_parts),
            }
        )
except KeyboardInterrupt:
    print("\n\n助手：已退出。")