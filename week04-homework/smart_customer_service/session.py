"""Simple in-memory session store for multi-turn conversations."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, MutableMapping

from langchain_core.messages import BaseMessage


@dataclass
class SessionState:
    session_id: str
    messages: list[BaseMessage] = field(default_factory=list)
    context: Dict[str, str] = field(default_factory=dict)
    slots: Dict[str, str] = field(default_factory=dict)
    pending_intent: str | None = None
    pending_slot: str | None = None
    intent: str | None = None
    tool_events: list[dict] = field(default_factory=list)


class SessionStore:
    def __init__(self):
        self._data: MutableMapping[str, SessionState] = {}
        self._lock = Lock()

    def get(self, session_id: str) -> SessionState | None:
        with self._lock:
            state = self._data.get(session_id)
            return deepcopy(state) if state else None

    def save(self, state: SessionState) -> None:
        with self._lock:
            self._data[state.session_id] = deepcopy(state)

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._data.pop(session_id, None)

    def reset(self):
        with self._lock:
            self._data.clear()
