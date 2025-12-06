import pytest
from fastapi.testclient import TestClient

from smart_customer_service.app import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_invoice_plugin_flow(client):
    payload = {
        "session_id": "invoice-session",
        "message": "我要给订单202312345开具发票，发送到test@example.com",
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "发票" in data["reply"]
    assert any(event["tool"] == "invoice.issue" for event in data["tool_events"])
