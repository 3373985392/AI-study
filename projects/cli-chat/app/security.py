"""邀请码、会话令牌和客户端地址的安全摘要工具。"""

import hashlib
import hmac
import re
import secrets


INVITE_CODE_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9_-]{16,64}$")


def validate_invite_code(code: str) -> str:
    """校验长期邀请码强度，并返回未经改写的原值。"""

    if not INVITE_CODE_PATTERN.fullmatch(code):
        raise ValueError("邀请码必须为 16–64 位，并同时包含字母和数字")
    return code


def secret_digest(pepper: str, value: str) -> str:
    """使用服务端 Pepper 生成可索引但不可直接还原的摘要。"""

    return hmac.new(
        pepper.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_session_token() -> str:
    """创建具有足够熵的浏览器会话令牌。"""

    return secrets.token_urlsafe(32)

