"""Web Chat 的 SQLite 持久化层。

每个操作使用独立连接，便于 FastAPI 在线程池中安全调用。额度预占使用
BEGIN IMMEDIATE 保证检查与写入在同一事务内完成。
"""

import sqlite3
import time
import uuid
import json
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class QuotaDecision:
    allowed: bool
    retry_after: int = 0
    minute_remaining: int = 0
    day_remaining: int = 0


class ChatDatabase:
    """集中管理邀请码、会话、调用记录和登录尝试。"""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def initialize(self) -> None:
        with closing(self.connect()) as connection, connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS invites (
                    id TEXT PRIMARY KEY,
                    code_digest TEXT NOT NULL UNIQUE,
                    label TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    minute_limit INTEGER NOT NULL,
                    day_limit INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,
                    revoked_at INTEGER,
                    last_used_at INTEGER
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token_digest TEXT PRIMARY KEY,
                    invite_id TEXT NOT NULL REFERENCES invites(id) ON DELETE CASCADE,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    last_seen_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS sessions_invite_idx ON sessions(invite_id);

                CREATE TABLE IF NOT EXISTS usage_events (
                    request_id TEXT PRIMARY KEY,
                    invite_id TEXT NOT NULL REFERENCES invites(id) ON DELETE CASCADE,
                    mode TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    occurred_at INTEGER NOT NULL,
                    duration_ms INTEGER,
                    first_token_ms INTEGER,
                    model TEXT,
                    persona TEXT,
                    input_characters INTEGER NOT NULL DEFAULT 0,
                    output_characters INTEGER NOT NULL DEFAULT 0,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    estimated_cost_usd REAL,
                    error_code TEXT
                );
                CREATE INDEX IF NOT EXISTS usage_invite_time_idx
                    ON usage_events(invite_id, occurred_at);

                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_digest TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    occurred_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS login_attempt_time_idx
                    ON login_attempts(client_digest, occurred_at);

                CREATE TABLE IF NOT EXISTS admin_sessions (
                    token_digest TEXT PRIMARY KEY,
                    credential_fingerprint TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    last_seen_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS admin_login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_digest TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    occurred_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS admin_login_attempt_time_idx
                    ON admin_login_attempts(client_digest, occurred_at);

                CREATE TABLE IF NOT EXISTS admin_audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    target_type TEXT,
                    target_id TEXT,
                    detail_json TEXT NOT NULL DEFAULT '{}',
                    occurred_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS admin_audit_time_idx
                    ON admin_audit_events(occurred_at DESC);

                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    invite_id TEXT NOT NULL REFERENCES invites(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    persona TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS conversations_invite_updated_idx
                    ON conversations(invite_id, updated_at DESC);

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources_json TEXT,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS messages_conversation_time_idx
                    ON messages(conversation_id, created_at);

                CREATE TABLE IF NOT EXISTS conversation_memories (
                    conversation_id TEXT PRIMARY KEY
                        REFERENCES conversations(id) ON DELETE CASCADE,
                    summary TEXT NOT NULL DEFAULT '',
                    facts_json TEXT NOT NULL DEFAULT '[]',
                    decisions_json TEXT NOT NULL DEFAULT '[]',
                    open_items_json TEXT NOT NULL DEFAULT '[]',
                    summarized_through_message_id TEXT,
                    updated_at INTEGER NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS message_feedback (
                    message_id TEXT PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
                    invite_id TEXT NOT NULL REFERENCES invites(id) ON DELETE CASCADE,
                    rating INTEGER NOT NULL,
                    comment TEXT,
                    created_at INTEGER NOT NULL
                );
                """
            )
            existing_usage_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(usage_events)")
            }
            usage_migrations = {
                "first_token_ms": "INTEGER",
                "model": "TEXT",
                "persona": "TEXT",
                "input_characters": "INTEGER NOT NULL DEFAULT 0",
                "output_characters": "INTEGER NOT NULL DEFAULT 0",
                "input_tokens": "INTEGER",
                "output_tokens": "INTEGER",
                "estimated_cost_usd": "REAL",
                "error_code": "TEXT",
            }
            for column, declaration in usage_migrations.items():
                if column not in existing_usage_columns:
                    connection.execute(
                        f"ALTER TABLE usage_events ADD COLUMN {column} {declaration}"
                    )

    # 会话模块：正文与匿名指标分表保存，便于独立设置保留和访问策略。
    def create_conversation(self, invite_id: str, persona: str, title: str = "新对话") -> sqlite3.Row:
        conversation_id = uuid.uuid4().hex
        now = int(time.time())
        with closing(self.connect()) as connection, connection:
            connection.execute(
                """INSERT INTO conversations (id, invite_id, title, persona, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (conversation_id, invite_id, title, persona, now, now),
            )
        return self.get_conversation(invite_id, conversation_id)

    def get_conversation(self, invite_id: str, conversation_id: str) -> sqlite3.Row | None:
        with closing(self.connect()) as connection, connection:
            return connection.execute(
                "SELECT * FROM conversations WHERE id = ? AND invite_id = ?",
                (conversation_id, invite_id),
            ).fetchone()

    def list_conversations(self, invite_id: str) -> list[sqlite3.Row]:
        with closing(self.connect()) as connection, connection:
            return connection.execute(
                """SELECT id, title, persona, created_at, updated_at
                   FROM conversations WHERE invite_id = ? ORDER BY updated_at DESC""",
                (invite_id,),
            ).fetchall()

    def update_conversation(
        self,
        invite_id: str,
        conversation_id: str,
        *,
        title: str | None = None,
        persona: str | None = None,
    ) -> sqlite3.Row | None:
        assignments: list[str] = []
        values: list[object] = []
        if title is not None:
            assignments.append("title = ?")
            values.append(title)
        if persona is not None:
            assignments.append("persona = ?")
            values.append(persona)
        if not assignments:
            return self.get_conversation(invite_id, conversation_id)
        assignments.append("updated_at = ?")
        values.append(int(time.time()))
        values.extend((conversation_id, invite_id))
        with closing(self.connect()) as connection, connection:
            connection.execute(
                f"UPDATE conversations SET {', '.join(assignments)} WHERE id = ? AND invite_id = ?",
                values,
            )
        return self.get_conversation(invite_id, conversation_id)

    def conversation_has_messages(self, invite_id: str, conversation_id: str) -> bool:
        """判断会话是否已经产生消息，用于锁定创建时选择的人格。"""

        with closing(self.connect()) as connection, connection:
            row = connection.execute(
                """SELECT 1 FROM messages m JOIN conversations c ON c.id = m.conversation_id
                   WHERE c.id = ? AND c.invite_id = ? LIMIT 1""",
                (conversation_id, invite_id),
            ).fetchone()
        return row is not None

    def delete_conversation(self, invite_id: str, conversation_id: str) -> bool:
        with closing(self.connect()) as connection, connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE id = ? AND invite_id = ?",
                (conversation_id, invite_id),
            )
            return cursor.rowcount > 0

    def list_messages(self, invite_id: str, conversation_id: str) -> list[dict[str, object]]:
        if not self.get_conversation(invite_id, conversation_id):
            return []
        with closing(self.connect()) as connection, connection:
            rows = connection.execute(
                """SELECT m.id, m.role, m.content, m.sources_json, m.created_at,
                          f.rating AS feedback
                   FROM messages m LEFT JOIN message_feedback f ON f.message_id = m.id
                   WHERE m.conversation_id = ? ORDER BY m.created_at, m.rowid""",
                (conversation_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "role": row["role"],
                "content": row["content"],
                "sources": json.loads(row["sources_json"] or "[]"),
                "createdAt": row["created_at"],
                "feedback": row["feedback"],
            }
            for row in rows
        ]

    def append_exchange(
        self,
        invite_id: str,
        conversation_id: str,
        user_content: str,
        assistant_content: str,
        sources: list[dict[str, object]],
    ) -> tuple[dict[str, object], dict[str, object]]:
        conversation = self.get_conversation(invite_id, conversation_id)
        if not conversation:
            raise ValueError("会话不存在")
        now = int(time.time())
        user_id = uuid.uuid4().hex
        assistant_id = uuid.uuid4().hex
        title = conversation["title"]
        generated_title = user_content.strip().replace("\n", " ")[:28]
        with closing(self.connect()) as connection, connection:
            connection.execute(
                "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, 'user', ?, ?)",
                (user_id, conversation_id, user_content, now),
            )
            connection.execute(
                """INSERT INTO messages
                   (id, conversation_id, role, content, sources_json, created_at)
                   VALUES (?, ?, 'assistant', ?, ?, ?)""",
                (assistant_id, conversation_id, assistant_content, json.dumps(sources, ensure_ascii=False), now),
            )
            connection.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (generated_title if title == "新对话" and generated_title else title, now, conversation_id),
            )
        return (
            {"id": user_id, "role": "user", "content": user_content, "sources": [], "createdAt": now},
            {"id": assistant_id, "role": "assistant", "content": assistant_content, "sources": sources, "createdAt": now},
        )

    def get_conversation_memory(
        self,
        invite_id: str,
        conversation_id: str,
    ) -> dict[str, object] | None:
        """读取属于当前邀请码的结构化会话记忆。"""

        with closing(self.connect()) as connection, connection:
            row = connection.execute(
                """SELECT cm.summary, cm.facts_json, cm.decisions_json,
                          cm.open_items_json, cm.summarized_through_message_id,
                          cm.updated_at, cm.version
                   FROM conversation_memories cm
                   JOIN conversations c ON c.id = cm.conversation_id
                   WHERE cm.conversation_id = ? AND c.invite_id = ?""",
                (conversation_id, invite_id),
            ).fetchone()
        return dict(row) if row else None

    def save_conversation_memory(
        self,
        invite_id: str,
        conversation_id: str,
        *,
        summary: str,
        facts: list[str],
        decisions: list[str],
        open_items: list[str],
        summarized_through_message_id: str,
    ) -> bool:
        """仅为已验证归属的会话原子写入最新滚动摘要。"""

        if not self.get_conversation(invite_id, conversation_id):
            return False
        with closing(self.connect()) as connection, connection:
            connection.execute(
                """INSERT INTO conversation_memories
                   (conversation_id, summary, facts_json, decisions_json,
                    open_items_json, summarized_through_message_id, updated_at, version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                   ON CONFLICT(conversation_id) DO UPDATE SET
                       summary = excluded.summary,
                       facts_json = excluded.facts_json,
                       decisions_json = excluded.decisions_json,
                       open_items_json = excluded.open_items_json,
                       summarized_through_message_id = excluded.summarized_through_message_id,
                       updated_at = excluded.updated_at,
                       version = conversation_memories.version + 1""",
                (
                    conversation_id,
                    summary,
                    json.dumps(facts, ensure_ascii=False),
                    json.dumps(decisions, ensure_ascii=False),
                    json.dumps(open_items, ensure_ascii=False),
                    summarized_through_message_id,
                    int(time.time()),
                ),
            )
        return True

    def clear_conversation_memory(self, invite_id: str, conversation_id: str) -> bool:
        """清除可能已经包含被删除消息的派生记忆。"""

        with closing(self.connect()) as connection, connection:
            cursor = connection.execute(
                """DELETE FROM conversation_memories WHERE conversation_id = ?
                   AND conversation_id IN
                       (SELECT id FROM conversations WHERE invite_id = ?)""",
                (conversation_id, invite_id),
            )
            return cursor.rowcount > 0

    def delete_message(self, invite_id: str, message_id: str) -> bool:
        with closing(self.connect()) as connection, connection:
            owned = connection.execute(
                """SELECT m.conversation_id FROM messages m
                   JOIN conversations c ON c.id = m.conversation_id
                   WHERE m.id = ? AND c.invite_id = ?""",
                (message_id, invite_id),
            ).fetchone()
            if not owned:
                return False
            cursor = connection.execute(
                """DELETE FROM messages WHERE id = ? AND conversation_id IN
                   (SELECT id FROM conversations WHERE invite_id = ?)""",
                (message_id, invite_id),
            )
            if cursor.rowcount > 0:
                connection.execute(
                    "DELETE FROM conversation_memories WHERE conversation_id = ?",
                    (owned["conversation_id"],),
                )
            return cursor.rowcount > 0

    def set_feedback(
        self,
        invite_id: str,
        message_id: str,
        rating: int,
        comment: str | None,
    ) -> bool:
        with closing(self.connect()) as connection, connection:
            owned = connection.execute(
                """SELECT 1 FROM messages m JOIN conversations c ON c.id = m.conversation_id
                   WHERE m.id = ? AND c.invite_id = ? AND m.role = 'assistant'""",
                (message_id, invite_id),
            ).fetchone()
            if not owned:
                return False
            connection.execute(
                """INSERT INTO message_feedback (message_id, invite_id, rating, comment, created_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(message_id) DO UPDATE SET rating = excluded.rating,
                   comment = excluded.comment, created_at = excluded.created_at""",
                (message_id, invite_id, rating, comment, int(time.time())),
            )
            return True

    def create_invite(
        self,
        code_digest: str,
        label: str,
        minute_limit: int,
        day_limit: int,
    ) -> str:
        invite_id = uuid.uuid4().hex[:12]
        with closing(self.connect()) as connection, connection:
            connection.execute(
                """INSERT INTO invites
                   (id, code_digest, label, minute_limit, day_limit, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (invite_id, code_digest, label, minute_limit, day_limit, int(time.time())),
            )
        return invite_id

    def find_invite_by_digest(self, code_digest: str) -> sqlite3.Row | None:
        with closing(self.connect()) as connection, connection:
            return connection.execute(
                "SELECT * FROM invites WHERE code_digest = ? AND active = 1",
                (code_digest,),
            ).fetchone()

    def list_invites(self) -> list[sqlite3.Row]:
        with closing(self.connect()) as connection, connection:
            return connection.execute(
                """SELECT id, label, active, minute_limit, day_limit,
                          created_at, revoked_at, last_used_at
                   FROM invites ORDER BY created_at DESC"""
            ).fetchall()

    def set_invite_active(self, invite_id: str, active: bool) -> bool:
        now = int(time.time())
        with closing(self.connect()) as connection, connection:
            cursor = connection.execute(
                "UPDATE invites SET active = ?, revoked_at = ? WHERE id = ?",
                (int(active), None if active else now, invite_id),
            )
            if not active:
                connection.execute("DELETE FROM sessions WHERE invite_id = ?", (invite_id,))
            return cursor.rowcount > 0

    def update_invite_admin(
        self,
        invite_id: str,
        *,
        label: str | None = None,
        minute_limit: int | None = None,
        day_limit: int | None = None,
        active: bool | None = None,
    ) -> sqlite3.Row | None:
        """更新后台允许修改的邀请码字段；撤销时同步注销普通会话。"""

        assignments: list[str] = []
        values: list[object] = []
        for column, value in (
            ("label", label),
            ("minute_limit", minute_limit),
            ("day_limit", day_limit),
        ):
            if value is not None:
                assignments.append(f"{column} = ?")
                values.append(value)
        if active is not None:
            assignments.extend(("active = ?", "revoked_at = ?"))
            values.extend((int(active), None if active else int(time.time())))

        with closing(self.connect()) as connection, connection:
            if not assignments:
                return connection.execute(
                    "SELECT * FROM invites WHERE id = ?",
                    (invite_id,),
                ).fetchone()
            values.append(invite_id)
            cursor = connection.execute(
                f"UPDATE invites SET {', '.join(assignments)} WHERE id = ?",
                values,
            )
            if cursor.rowcount == 0:
                return None
            if active is False:
                connection.execute("DELETE FROM sessions WHERE invite_id = ?", (invite_id,))
            return connection.execute("SELECT * FROM invites WHERE id = ?", (invite_id,)).fetchone()

    def list_admin_invites(
        self,
        *,
        query: str = "",
        status: str = "all",
        page: int = 1,
        page_size: int = 30,
    ) -> dict[str, object]:
        """分页返回邀请码及会话、调用聚合，避免后台逐条查询。"""

        conditions: list[str] = []
        params: list[object] = []
        if query:
            conditions.append("(i.id LIKE ? OR i.label LIKE ?)")
            pattern = f"%{query}%"
            params.extend((pattern, pattern))
        if status == "active":
            conditions.append("i.active = 1")
        elif status == "revoked":
            conditions.append("i.active = 0")
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        offset = (page - 1) * page_size

        with closing(self.connect()) as connection, connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM invites i {where}",
                params,
            ).fetchone()[0]
            rows = connection.execute(
                f"""WITH conversation_totals AS (
                         SELECT invite_id, COUNT(*) AS conversation_count,
                                MAX(updated_at) AS last_chat_at
                         FROM conversations GROUP BY invite_id
                     ), usage_totals AS (
                         SELECT invite_id, COUNT(*) AS total_used,
                                COALESCE(SUM(input_tokens), 0) AS input_tokens,
                                COALESCE(SUM(output_tokens), 0) AS output_tokens,
                                COALESCE(SUM(estimated_cost_usd), 0) AS estimated_cost_usd
                         FROM usage_events GROUP BY invite_id
                     )
                     SELECT i.id, i.label, i.active, i.minute_limit, i.day_limit,
                            i.created_at, i.revoked_at, i.last_used_at,
                            COALESCE(c.conversation_count, 0) AS conversation_count,
                            c.last_chat_at, COALESCE(u.total_used, 0) AS total_used,
                            COALESCE(u.input_tokens, 0) AS input_tokens,
                            COALESCE(u.output_tokens, 0) AS output_tokens,
                            COALESCE(u.estimated_cost_usd, 0) AS estimated_cost_usd
                     FROM invites i
                     LEFT JOIN conversation_totals c ON c.invite_id = i.id
                     LEFT JOIN usage_totals u ON u.invite_id = i.id
                     {where}
                     ORDER BY COALESCE(c.last_chat_at, i.last_used_at, i.created_at) DESC
                     LIMIT ? OFFSET ?""",
                (*params, page_size, offset),
            ).fetchall()
        return {"items": [dict(row) for row in rows], "total": total}

    def list_admin_conversations(
        self,
        invite_id: str,
        *,
        page: int = 1,
        page_size: int = 30,
    ) -> dict[str, object] | None:
        """分页返回指定邀请码的同步会话。"""

        offset = (page - 1) * page_size
        with closing(self.connect()) as connection, connection:
            invite = connection.execute(
                "SELECT id, label, active FROM invites WHERE id = ?",
                (invite_id,),
            ).fetchone()
            if not invite:
                return None
            total = connection.execute(
                "SELECT COUNT(*) FROM conversations WHERE invite_id = ?",
                (invite_id,),
            ).fetchone()[0]
            rows = connection.execute(
                """SELECT c.id, c.title, c.persona, c.created_at, c.updated_at,
                          COUNT(m.id) AS message_count
                   FROM conversations c
                   LEFT JOIN messages m ON m.conversation_id = c.id
                   WHERE c.invite_id = ? GROUP BY c.id
                   ORDER BY c.updated_at DESC LIMIT ? OFFSET ?""",
                (invite_id, page_size, offset),
            ).fetchall()
        return {"invite": dict(invite), "items": [dict(row) for row in rows], "total": total}

    def get_admin_conversation_messages(
        self,
        conversation_id: str,
        *,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, object] | None:
        """分页读取任意同步会话正文及滚动摘要，供管理员只读审阅。"""

        offset = (page - 1) * page_size
        with closing(self.connect()) as connection, connection:
            conversation = connection.execute(
                """SELECT c.id, c.title, c.persona, c.created_at, c.updated_at,
                          i.id AS invite_id, i.label AS invite_label
                   FROM conversations c JOIN invites i ON i.id = c.invite_id
                   WHERE c.id = ?""",
                (conversation_id,),
            ).fetchone()
            if not conversation:
                return None
            total = connection.execute(
                "SELECT COUNT(*) FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()[0]
            rows = connection.execute(
                """SELECT m.id, m.role, m.content, m.sources_json, m.created_at,
                          f.rating AS feedback, f.comment AS feedback_comment
                   FROM messages m
                   LEFT JOIN message_feedback f ON f.message_id = m.id
                   WHERE m.conversation_id = ?
                   ORDER BY m.created_at, m.rowid LIMIT ? OFFSET ?""",
                (conversation_id, page_size, offset),
            ).fetchall()
            memory = connection.execute(
                """SELECT summary, facts_json, decisions_json, open_items_json,
                          summarized_through_message_id, updated_at
                   FROM conversation_memories WHERE conversation_id = ?""",
                (conversation_id,),
            ).fetchone()
        messages = []
        for row in rows:
            item = dict(row)
            item["sources"] = json.loads(item.pop("sources_json") or "[]")
            messages.append(item)
        memory_payload = dict(memory) if memory else None
        if memory_payload:
            for name in ("facts_json", "decisions_json", "open_items_json"):
                memory_payload[name.removesuffix("_json")] = json.loads(memory_payload.pop(name) or "[]")
        return {
            "conversation": dict(conversation),
            "memory": memory_payload,
            "items": messages,
            "total": total,
        }

    def create_session(
        self,
        token_digest: str,
        invite_id: str,
        expires_at: int,
    ) -> None:
        now = int(time.time())
        with closing(self.connect()) as connection, connection:
            connection.execute(
                """INSERT INTO sessions
                   (token_digest, invite_id, created_at, expires_at, last_seen_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (token_digest, invite_id, now, expires_at, now),
            )
            connection.execute(
                "UPDATE invites SET last_used_at = ? WHERE id = ?",
                (now, invite_id),
            )

    def get_session(self, token_digest: str, now: int | None = None) -> sqlite3.Row | None:
        current = now or int(time.time())
        with closing(self.connect()) as connection, connection:
            row = connection.execute(
                """SELECT s.token_digest, s.invite_id, s.expires_at,
                          i.minute_limit, i.day_limit
                   FROM sessions s JOIN invites i ON i.id = s.invite_id
                   WHERE s.token_digest = ? AND s.expires_at > ? AND i.active = 1""",
                (token_digest, current),
            ).fetchone()
            if row:
                connection.execute(
                    "UPDATE sessions SET last_seen_at = ? WHERE token_digest = ?",
                    (current, token_digest),
                )
            else:
                connection.execute(
                    "DELETE FROM sessions WHERE token_digest = ? OR expires_at <= ?",
                    (token_digest, current),
                )
            return row

    def delete_session(self, token_digest: str) -> None:
        with closing(self.connect()) as connection, connection:
            connection.execute("DELETE FROM sessions WHERE token_digest = ?", (token_digest,))

    def create_admin_session(
        self,
        token_digest: str,
        credential_fingerprint: str,
        expires_at: int,
    ) -> None:
        now = int(time.time())
        with closing(self.connect()) as connection, connection:
            connection.execute(
                """INSERT INTO admin_sessions
                   (token_digest, credential_fingerprint, created_at, expires_at, last_seen_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (token_digest, credential_fingerprint, now, expires_at, now),
            )

    def get_admin_session(
        self,
        token_digest: str,
        credential_fingerprint: str,
        now: int | None = None,
    ) -> sqlite3.Row | None:
        current = now or int(time.time())
        with closing(self.connect()) as connection, connection:
            row = connection.execute(
                """SELECT token_digest, expires_at FROM admin_sessions
                   WHERE token_digest = ? AND expires_at > ?
                   AND credential_fingerprint = ?""",
                (token_digest, current, credential_fingerprint),
            ).fetchone()
            if row:
                connection.execute(
                    "UPDATE admin_sessions SET last_seen_at = ? WHERE token_digest = ?",
                    (current, token_digest),
                )
            else:
                connection.execute(
                    """DELETE FROM admin_sessions WHERE token_digest = ?
                       OR expires_at <= ? OR credential_fingerprint != ?""",
                    (token_digest, current, credential_fingerprint),
                )
            return row

    def delete_admin_session(self, token_digest: str) -> None:
        with closing(self.connect()) as connection, connection:
            connection.execute("DELETE FROM admin_sessions WHERE token_digest = ?", (token_digest,))

    def admin_login_blocked(
        self,
        client_digest: str,
        limit: int,
        now: int | None = None,
    ) -> bool:
        current = now or int(time.time())
        with closing(self.connect()) as connection, connection:
            count = connection.execute(
                """SELECT COUNT(*) FROM admin_login_attempts
                   WHERE client_digest = ? AND success = 0 AND occurred_at > ?""",
                (client_digest, current - 60),
            ).fetchone()[0]
        return count >= limit

    def record_admin_login_attempt(self, client_digest: str, success: bool) -> None:
        with closing(self.connect()) as connection, connection:
            connection.execute(
                """INSERT INTO admin_login_attempts
                   (client_digest, success, occurred_at) VALUES (?, ?, ?)""",
                (client_digest, int(success), int(time.time())),
            )

    def record_admin_audit(
        self,
        action: str,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        """记录不含密码、邀请码明文和聊天正文的管理员行为。"""

        with closing(self.connect()) as connection, connection:
            connection.execute(
                """INSERT INTO admin_audit_events
                   (action, target_type, target_id, detail_json, occurred_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    action,
                    target_type,
                    target_id,
                    json.dumps(details or {}, ensure_ascii=False),
                    int(time.time()),
                ),
            )

    def login_blocked(self, client_digest: str, limit: int, now: int | None = None) -> bool:
        current = now or int(time.time())
        with closing(self.connect()) as connection, connection:
            count = connection.execute(
                """SELECT COUNT(*) FROM login_attempts
                   WHERE client_digest = ? AND success = 0 AND occurred_at > ?""",
                (client_digest, current - 60),
            ).fetchone()[0]
        return count >= limit

    def record_login_attempt(self, client_digest: str, success: bool) -> None:
        with closing(self.connect()) as connection, connection:
            connection.execute(
                "INSERT INTO login_attempts (client_digest, success, occurred_at) VALUES (?, ?, ?)",
                (client_digest, int(success), int(time.time())),
            )

    def quota_status(self, invite_id: str, minute_limit: int, day_limit: int) -> QuotaDecision:
        now = int(time.time())
        with closing(self.connect()) as connection, connection:
            minute_count = connection.execute(
                "SELECT COUNT(*) FROM usage_events WHERE invite_id = ? AND occurred_at > ?",
                (invite_id, now - 60),
            ).fetchone()[0]
            day_count = connection.execute(
                "SELECT COUNT(*) FROM usage_events WHERE invite_id = ? AND occurred_at > ?",
                (invite_id, now - 86400),
            ).fetchone()[0]
        return QuotaDecision(
            allowed=minute_count < minute_limit and day_count < day_limit,
            minute_remaining=max(0, minute_limit - minute_count),
            day_remaining=max(0, day_limit - day_count),
        )

    def reserve_usage(
        self,
        invite_id: str,
        mode: str,
        minute_limit: int,
        day_limit: int,
        *,
        model: str = "",
        persona: str = "normal",
        input_characters: int = 0,
    ) -> tuple[str | None, QuotaDecision]:
        now = int(time.time())
        request_id = uuid.uuid4().hex
        with closing(self.connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            minute_rows = connection.execute(
                "SELECT occurred_at FROM usage_events WHERE invite_id = ? AND occurred_at > ? ORDER BY occurred_at",
                (invite_id, now - 60),
            ).fetchall()
            day_rows = connection.execute(
                "SELECT occurred_at FROM usage_events WHERE invite_id = ? AND occurred_at > ? ORDER BY occurred_at",
                (invite_id, now - 86400),
            ).fetchall()
            if len(minute_rows) >= minute_limit:
                retry = max(1, minute_rows[0][0] + 60 - now)
                return None, QuotaDecision(False, retry, 0, max(0, day_limit - len(day_rows)))
            if len(day_rows) >= day_limit:
                retry = max(1, day_rows[0][0] + 86400 - now)
                return None, QuotaDecision(False, retry, max(0, minute_limit - len(minute_rows)), 0)
            connection.execute(
                """INSERT INTO usage_events
                   (request_id, invite_id, mode, outcome, occurred_at, model, persona, input_characters)
                   VALUES (?, ?, ?, 'started', ?, ?, ?, ?)""",
                (request_id, invite_id, mode, now, model, persona, input_characters),
            )
        return request_id, QuotaDecision(
            True,
            minute_remaining=minute_limit - len(minute_rows) - 1,
            day_remaining=day_limit - len(day_rows) - 1,
        )

    def finish_usage(
        self,
        request_id: str,
        outcome: str,
        duration_ms: int,
        *,
        first_token_ms: int | None = None,
        output_characters: int = 0,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        estimated_cost_usd: float | None = None,
        error_code: str | None = None,
    ) -> None:
        with closing(self.connect()) as connection, connection:
            connection.execute(
                """UPDATE usage_events SET outcome = ?, duration_ms = ?, first_token_ms = ?,
                   output_characters = ?, input_tokens = ?, output_tokens = ?,
                   estimated_cost_usd = ?, error_code = ?
                   WHERE request_id = ?""",
                (
                    outcome,
                    duration_ms,
                    first_token_ms,
                    output_characters,
                    input_tokens,
                    output_tokens,
                    estimated_cost_usd,
                    error_code,
                    request_id,
                ),
            )

    def invite_stats(self, invite_id: str) -> sqlite3.Row | None:
        now = int(time.time())
        with closing(self.connect()) as connection, connection:
            return connection.execute(
                """SELECT i.id, i.label, i.active, i.minute_limit, i.day_limit,
                          SUM(CASE WHEN u.occurred_at > ? THEN 1 ELSE 0 END) AS minute_used,
                          SUM(CASE WHEN u.occurred_at > ? THEN 1 ELSE 0 END) AS day_used,
                          COUNT(u.request_id) AS total_used,
                          SUM(CASE WHEN u.outcome = 'error' THEN 1 ELSE 0 END) AS error_count,
                          SUM(CASE WHEN u.outcome = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_count,
                          CAST(AVG(u.first_token_ms) AS INTEGER) AS average_first_token_ms,
                          CAST(AVG(u.duration_ms) AS INTEGER) AS average_duration_ms,
                          COALESCE(SUM(u.input_tokens), 0) AS input_tokens,
                          COALESCE(SUM(u.output_tokens), 0) AS output_tokens,
                          COALESCE(SUM(u.estimated_cost_usd), 0) AS estimated_cost_usd
                   FROM invites i LEFT JOIN usage_events u ON u.invite_id = i.id
                   WHERE i.id = ? GROUP BY i.id""",
                (now - 60, now - 86400, invite_id),
            ).fetchone()

    def prune_metadata(self, retention_days: int) -> None:
        cutoff = int(time.time()) - retention_days * 86400
        with closing(self.connect()) as connection, connection:
            connection.execute("DELETE FROM usage_events WHERE occurred_at < ?", (cutoff,))
            connection.execute("DELETE FROM login_attempts WHERE occurred_at < ?", (int(time.time()) - 86400,))
            connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (int(time.time()),))
            connection.execute("DELETE FROM admin_login_attempts WHERE occurred_at < ?", (int(time.time()) - 86400,))
            connection.execute("DELETE FROM admin_sessions WHERE expires_at <= ?", (int(time.time()),))
            connection.execute("DELETE FROM admin_audit_events WHERE occurred_at < ?", (cutoff,))

    def prune_conversations(self, retention_days: int) -> None:
        """删除超过正文保留期限且长期未更新的同步会话。"""

        cutoff = int(time.time()) - retention_days * 86400
        with closing(self.connect()) as connection, connection:
            connection.execute("DELETE FROM conversations WHERE updated_at < ?", (cutoff,))
