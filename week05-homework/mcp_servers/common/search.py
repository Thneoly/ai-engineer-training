from __future__ import annotations

from typing import Dict, List

from ddgs import DDGS


class DuckDuckGoSearchTool:
    """Simple wrapper around ddgs to fetch Chinese web snippets."""

    def __init__(self, *, max_results: int = 4, region: str = "cn-zh", timelimit: str | None = None) -> None:
        self.max_results = max_results
        self.region = region
        self.timelimit = timelimit

    def search(self, query: str) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        try:
            with DDGS(timeout=10) as client:
                for hit in client.text(
                    query,
                    max_results=self.max_results,
                    region=self.region,
                    timelimit=self.timelimit,
                ):
                    rows.append(
                        {
                            "title": hit.get("title", ""),
                            "snippet": hit.get("body", ""),
                            "url": hit.get("href") or hit.get("url", ""),
                        }
                    )
        except Exception as exc:  # pragma: no cover - network failure best-effort
            rows.append(
                {
                    "title": "DuckDuckGo 查询失败",
                    "snippet": str(exc),
                    "url": "",
                }
            )
        return rows or [
            {
                "title": "未获取到搜索结果",
                "snippet": "请稍后重试或更换关键词",
                "url": "",
            }
        ]
