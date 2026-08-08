"""Web Chat 的运行配置。

所有敏感值只从环境变量读取；本模块不提供可用于生产的默认密钥。
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _parse_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class WebSettings:
    """认证、数据库和限额相关的不可变配置。"""

    database_path: Path
    invite_code_pepper: str
    session_token_pepper: str
    cookie_secure: bool = False
    allowed_origins: tuple[str, ...] = ("http://localhost:5173",)
    session_days: int = 30
    minute_limit: int = 5
    day_limit: int = 50
    login_attempt_limit: int = 5
    metadata_retention_days: int = 90
    conversation_retention_days: int = 365
    sse_heartbeat_seconds: float = 15.0
    input_price_per_million: float = 0.0
    output_price_per_million: float = 0.0
    admin_password_hash: str = ""
    admin_session_token_pepper: str = ""
    admin_session_hours: int = 8
    admin_login_attempt_limit: int = 5


def load_web_settings() -> WebSettings:
    """加载 Web 配置并在启动阶段报告不安全或缺失的设置。"""

    load_dotenv(REPOSITORY_ROOT / ".env")
    # 生产 systemd 使用的环境文件也供手动邀请码管理命令复用。
    production_env = Path(os.getenv("CHAT_ENV_FILE", "/etc/ai-study/chat.env"))
    if production_env.exists():
        load_dotenv(production_env)
    database_path = Path(
        os.getenv(
            "CHAT_DATABASE_PATH",
            str(REPOSITORY_ROOT / "projects" / "cli-chat" / "data" / "chat.sqlite3"),
        )
    ).expanduser()
    if not database_path.is_absolute():
        database_path = REPOSITORY_ROOT / database_path
    invite_pepper = os.getenv("INVITE_CODE_PEPPER", "")
    session_pepper = os.getenv("SESSION_TOKEN_PEPPER", "")
    admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
    admin_session_pepper = os.getenv("ADMIN_SESSION_TOKEN_PEPPER", "")

    missing = [
        name
        for name, value in (
            ("INVITE_CODE_PEPPER", invite_pepper),
            ("SESSION_TOKEN_PEPPER", session_pepper),
            ("ADMIN_PASSWORD_HASH", admin_password_hash),
            ("ADMIN_SESSION_TOKEN_PEPPER", admin_session_pepper),
        )
        if (
            (name == "ADMIN_PASSWORD_HASH" and not value.startswith("scrypt$"))
            or (name != "ADMIN_PASSWORD_HASH" and len(value) < 32)
            or value.startswith("replace-with")
        )
    ]
    if missing:
        raise RuntimeError(f"以下密钥缺失或少于 32 个字符: {', '.join(missing)}")

    origins = tuple(
        origin.strip().rstrip("/")
        for origin in os.getenv(
            "CHAT_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    )

    return WebSettings(
        database_path=database_path,
        invite_code_pepper=invite_pepper,
        session_token_pepper=session_pepper,
        cookie_secure=_parse_bool("CHAT_COOKIE_SECURE", False),
        allowed_origins=origins,
        session_days=int(os.getenv("CHAT_SESSION_DAYS", "30")),
        minute_limit=int(os.getenv("CHAT_MINUTE_LIMIT", "5")),
        day_limit=int(os.getenv("CHAT_DAY_LIMIT", "50")),
        login_attempt_limit=int(os.getenv("CHAT_LOGIN_ATTEMPT_LIMIT", "5")),
        metadata_retention_days=int(os.getenv("CHAT_METADATA_RETENTION_DAYS", "90")),
        conversation_retention_days=int(os.getenv("CHAT_CONVERSATION_RETENTION_DAYS", "365")),
        sse_heartbeat_seconds=float(os.getenv("CHAT_SSE_HEARTBEAT_SECONDS", "15")),
        input_price_per_million=float(os.getenv("LLM_INPUT_PRICE_PER_MILLION", "0")),
        output_price_per_million=float(os.getenv("LLM_OUTPUT_PRICE_PER_MILLION", "0")),
        admin_password_hash=admin_password_hash,
        admin_session_token_pepper=admin_session_pepper,
        admin_session_hours=int(os.getenv("ADMIN_SESSION_HOURS", "8")),
        admin_login_attempt_limit=int(os.getenv("ADMIN_LOGIN_ATTEMPT_LIMIT", "5")),
    )
