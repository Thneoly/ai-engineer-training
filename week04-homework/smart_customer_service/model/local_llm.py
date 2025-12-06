"""Deterministic chat model to keep the homework self-contained."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class DeterministicChatModel(BaseChatModel):
    model_name: str = "rule-based"
    system_prompt: str
    style: str = "balanced"
    timezone: str = "Asia/Shanghai"

    @property
    def _llm_type(self) -> str:
        return "deterministic-rule"

    def _generate(self, messages: List[BaseMessage], stop: List[str] | None = None, **kwargs: Any) -> ChatResult:
        reply = self._respond(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=reply))])

    def _respond(self, messages: List[BaseMessage]) -> str:
        last = messages[-1]
        text = last.content if isinstance(last, HumanMessage) else str(last.content)
        lowered = text.lower()
        if "昨天" in text or "yesterday" in lowered:
            ask_time = datetime.utcnow() + timedelta(hours=self._tz_offset())
            date_str = (ask_time - timedelta(days=1)).strftime("%Y-%m-%d")
            if self._english_mode():
                return f"'Yesterday' refers to {date_str}. I can keep helping you with the order."
            return f"您说的“昨天”是 {date_str}，我可以帮您继续查询订单。"
        if any(keyword in lowered for keyword in ["hello", "hi"]):
            return self._format("Hello! I'm here if you need anything.")
        if any(keyword in text for keyword in ["你好", "您好"]):
            return self._format("您好，我在这里，随时可以为您服务。")
        return self._format(self._default_ack())

    def _format(self, text: str) -> str:
        if self.style == "warm":
            suffix = (
                " If you need anything else, just let me know!"
                if self._english_mode()
                else " 如果还有其他疑问，也欢迎随时告诉我哦。"
            )
            return f"{text}{suffix}"
        if self.style == "concise":
            return text
        return text

    def _default_ack(self) -> str:
        if self._english_mode():
            return "Got it, I'll handle that for you."
        return "已经收到您的问题，我会尽快为您查阅相关信息。"

    def _tz_offset(self) -> int:
        # Very small helper: map timezone name to offset hours (only a few cases needed)
        mapping = {
            "Asia/Shanghai": 8,
            "UTC": 0,
        }
        return mapping.get(self.timezone, 8)

    def _english_mode(self) -> bool:
        return any("a" <= ch.lower() <= "z" for ch in self.system_prompt if ch.isalpha())
