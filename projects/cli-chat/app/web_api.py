"""邀请码保护的 FastAPI Web Chat 接口。"""

import json
import logging
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from starlette.background import BackgroundTask
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from app.chat_service import ChatService
from app.database import ChatDatabase
from app.security import create_session_token, secret_digest
from app.web_settings import WebSettings, load_web_settings


COOKIE_NAME = "ai_chat_session"
logger = logging.getLogger(__name__)


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12_000)

    @field_validator("content")
    @classmethod
    def reject_blank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("消息内容不能为空")
        return value


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4_000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=20)
    mode: Literal["chat", "rag"] = "chat"
    persona: Literal["brat", "normal"] = "normal"

    @field_validator("message")
    @classmethod
    def reject_blank_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("问题不能为空")
        return value

    @model_validator(mode="after")
    def validate_history_size(self) -> "ChatRequest":
        if sum(len(item.content) for item in self.history) > 40_000:
            raise ValueError("历史消息总长度不能超过 40000 个字符")
        return self


class RedeemRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)


@dataclass(frozen=True)
class AuthContext:
    token_digest: str
    invite_id: str
    expires_at: int
    minute_limit: int
    day_limit: int


class ActiveRequestRegistry:
    """单进程内限制每个邀请码同时只进行一个流式请求。"""

    def __init__(self) -> None:
        self._active: set[str] = set()
        self._lock = threading.Lock()

    def acquire(self, invite_id: str) -> bool:
        with self._lock:
            if invite_id in self._active:
                return False
            self._active.add(invite_id)
            return True

    def release(self, invite_id: str) -> None:
        with self._lock:
            self._active.discard(invite_id)


def sse_event(event: str, payload: dict[str, object]) -> str:
    """生成不会破坏中文和换行内容的标准 SSE 事件。"""

    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"


def create_app(
    settings: WebSettings | None = None,
    database: ChatDatabase | None = None,
    chat_service: ChatService | None = None,
) -> FastAPI:
    """创建应用；依赖可注入，便于测试时完全隔离真实模型和数据库。"""

    resolved_settings = settings or load_web_settings()
    resolved_database = database or ChatDatabase(resolved_settings.database_path)
    resolved_chat_service = chat_service or ChatService.from_environment()
    resolved_database.prune_metadata(resolved_settings.metadata_retention_days)
    registry = ActiveRequestRegistry()

    app = FastAPI(title="AI Study Web Chat", docs_url=None, redoc_url=None)

    def ensure_origin(request: Request) -> None:
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") not in resolved_settings.allowed_origins:
            raise HTTPException(status_code=403, detail="请求来源不受信任")

    def get_auth(request: Request) -> AuthContext | None:
        token = request.cookies.get(COOKIE_NAME)
        if not token:
            return None
        digest = secret_digest(resolved_settings.session_token_pepper, token)
        row = resolved_database.get_session(digest)
        if not row:
            return None
        return AuthContext(
            token_digest=digest,
            invite_id=row["invite_id"],
            expires_at=row["expires_at"],
            minute_limit=row["minute_limit"],
            day_limit=row["day_limit"],
        )

    def require_auth(request: Request) -> AuthContext:
        auth = get_auth(request)
        if not auth:
            raise HTTPException(status_code=401, detail="请先输入有效邀请码")
        return auth

    def auth_payload(auth: AuthContext) -> dict[str, object]:
        quota = resolved_database.quota_status(
            auth.invite_id,
            auth.minute_limit,
            auth.day_limit,
        )
        return {
            "authenticated": True,
            "viewerId": auth.invite_id,
            "expiresAt": auth.expires_at,
            "limits": {
                "minute": auth.minute_limit,
                "day": auth.day_limit,
                "minuteRemaining": quota.minute_remaining,
                "dayRemaining": quota.day_remaining,
            },
        }

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/auth/session")
    def session_state(request: Request) -> dict[str, object]:
        auth = get_auth(request)
        return auth_payload(auth) if auth else {"authenticated": False}

    @app.post("/api/auth/redeem")
    def redeem(payload: RedeemRequest, request: Request) -> JSONResponse:
        ensure_origin(request)
        client_host = request.client.host if request.client else "unknown"
        client_digest = secret_digest(resolved_settings.session_token_pepper, client_host)
        if resolved_database.login_blocked(
            client_digest,
            resolved_settings.login_attempt_limit,
        ):
            raise HTTPException(
                status_code=429,
                detail="尝试次数过多，请稍后再试",
                headers={"Retry-After": "60"},
            )

        code_digest = secret_digest(resolved_settings.invite_code_pepper, payload.code)
        invite = resolved_database.find_invite_by_digest(code_digest)
        resolved_database.record_login_attempt(client_digest, invite is not None)
        if not invite:
            raise HTTPException(status_code=401, detail="邀请码无效或已停用")

        token = create_session_token()
        token_digest = secret_digest(resolved_settings.session_token_pepper, token)
        expires_at = int(time.time()) + resolved_settings.session_days * 86400
        resolved_database.create_session(token_digest, invite["id"], expires_at)
        auth = AuthContext(
            token_digest,
            invite["id"],
            expires_at,
            invite["minute_limit"],
            invite["day_limit"],
        )
        response = JSONResponse(auth_payload(auth))
        response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=resolved_settings.session_days * 86400,
            httponly=True,
            secure=resolved_settings.cookie_secure,
            samesite="strict",
            path="/",
        )
        return response

    @app.post("/api/auth/logout", status_code=204)
    def logout(request: Request) -> Response:
        ensure_origin(request)
        auth = get_auth(request)
        if auth:
            resolved_database.delete_session(auth.token_digest)
        response = Response(status_code=204)
        response.delete_cookie(
            COOKIE_NAME,
            path="/",
            secure=resolved_settings.cookie_secure,
            httponly=True,
            samesite="strict",
        )
        return response

    @app.post("/api/chat/stream")
    def stream_chat(payload: ChatRequest, request: Request) -> StreamingResponse:
        ensure_origin(request)
        auth = require_auth(request)
        if not registry.acquire(auth.invite_id):
            raise HTTPException(status_code=409, detail="已有回答正在生成")

        request_id, quota = resolved_database.reserve_usage(
            auth.invite_id,
            payload.mode,
            auth.minute_limit,
            auth.day_limit,
        )
        if not request_id:
            registry.release(auth.invite_id)
            raise HTTPException(
                status_code=429,
                detail="当前邀请码的使用额度已用完",
                headers={"Retry-After": str(quota.retry_after)},
            )

        history = [item.model_dump() for item in payload.history]

        def generate() -> Iterator[str]:
            started = time.monotonic()
            outcome = "success"
            try:
                for token in resolved_chat_service.stream_reply(
                    payload.message,
                    history,
                    rag_enabled=payload.mode == "rag",
                    persona_id=payload.persona,
                ):
                    yield sse_event("token", {"text": token})
                yield sse_event("done", {"requestId": request_id})
            except GeneratorExit:
                outcome = "cancelled"
                raise
            except Exception as error:
                outcome = "error"
                logger.warning(
                    "chat request %s failed with %s",
                    request_id,
                    type(error).__name__,
                )
                yield sse_event(
                    "error",
                    {"code": "upstream_error", "message": "模型服务暂时不可用，请稍后重试"},
                )
            finally:
                duration_ms = int((time.monotonic() - started) * 1000)
                resolved_database.finish_usage(request_id, outcome, duration_ms)
                registry.release(auth.invite_id)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            # 即使客户端在生成器第一次迭代前断开，也释放该邀请码的并发锁。
            background=BackgroundTask(registry.release, auth.invite_id),
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
            },
        )

    return app
