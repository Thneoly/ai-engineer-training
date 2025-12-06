"""FastAPI application exposing the smart customer service runtime."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import get_settings
from .runtime import ServiceRuntime


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: str | None
    slots: dict
    tool_events: list


class ReloadModelRequest(BaseModel):
    system_prompt: str | None = None
    style: str | None = None
    provider: str | None = None
    dashscope_model: str | None = None
    temperature: float | None = None


runtime: ServiceRuntime | None = None


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    global runtime
    runtime = ServiceRuntime(settings)

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "plugins": runtime.plugin_manager.plugins,
            "llm_provider": runtime.settings.llm_provider,
        }

    @app.post("/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest):
        try:
            result = runtime.process(payload.session_id, payload.message)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return ChatResponse(
            session_id=result.session_id,
            reply=result.reply,
            intent=result.intent,
            slots=result.slot_state,
            tool_events=result.tool_events,
        )

    @app.post("/reload/model")
    async def reload_model(payload: ReloadModelRequest):
        runtime.reload_model(
            system_prompt=payload.system_prompt,
            style=payload.style,
            provider=payload.provider,
            dashscope_model=payload.dashscope_model,
            temperature=payload.temperature,
        )
        return {
            "status": "reloaded",
            "style": runtime.settings.model_style,
            "provider": runtime.settings.llm_provider,
        }

    @app.post("/reload/plugins")
    async def reload_plugins():
        runtime.reload_plugins()
        return {"status": "reloaded", "plugins": runtime.plugin_manager.plugins}

    return app
