"""In-memory order store with deterministic data for demos and tests."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, List, Optional


@dataclass
class OrderItem:
    sku: str
    name: str
    quantity: int
    price: float


@dataclass
class Logistics:
    carrier: str
    tracking_no: str
    latest_event: str
    eta: str


@dataclass
class Order:
    order_id: str
    user_id: str
    created_at: datetime
    status: str
    total_amount: float
    currency: str = "CNY"
    items: List[OrderItem] = field(default_factory=list)
    logistics: Optional[Logistics] = None
    refund_status: str = "none"  # none | requested | completed
    invoice_email: Optional[str] = None
    invoice_issued_at: Optional[datetime] = None


class OrderStore:
    """Thread-safe mutable order store backed by a simple dictionary."""

    def __init__(self, seed_orders: Dict[str, Order]):
        self._orders = seed_orders
        self._lock = Lock()

    def get(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    def list_all(self) -> List[Order]:
        return list(self._orders.values())

    def mark_refund(self, order_id: str, reason: str) -> Order:
        with self._lock:
            order = self._orders.get(order_id)
            if not order:
                raise ValueError("订单不存在")
            if order.refund_status == "completed":
                raise ValueError("该订单已完成退款")
            order.refund_status = "requested"
            order.status = "待退款"
            return order

    def mark_invoice(self, order_id: str, email: str) -> Order:
        with self._lock:
            order = self._orders.get(order_id)
            if not order:
                raise ValueError("订单不存在")
            order.invoice_email = email
            order.invoice_issued_at = datetime.utcnow()
            return order


def _build_seed_orders() -> Dict[str, Order]:
    now = datetime.utcnow()
    return {
        "202312345": Order(
            order_id="202312345",
            user_id="u1001",
            created_at=now - timedelta(days=3),
            status="已发货",
            total_amount=488.0,
            items=[
                OrderItem(sku="SKU-1", name="智能音箱", quantity=1, price=288.0),
                OrderItem(sku="SKU-2", name="Type-C 数据线", quantity=2, price=100.0),
            ],
            logistics=Logistics(
                carrier="顺丰",
                tracking_no="SF123456789",
                latest_event="包裹已到达上海转运中心",
                eta=(now + timedelta(days=2)).strftime("%Y-%m-%d"),
            ),
        ),
        "202399999": Order(
            order_id="202399999",
            user_id="u1002",
            created_at=now - timedelta(days=10),
            status="已完成",
            total_amount=1099.0,
            items=[OrderItem(sku="SKU-3", name="蓝牙耳机", quantity=1, price=1099.0)],
            logistics=Logistics(
                carrier="京东物流",
                tracking_no="JD99887766",
                latest_event="签收完成",
                eta=(now - timedelta(days=3)).strftime("%Y-%m-%d"),
            ),
            refund_status="completed",
        ),
        "132465": Order(
            order_id="132465",
            user_id="u2001",
            created_at=now - timedelta(days=5),
            status="配送中",
            total_amount=258.0,
            items=[
                OrderItem(sku="SKU-5", name="旅行收纳包", quantity=1, price=158.0),
                OrderItem(sku="SKU-6", name="速干浴巾", quantity=1, price=100.0),
            ],
            logistics=Logistics(
                carrier="菜鸟裹裹",
                tracking_no="CN135792468",
                latest_event="包裹已从杭州发出，正在运往目的地",
                eta=(now + timedelta(days=1)).strftime("%Y-%m-%d"),
            ),
        ),
    }


ORDER_STORE = OrderStore(_build_seed_orders())
