"""Web Chat 的 SQLite 持久化层。

每个操作使用独立连接，便于 FastAPI 在线程池中安全调用。额度预占使用
BEGIN IMMEDIATE 保证检查与写入在同一事务内完成。
"""

import sqlite3
import time
import uuid
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
                    duration_ms INTEGER
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
                """
            )

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
                   (request_id, invite_id, mode, outcome, occurred_at)
                   VALUES (?, ?, ?, 'started', ?)""",
                (request_id, invite_id, mode, now),
            )
        return request_id, QuotaDecision(
            True,
            minute_remaining=minute_limit - len(minute_rows) - 1,
            day_remaining=day_limit - len(day_rows) - 1,
        )

    def finish_usage(self, request_id: str, outcome: str, duration_ms: int) -> None:
        with closing(self.connect()) as connection, connection:
            connection.execute(
                "UPDATE usage_events SET outcome = ?, duration_ms = ? WHERE request_id = ?",
                (outcome, duration_ms, request_id),
            )

    def invite_stats(self, invite_id: str) -> sqlite3.Row | None:
        now = int(time.time())
        with closing(self.connect()) as connection, connection:
            return connection.execute(
                """SELECT i.id, i.label, i.active, i.minute_limit, i.day_limit,
                          SUM(CASE WHEN u.occurred_at > ? THEN 1 ELSE 0 END) AS minute_used,
                          SUM(CASE WHEN u.occurred_at > ? THEN 1 ELSE 0 END) AS day_used,
                          COUNT(u.request_id) AS total_used
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
