from __future__ import annotations

import json
from typing import Any, Dict


def format_sse(event: str, payload: Dict[str, Any]) -> Dict[str, str]:
    """Return a dict compatible with FastAPI EventSourceResponse."""

    return {
        "event": event,
        "data": json.dumps(payload, ensure_ascii=False),
    }
