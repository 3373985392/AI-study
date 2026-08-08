"""管理员密码哈希与独立会话凭据工具。

管理员密码只以 scrypt 哈希形式进入配置；浏览器会话仍使用随机令牌，数据库
只保存令牌 HMAC 摘要。该模块不依赖第三方密码库，便于服务器离线部署。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets


SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32


def hash_admin_password(password: str) -> str:
    """生成可放入 ``ADMIN_PASSWORD_HASH`` 的自描述 scrypt 哈希。"""

    if len(password) < 12:
        raise ValueError("管理员密码至少需要 12 个字符")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return "$".join((
        "scrypt",
        str(SCRYPT_N),
        str(SCRYPT_R),
        str(SCRYPT_P),
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    ))


def verify_admin_password(password: str, encoded_hash: str) -> bool:
    """以固定时间比较验证密码；格式损坏时安全地返回 ``False``。"""

    try:
        algorithm, raw_n, raw_r, raw_p, raw_salt, raw_digest = encoded_hash.split("$")
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(raw_salt.encode("ascii"))
        expected = base64.urlsafe_b64decode(raw_digest.encode("ascii"))
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(raw_n),
            r=int(raw_r),
            p=int(raw_p),
            dklen=len(expected),
        )
    except (ValueError, TypeError, UnicodeError):
        return False
    return hmac.compare_digest(actual, expected)


def credential_fingerprint(encoded_hash: str) -> str:
    """用于让密码轮换立即使旧管理员会话失效。"""

    return hashlib.sha256(encoded_hash.encode("utf-8")).hexdigest()


def generate_invite_code() -> str:
    """生成满足现有邀请码格式且同时包含字母和数字的高熵值。"""

    return "A1" + secrets.token_urlsafe(24)
