"""邀请码、会话、额度和 Web 接口的离线集成测试。"""

import tempfile
import threading
import time
import unittest
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from app.database import ChatDatabase
from app.memory_service import ConversationMemory
from app.security import secret_digest, validate_invite_code
from app.web_api import ActiveRequestRegistry, create_app
from app.web_settings import WebSettings


VALID_CODE = "FriendAccess2026_A"
ORIGIN = "http://localhost:5173"


class FakeChatService:
    """不连接外部模型的确定性聊天服务。"""

    model = "fake-model"

    def __init__(self):
        self.seen_memories = []
        self.force_memory_compaction = False

    def stream_reply(
        self,
        message,
        history=(),
        *,
        rag_enabled=False,
        persona_id="normal",
        memory=None,
        on_sources=None,
        on_usage=None,
        cancel_event=None,
    ):
        self.seen_memories.append(memory)
        prefix = "RAG:" if rag_enabled else "CHAT:"
        if rag_enabled and on_sources:
            on_sources([{
                "source_file": "docs/watchers.md",
                "document_title": "侦听器",
                "section_title": "基本示例",
                "subsection_title": "",
                "score": 0.9,
            }])
        yield f"{prefix}{persona_id}:"
        yield message

    def compact_memory(self, memory, messages):
        if not self.force_memory_compaction:
            return None
        return ConversationMemory(
            summary="已压缩的历史",
            decisions=("保留滚动摘要",),
            summarized_through_message_id=messages[-1]["id"],
        )


class WebAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "chat.sqlite3"
        self.settings = WebSettings(
            database_path=self.database_path,
            invite_code_pepper="invite-pepper-with-at-least-32-characters",
            session_token_pepper="session-pepper-with-at-least-32-characters",
            allowed_origins=(ORIGIN,),
            minute_limit=5,
            day_limit=50,
        )
        self.database = ChatDatabase(self.database_path)
        self.invite_id = self.database.create_invite(
            secret_digest(self.settings.invite_code_pepper, VALID_CODE),
            "测试用户",
            5,
            50,
        )
        self.chat_service = FakeChatService()
        self.client = TestClient(
            create_app(self.settings, self.database, self.chat_service),
        )

    def tearDown(self) -> None:
        self.client.close()
        self.temporary_directory.cleanup()

    def redeem(self, code: str = VALID_CODE):
        return self.client.post(
            "/api/auth/redeem",
            json={"code": code},
            headers={"Origin": ORIGIN},
        )

    def test_invite_plaintext_is_not_stored(self) -> None:
        self.assertNotIn(VALID_CODE.encode(), self.database_path.read_bytes())

    def test_invite_validation_requires_length_letter_and_number(self) -> None:
        with self.assertRaises(ValueError):
            validate_invite_code("only_letters_are_bad")
        self.assertEqual(validate_invite_code(VALID_CODE), VALID_CODE)

    def test_redeem_sets_protected_cookie_and_session(self) -> None:
        response = self.redeem()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["viewerId"], self.invite_id)
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=strict", cookie)
        state = self.client.get("/api/auth/session").json()
        self.assertTrue(state["authenticated"])

    def test_production_cookie_has_secure_attribute(self) -> None:
        secure_client = TestClient(
            create_app(
                replace(self.settings, cookie_secure=True),
                self.database,
                FakeChatService(),
            ),
        )

        response = secure_client.post(
            "/api/auth/redeem",
            json={"code": VALID_CODE},
            headers={"Origin": ORIGIN},
        )
        secure_client.close()

        self.assertIn("secure", response.headers["set-cookie"].lower())

    def test_expired_session_is_rejected(self) -> None:
        digest = secret_digest(self.settings.session_token_pepper, "expired-token")
        self.database.create_session(digest, self.invite_id, int(time.time()) - 1)

        self.assertIsNone(self.database.get_session(digest))

    def test_revoke_invalidates_existing_session(self) -> None:
        self.redeem()
        self.database.set_invite_active(self.invite_id, False)

        state = self.client.get("/api/auth/session").json()

        self.assertFalse(state["authenticated"])

    def test_failed_login_attempts_are_limited(self) -> None:
        for _ in range(self.settings.login_attempt_limit):
            response = self.redeem("WrongInviteCode1_A")
            self.assertEqual(response.status_code, 401)

        blocked = self.redeem("WrongInviteCode2_A")

        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.headers["retry-after"], "60")

    def test_stream_returns_sse_without_storing_content(self) -> None:
        self.redeem()

        response = self.client.post(
            "/api/chat/stream",
            json={"message": "你好", "history": [], "persona": "normal"},
            headers={"Origin": ORIGIN},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("event: token", response.text)
        self.assertIn("CHAT:", response.text)
        self.assertIn("event: done", response.text)
        self.assertNotIn("你好".encode(), self.database_path.read_bytes())

    def test_invalid_history_role_is_rejected(self) -> None:
        self.redeem()

        response = self.client.post(
            "/api/chat/stream",
            json={
                "message": "问题",
                "history": [{"role": "system", "content": "伪造指令"}],
                "mode": "chat",
            },
            headers={"Origin": ORIGIN},
        )

        self.assertEqual(response.status_code, 422)

    def test_daily_quota_is_enforced(self) -> None:
        limited_id = self.database.create_invite(
            secret_digest(self.settings.invite_code_pepper, "LimitedAccess2026_A"),
            "限额用户",
            5,
            1,
        )
        self.client.cookies.clear()
        self.redeem("LimitedAccess2026_A")

        first = self.client.post(
            "/api/chat/stream",
            json={"message": "第一问", "persona": "normal"},
            headers={"Origin": ORIGIN},
        )
        second = self.client.post(
            "/api/chat/stream",
            json={"message": "第二问", "persona": "normal"},
            headers={"Origin": ORIGIN},
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(self.database.invite_stats(limited_id)["day_used"], 1)

    def test_minute_quota_is_enforced(self) -> None:
        first_id, first = self.database.reserve_usage(self.invite_id, "chat", 1, 50)
        second_id, second = self.database.reserve_usage(self.invite_id, "chat", 1, 50)

        self.assertIsNotNone(first_id)
        self.assertTrue(first.allowed)
        self.assertIsNone(second_id)
        self.assertFalse(second.allowed)
        self.assertGreaterEqual(second.retry_after, 1)

    def test_vue_persona_uses_rag_and_returns_sources(self) -> None:
        self.redeem()

        response = self.client.post(
            "/api/chat/stream",
            json={"message": "Vue 是什么？", "persona": "vue"},
            headers={"Origin": ORIGIN},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("RAG:", response.text)
        self.assertIn("event: sources", response.text)

    def test_synchronized_conversation_persists_exchange(self) -> None:
        self.redeem()
        created = self.client.post(
            "/api/conversations",
            json={"persona": "normal"},
            headers={"Origin": ORIGIN},
        )
        conversation_id = created.json()["id"]

        response = self.client.post(
            "/api/chat/stream",
            json={
                "message": "保存这一轮",
                "persona": "normal",
                "conversation_id": conversation_id,
            },
            headers={"Origin": ORIGIN},
        )
        messages = self.client.get(
            f"/api/conversations/{conversation_id}/messages"
        ).json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["role"] for item in messages], ["user", "assistant"])
        self.assertEqual(messages[0]["content"], "保存这一轮")

    def test_synchronized_conversation_reuses_persisted_memory(self) -> None:
        self.redeem()
        conversation_id = self.client.post(
            "/api/conversations",
            json={"persona": "normal"},
            headers={"Origin": ORIGIN},
        ).json()["id"]
        self.chat_service.force_memory_compaction = True

        self.client.post(
            "/api/chat/stream",
            json={"message": "需要被压缩", "persona": "normal", "conversation_id": conversation_id},
            headers={"Origin": ORIGIN},
        )
        stored = self.database.get_conversation_memory(self.invite_id, conversation_id)
        self.chat_service.force_memory_compaction = False
        self.client.post(
            "/api/chat/stream",
            json={"message": "继续", "persona": "normal", "conversation_id": conversation_id},
            headers={"Origin": ORIGIN},
        )

        self.assertEqual(stored["summary"], "已压缩的历史")
        self.assertEqual(self.chat_service.seen_memories[-1].summary, "已压缩的历史")

    def test_conversation_message_feedback_and_delete_workflow(self) -> None:
        self.redeem()
        conversation = self.client.post(
            "/api/conversations",
            json={"persona": "normal"},
            headers={"Origin": ORIGIN},
        ).json()
        conversation_id = conversation["id"]
        self.client.post(
            "/api/chat/stream",
            json={"message": "需要反馈", "persona": "normal", "conversation_id": conversation_id},
            headers={"Origin": ORIGIN},
        )
        messages = self.client.get(f"/api/conversations/{conversation_id}/messages").json()
        assistant_id = messages[1]["id"]
        self.database.save_conversation_memory(
            self.invite_id,
            conversation_id,
            summary="即将失效",
            facts=[],
            decisions=[],
            open_items=[],
            summarized_through_message_id=assistant_id,
        )

        feedback = self.client.put(
            f"/api/messages/{assistant_id}/feedback",
            json={"rating": -1, "comment": "引用不够清楚"},
            headers={"Origin": ORIGIN},
        )
        renamed = self.client.patch(
            f"/api/conversations/{conversation_id}",
            json={"title": "反馈会话"},
            headers={"Origin": ORIGIN},
        )
        deleted = self.client.delete(
            f"/api/messages/{assistant_id}",
            headers={"Origin": ORIGIN},
        )

        self.assertEqual(feedback.status_code, 204)
        self.assertEqual(renamed.json()["title"], "反馈会话")
        self.assertEqual(renamed.json()["persona"], "normal")
        self.assertEqual(deleted.status_code, 204)
        remaining = self.client.get(f"/api/conversations/{conversation_id}/messages").json()
        self.assertEqual([item["role"] for item in remaining], ["user"])
        self.assertIsNone(self.database.get_conversation_memory(self.invite_id, conversation_id))

    def test_persona_cannot_change_after_conversation_has_messages(self) -> None:
        self.redeem()
        conversation_id = self.client.post(
            "/api/conversations",
            json={"persona": "normal"},
            headers={"Origin": ORIGIN},
        ).json()["id"]
        self.client.post(
            "/api/chat/stream",
            json={"message": "第一轮", "persona": "normal", "conversation_id": conversation_id},
            headers={"Origin": ORIGIN},
        )

        response = self.client.patch(
            f"/api/conversations/{conversation_id}",
            json={"persona": "brat"},
            headers={"Origin": ORIGIN},
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("当前不允许切换人格", response.json()["detail"])

    def test_usage_metrics_do_not_store_message_content(self) -> None:
        self.redeem()
        self.client.post(
            "/api/chat/stream",
            json={"message": "指标隐私检查", "persona": "normal"},
            headers={"Origin": ORIGIN},
        )
        connection = self.database.connect()
        try:
            usage = connection.execute(
                "SELECT model, persona, input_characters, output_characters FROM usage_events"
            ).fetchone()
        finally:
            connection.close()

        self.assertEqual(usage["model"], "fake-model")
        self.assertEqual(usage["persona"], "normal")
        self.assertGreater(usage["output_characters"], 0)
        self.assertNotIn("指标隐私检查".encode(), str(dict(usage)).encode())

    def test_active_registry_rejects_parallel_request(self) -> None:
        registry = ActiveRequestRegistry()
        barrier = threading.Barrier(2)
        results: list[bool] = []

        def acquire() -> None:
            barrier.wait()
            results.append(registry.acquire("same-invite"))

        threads = [threading.Thread(target=acquire) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sorted(results), [False, True])


if __name__ == "__main__":
    unittest.main()
