"""Invoice plugin implementation."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from .base import BasePlugin, PluginMetadata
from ..orders import OrderStore, ORDER_STORE


class InvoicePlugin(BasePlugin):
    def __init__(self, store: OrderStore | None = None):
        self.store = store or ORDER_STORE
        self.metadata = PluginMetadata(
            name="invoice",
            version="1.0.0",
            description="提供电子发票开具能力",
            capabilities=["invoice.issue"],
        )

    def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        order_id = payload.get("order_id")
        email = payload.get("email")
        if not order_id or not email:
            raise ValueError("发票插件需要 order_id 和 email")
        order = self.store.mark_invoice(order_id, email)
        invoice_no = f"INV-{order.order_id}-{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        return {
            "invoice_no": invoice_no,
            "order_id": order.order_id,
            "email": email,
            "issued_at": order.invoice_issued_at.isoformat() if order.invoice_issued_at else None,
            "download_url": f"https://invoice.example.com/{invoice_no}"
        }


def build_plugin(**deps) -> BasePlugin:
    store = deps.get("order_store")
    return InvoicePlugin(store=store)
