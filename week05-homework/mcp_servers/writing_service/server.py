from __future__ import annotations

import asyncio
import os
from typing import Dict

from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

from common import PromptLibrary, build_llm, format_sse

app = FastAPI(title="Writing MCP Service", version="0.1.0")

MODEL_NAME = os.getenv("MODEL_NAME", "qwen-plus")
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

prompt_library = PromptLibrary(build_llm(MODEL_NAME, mock=MOCK_MODE))


class WritingPayload(BaseModel):
    tone: str
    length: str
    summary: str


def build_draft(payload: WritingPayload) -> Dict[str, str]:
    draft = prompt_library.writing_chain.invoke(
        {
            "tone": payload.tone,
            "length": payload.length,
            "summary": payload.summary,
        }
    )
    return {"draft": draft}


@app.post("/events")
async def run_writing_events(payload: WritingPayload) -> EventSourceResponse:
    async def event_stream():
        yield format_sse("log", {"agent": "writing", "message": "撰写初稿"})
        result = await asyncio.to_thread(build_draft, payload)
        yield format_sse("payload", result)
        yield format_sse("result", result)

    return EventSourceResponse(event_stream())


@app.get("/healthz")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}
