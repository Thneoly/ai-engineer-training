from fastapi.testclient import TestClient

from smart_customer_service.app import create_app


def test_model_reload_keeps_old_session():
    app = create_app()
    client = TestClient(app)

    # Start a session and leave it pending order id
    resp = client.post("/chat", json={"session_id": "s1", "message": "查订单"})
    assert resp.status_code == 200
    first_reply = resp.json()["reply"]
    assert "订单号" in first_reply

    # Reload model with a different style
    resp_reload = client.post("/reload/model", json={"style": "concise", "system_prompt": "You are an English agent."})
    assert resp_reload.status_code == 200

    # Old session should still be waiting for order id prompt (Chinese text)
    resp = client.post("/chat", json={"session_id": "s1", "message": "你好"})
    assert "订单号" in resp.json()["reply"]

    # New session picks up new persona (English concise)
    resp_new = client.post("/chat", json={"session_id": "s2", "message": "hello"})
    assert resp_new.json()["reply"].startswith("You") or "hello" in resp_new.json()["reply"].lower()
