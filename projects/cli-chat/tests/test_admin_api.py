"""管理员认证、邀请码管理和跨邀请码历史查询测试。"""

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from app.admin_security import credential_fingerprint, hash_admin_password
from app.database import ChatDatabase
from app.security import secret_digest
from app.web_api import create_app
from app.web_settings import WebSettings


ORIGIN = "http://localhost:5173"
ADMIN_PASSWORD = "StrongAdminPassword2026!"
USER_CODE = "FriendAccess2026_A"


class UnusedChatService:
    model = "unused"


class AdminApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.password_hash = hash_admin_password(ADMIN_PASSWORD)

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "chat.sqlite3"
        self.settings = WebSettings(
            database_path=self.database_path,
            invite_code_pepper="invite-pepper-with-at-least-32-characters",
            session_token_pepper="session-pepper-with-at-least-32-characters",
            admin_password_hash=self.password_hash,
            admin_session_token_pepper="admin-session-pepper-with-at-least-32-characters",
            allowed_origins=(ORIGIN,),
        )
        self.database = ChatDatabase(self.database_path)
        self.invite_id = self.database.create_invite(
            secret_digest(self.settings.invite_code_pepper, USER_CODE),
            "朋友A",
            5,
            50,
        )
        self.client = TestClient(create_app(self.settings, self.database, UnusedChatService()))

    def tearDown(self) -> None:
        self.client.close()
        self.temporary_directory.cleanup()

    def login(self, password: str = ADMIN_PASSWORD):
        return self.client.post(
            "/api/admin/auth/login",
            json={"password": password},
            headers={"Origin": ORIGIN},
        )

    def test_admin_login_cookie_is_independent_and_rotation_invalidates_session(self) -> None:
        response = self.login()

        self.assertEqual(response.status_code, 200)
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("ai_chat_admin_session", cookie)
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=strict", cookie)
        self.assertTrue(self.client.get("/api/admin/auth/session").json()["authenticated"])
        self.assertFalse(self.client.get("/api/auth/session").json()["authenticated"])

        rotated_settings = replace(
            self.settings,
            admin_password_hash=hash_admin_password("AnotherStrongPassword2026!"),
        )
        rotated = TestClient(create_app(rotated_settings, self.database, UnusedChatService()))
        rotated.cookies.set("ai_chat_admin_session", self.client.cookies.get("ai_chat_admin_session"))
        try:
            self.assertFalse(rotated.get("/api/admin/auth/session").json()["authenticated"])
        finally:
            rotated.close()

    def test_admin_cookie_uses_secure_attribute_in_production(self) -> None:
        secure = TestClient(create_app(
            replace(self.settings, cookie_secure=True),
            self.database,
            UnusedChatService(),
        ))
        try:
            response = secure.post(
                "/api/admin/auth/login",
                json={"password": ADMIN_PASSWORD},
                headers={"Origin": ORIGIN},
            )
            self.assertIn("secure", response.headers["set-cookie"].lower())
        finally:
            secure.close()

    def test_admin_login_is_rate_limited(self) -> None:
        for _ in range(self.settings.admin_login_attempt_limit):
            self.assertEqual(self.login("wrong-password").status_code, 401)

        blocked = self.login("wrong-password")

        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.headers["retry-after"], "60")

    def test_normal_invite_cookie_cannot_access_admin_api(self) -> None:
        ordinary = TestClient(create_app(self.settings, self.database, UnusedChatService()))
        try:
            redeemed = ordinary.post(
                "/api/auth/redeem",
                json={"code": USER_CODE},
                headers={"Origin": ORIGIN},
            )
            self.assertEqual(redeemed.status_code, 200)
            self.assertEqual(ordinary.get("/api/admin/invites").status_code, 401)
        finally:
            ordinary.close()

    def test_create_generated_and_custom_invites_then_update_and_revoke(self) -> None:
        self.login()
        generated = self.client.post(
            "/api/admin/invites",
            json={"mode": "generated", "label": "自动", "minute_limit": 3, "day_limit": 30},
            headers={"Origin": ORIGIN},
        )
        custom_code = "CustomInvite2026_A"
        custom = self.client.post(
            "/api/admin/invites",
            json={
                "mode": "custom", "label": "自定义", "minute_limit": 4, "day_limit": 40,
                "code": custom_code, "code_confirmation": custom_code,
            },
            headers={"Origin": ORIGIN},
        )

        self.assertEqual(generated.status_code, 201)
        self.assertRegex(generated.json()["oneTimeCode"], r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9_-]{16,64}$")
        self.assertEqual(custom.status_code, 201)
        self.assertNotIn(custom_code.encode(), self.database_path.read_bytes())
        duplicate = self.client.post(
            "/api/admin/invites",
            json={
                "mode": "custom", "label": "重复", "minute_limit": 4, "day_limit": 40,
                "code": custom_code, "code_confirmation": custom_code,
            },
            headers={"Origin": ORIGIN},
        )
        self.assertEqual(duplicate.status_code, 409)

        invite_id = custom.json()["invite"]["id"]
        token_digest = secret_digest(self.settings.session_token_pepper, "ordinary-token")
        self.database.create_session(token_digest, invite_id, 4_000_000_000)
        updated = self.client.patch(
            f"/api/admin/invites/{invite_id}",
            json={"label": "修改后", "minute_limit": 9, "day_limit": 90, "active": False},
            headers={"Origin": ORIGIN},
        )

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["label"], "修改后")
        self.assertFalse(updated.json()["active"])
        self.assertIsNone(self.database.get_session(token_digest))

    def test_admin_reads_paginated_history_memory_and_audit_without_body(self) -> None:
        conversation = self.database.create_conversation(self.invite_id, "normal", "隐私测试")
        self.database.append_exchange(
            self.invite_id,
            conversation["id"],
            "敏感聊天正文",
            "助手回复正文",
            [],
        )
        messages = self.database.list_messages(self.invite_id, conversation["id"])
        self.database.save_conversation_memory(
            self.invite_id,
            conversation["id"],
            summary="摘要内容",
            facts=["事实一"],
            decisions=[],
            open_items=[],
            summarized_through_message_id=messages[-1]["id"],
        )
        self.login()

        invites = self.client.get("/api/admin/invites?page=1&page_size=1").json()
        conversations = self.client.get(
            f"/api/admin/invites/{self.invite_id}/conversations?page=1&page_size=1"
        ).json()
        history = self.client.get(
            f"/api/admin/conversations/{conversation['id']}/messages?page=1&page_size=1"
        ).json()

        self.assertEqual(invites["total"], 1)
        self.assertEqual(conversations["total"], 1)
        self.assertEqual(history["total"], 2)
        self.assertEqual(history["items"][0]["content"], "敏感聊天正文")
        self.assertEqual(history["memory"]["summary"], "摘要内容")
        connection = self.database.connect()
        try:
            audits = connection.execute(
                "SELECT action, detail_json FROM admin_audit_events ORDER BY id"
            ).fetchall()
        finally:
            connection.close()
        self.assertIn("conversation.view", [row["action"] for row in audits])
        serialized = json.dumps([dict(row) for row in audits], ensure_ascii=False)
        self.assertNotIn("敏感聊天正文", serialized)
        self.assertNotIn(ADMIN_PASSWORD, serialized)

    def test_logout_clears_admin_session(self) -> None:
        self.login()

        response = self.client.post("/api/admin/auth/logout", headers={"Origin": ORIGIN})

        self.assertEqual(response.status_code, 204)
        self.assertFalse(self.client.get("/api/admin/auth/session").json()["authenticated"])


if __name__ == "__main__":
    unittest.main()
