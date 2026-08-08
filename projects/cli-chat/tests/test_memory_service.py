"""滚动会话记忆的离线单元测试。"""

import json
import unittest
from types import SimpleNamespace

from app.memory_service import ConversationMemory, MemoryService


class FakeMemoryCompletions:
    """返回确定性 JSON，并记录记忆模型收到的增量消息。"""

    def __init__(self) -> None:
        self.last_request = None

    def create(self, **kwargs):
        self.last_request = kwargs
        content = json.dumps({
            "summary": "用户正在实现长对话记忆。",
            "facts": ["项目使用 FastAPI"],
            "decisions": ["复用聊天模型生成摘要"],
            "open_items": ["补充生产观测"],
        }, ensure_ascii=False)
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=content),
        )])


class MemoryServiceTests(unittest.TestCase):
    def make_service(self, *, trigger_tokens: int = 1):
        completions = FakeMemoryCompletions()
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        service = MemoryService(
            client,
            "test-model",
            trigger_tokens=trigger_tokens,
            recent_rounds=1,
            max_input_tokens=10_000,
        )
        return service, completions

    @staticmethod
    def messages():
        return [
            {"id": "m1", "role": "user", "content": "问题一"},
            {"id": "m2", "role": "assistant", "content": "回答一"},
            {"id": "m3", "role": "user", "content": "问题二"},
            {"id": "m4", "role": "assistant", "content": "回答二"},
            {"id": "m5", "role": "user", "content": "最近问题"},
            {"id": "m6", "role": "assistant", "content": "最近回答"},
        ]

    def test_compact_keeps_recent_round_and_returns_boundary(self) -> None:
        service, completions = self.make_service()

        memory = service.compact(ConversationMemory(), self.messages())

        self.assertIsNotNone(memory)
        self.assertEqual(memory.summarized_through_message_id, "m4")
        self.assertIn("FastAPI", memory.facts[0])
        payload = json.loads(completions.last_request["messages"][1]["content"])
        self.assertEqual(len(payload["new_messages"]), 4)
        self.assertEqual(payload["new_messages"][-1]["content"], "回答二")

    def test_compact_only_reads_messages_after_existing_boundary(self) -> None:
        service, completions = self.make_service()
        memory = ConversationMemory(
            summary="已有摘要",
            summarized_through_message_id="m2",
        )

        updated = service.compact(memory, self.messages())

        self.assertIsNotNone(updated)
        payload = json.loads(completions.last_request["messages"][1]["content"])
        self.assertEqual(
            [item["content"] for item in payload["new_messages"]],
            ["问题二", "回答二"],
        )

    def test_compact_skips_short_context(self) -> None:
        service, completions = self.make_service(trigger_tokens=10_000)

        memory = service.compact(ConversationMemory(), self.messages())

        self.assertIsNone(memory)
        self.assertIsNone(completions.last_request)


if __name__ == "__main__":
    unittest.main()
