from __future__ import annotations

import asyncio
import os
from typing import Dict, List

from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

from common import PromptLibrary, build_llm, format_sse

app = FastAPI(title="Polish MCP Service", version="0.1.0")

MODEL_NAME = os.getenv("MODEL_NAME", "qwen-plus")
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

prompt_library = PromptLibrary(build_llm(MODEL_NAME, mock=MOCK_MODE))


class PolishPayload(BaseModel):
    tone: str
    audience: str
    draft: str
    actions: List[str]


def run_polish(payload: PolishPayload) -> Dict[str, str]:
    final_article = prompt_library.polish_chain.invoke(
        {
            "tone": payload.tone,
            "audience": payload.audience,
            "draft": payload.draft,
            "actions": "\n".join(payload.actions),
        }
    )
    return {"final_article": final_article}


@app.post("/events")
async def run_polish_events(payload: PolishPayload) -> EventSourceResponse:
    async def event_stream():
        yield format_sse("log", {"agent": "polish", "message": "润色终稿"})
        result = await asyncio.to_thread(run_polish, payload)
        yield format_sse("payload", result)
        yield format_sse("result", result)

    return EventSourceResponse(event_stream())


@app.get("/healthz")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}
