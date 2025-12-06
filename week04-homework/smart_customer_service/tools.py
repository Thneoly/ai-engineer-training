"""Domain tools that LangGraph nodes can call."""
from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Any, Optional

from langchain_core.messages import AIMessage

from .orders import OrderStore, ORDER_STORE, Order


class OrderTools:
    """Encapsulates domain actions such as querying order status and refunding."""

    def __init__(self, store: OrderStore | None = None):
        self.store = store or ORDER_STORE

    def query_order(self, order_id: str) -> Dict[str, Any]:
        order = self._require_order(order_id)
        data = asdict(order)
        # datetime values are not JSON serializable by default
        data["created_at"] = order.created_at.isoformat()
        if order.invoice_issued_at:
            data["invoice_issued_at"] = order.invoice_issued_at.isoformat()
        return data

    def summarize_order(self, order_id: str) -> str:
        order = self._require_order(order_id)
        parts = [
            f"订单 {order.order_id} 当前状态：{order.status}，总金额 {order.total_amount}{order.currency}。",
        ]
        if order.logistics:
            parts.append(
                f"物流由 {order.logistics.carrier} 承运，运单号 {order.logistics.tracking_no}，"
                f"最新进展：{order.logistics.latest_event}，预计送达 {order.logistics.eta}."
            )
        if order.refund_status == "requested":
            parts.append("系统显示该订单已提交退款申请，正在审核中。")
        elif order.refund_status == "completed":
            parts.append("该订单已完成退款，资金将在1-3个工作日原路退回。")
        return " ".join(parts)

    def request_refund(self, order_id: str, reason: str) -> str:
        order = self.store.mark_refund(order_id, reason)
        return (
            f"已经为订单 {order.order_id} 提交退款申请，原因：{reason}。"
            "审核通过后将以短信与邮件通知您，届时退款会原路退回。"
        )

    def _require_order(self, order_id: str) -> Order:
        order = self.store.get(order_id)
        if not order:
            raise ValueError("未找到对应订单，请确认订单号是否正确。")
        return order


def build_tool_message(content: str) -> AIMessage:
    """Helper to convert tool response into LangChain message."""

    return AIMessage(content=content)
