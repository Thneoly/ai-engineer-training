from __future__ import annotations

import asyncio
import json
import os
from typing import Dict

from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

from common import PromptLibrary, build_llm, format_sse

app = FastAPI(title="Review MCP Service", version="0.1.0")

MODEL_NAME = os.getenv("MODEL_NAME", "qwen-plus")
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

prompt_library = PromptLibrary(build_llm(MODEL_NAME, mock=MOCK_MODE))


class ReviewPayload(BaseModel):
    draft: str


def safe_json(payload: str, fallback: Dict[str, object]) -> Dict[str, object]:
    try:
        data = json.loads(payload)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    merged = dict(fallback)
    merged["raw"] = payload
    return merged


def run_review(payload: ReviewPayload) -> Dict[str, object]:
    retry_log: list[str] = []
    primary_raw = prompt_library.review_chain.invoke({"draft": payload.draft})
    review = safe_json(
        primary_raw,
        {
            "status": "needs_revision",
            "issues": ["缺少结构化引用"],
            "actions": ["补充引用"],
            "summary": "默认审核结果",
        },
    )
    if review.get("status") != "approved":
        retry_log.append("一级审核未通过，启动高级审核")
        senior_raw = prompt_library.senior_chain.invoke(
            {"draft": payload.draft, "issues": "; ".join(review.get("issues", []))}
        )
        senior = safe_json(
            senior_raw,
            {
                "status": "approved",
                "actions": review.get("actions", []),
                "summary": "高级审核补充说明",
                "compliance_notes": "",
            },
        )
        senior["escalated_from"] = review
        review = senior
    return {"review": review, "retry_log": retry_log}


@app.post("/events")
async def run_review_events(payload: ReviewPayload) -> EventSourceResponse:
    async def event_stream():
        yield format_sse("log", {"agent": "review", "message": "执行审核"})
        result = await asyncio.to_thread(run_review, payload)
        if result["retry_log"]:
            yield format_sse("log", {"agent": "review", "message": result["retry_log"][0]})
        yield format_sse("payload", result)
        yield format_sse("result", result)

    return EventSourceResponse(event_stream())


@app.get("/healthz")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}
