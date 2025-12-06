from __future__ import annotations

import asyncio
import json
import os
from typing import Dict

from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

from common import DuckDuckGoSearchTool, PromptLibrary, build_llm, format_sse

app = FastAPI(title="Research MCP Service", version="0.1.0")

MODEL_NAME = os.getenv("MODEL_NAME", "qwen-plus")
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

prompt_library = PromptLibrary(build_llm(MODEL_NAME, mock=MOCK_MODE))
search_tool = DuckDuckGoSearchTool()


class ResearchPayload(BaseModel):
    question: str
    tone: str
    length: str


def safe_json(payload: str, fallback: Dict[str, str | list]) -> Dict[str, str | list]:
    try:
        data = json.loads(payload)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    result = dict(fallback)
    result["raw"] = payload
    return result


def build_research_package(body: ResearchPayload) -> Dict[str, object]:
    search_results = search_tool.search(body.question)
    search_summary = "\n".join(
        f"- {item['title']}（{item['url']}）: {item['snippet']}".strip()
        for item in search_results
        if item.get("title") or item.get("snippet")
    ) or "(检索结果为空)"
    raw = prompt_library.research_chain.invoke(
        {
            "question": body.question,
            "tone": body.tone,
            "length": body.length,
            "search_summary": search_summary,
        }
    )
    research = safe_json(
        raw,
        {
            "outline": ["引言", "应用场景", "落地策略"],
            "bullet_points": ["默认要点"],
            "citations": [],
            "insight": "",
        },
    )
    return {
        "research": research,
        "search_results": search_results,
    }


@app.post("/events")
async def run_research_events(payload: ResearchPayload) -> EventSourceResponse:
    async def event_stream():
        yield format_sse("log", {"agent": "research", "message": "开始检索"})
        result = await asyncio.to_thread(build_research_package, payload)
        yield format_sse("payload", result)
        yield format_sse("result", result)

    return EventSourceResponse(event_stream())


@app.get("/healthz")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}
