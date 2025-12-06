"""Intent router and slot extraction helpers."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


ORDER_ID_PATTERN = re.compile(r"(?<!\d)(20\d{7,}|\d{6,})(?!\d)")
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


@dataclass
class RouteResult:
    intent: str
    required_slot: Optional[str] = None


class IntentRouter:
    def detect(self, text: str, pending_slot: Optional[str] = None, pending_intent: Optional[str] = None) -> RouteResult:
        text_lower = text.lower()
        if pending_slot and pending_intent:
            return RouteResult(intent=pending_intent, required_slot=None)
        if any(keyword in text_lower for keyword in ["发票", "开票"]):
            if not self.extract_order_id(text):
                return RouteResult(intent="invoice", required_slot="order_id")
            if not self.extract_email(text):
                return RouteResult(intent="invoice", required_slot="email")
            return RouteResult(intent="invoice")
        if any(keyword in text_lower for keyword in ["退款", "退货", "退钱"]):
            return RouteResult(intent="refund", required_slot=self._slot_if_missing(text))
        if any(keyword in text_lower for keyword in ["查订单", "订单", "物流"]):
            return RouteResult(intent="order", required_slot=self._slot_if_missing(text))
        return RouteResult(intent="general")

    def _slot_if_missing(self, text: str) -> Optional[str]:
        if not ORDER_ID_PATTERN.search(text):
            return "order_id"
        return None

    def extract_order_id(self, text: str) -> Optional[str]:
        match = ORDER_ID_PATTERN.search(text)
        return match.group(1) if match else None

    def extract_email(self, text: str) -> Optional[str]:
        match = EMAIL_PATTERN.search(text)
        return match.group(0) if match else None
