"""邀请码、会话、额度和 Web 接口的离线集成测试。"""

import tempfile
import threading
import time
import unittest
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from app.database import ChatDatabase
from app.security import secret_digest, validate_invite_code
from app.web_api import ActiveRequestRegistry, create_app
from app.web_settings import WebSettings


VALID_CODE = "FriendAccess2026_A"
ORIGIN = "http://localhost:5173"


class FakeChatService:
    """不连接外部模型的确定性聊天服务。"""

    def stream_reply(
        self,
        message,
        history=(),
        *,
        rag_enabled=False,
        persona_id="normal",
    ):
        prefix = "RAG:" if rag_enabled else "CHAT:"
        yield f"{prefix}{persona_id}:"
        yield message


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
        self.client = TestClient(
            create_app(self.settings, self.database, FakeChatService()),
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
            json={"message": "你好", "history": [], "mode": "chat"},
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
            json={"message": "第一问", "mode": "chat"},
            headers={"Origin": ORIGIN},
        )
        second = self.client.post(
            "/api/chat/stream",
            json={"message": "第二问", "mode": "chat"},
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

    def test_rag_mode_is_streamed_through_same_endpoint(self) -> None:
        self.redeem()

        response = self.client.post(
            "/api/chat/stream",
            json={"message": "Vue 是什么？", "mode": "rag"},
            headers={"Origin": ORIGIN},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("RAG:", response.text)

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
