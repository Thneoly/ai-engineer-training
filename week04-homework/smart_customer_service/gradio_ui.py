"""Gradio front-end for the smart customer service backend."""
from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
import httpx

API_BASE = os.getenv("SMART_CS_GRADIO_BACKEND", "http://127.0.0.1:8000")
GRADIO_HOST = os.getenv("SMART_CS_GRADIO_HOST", "0.0.0.0")
GRADIO_PORT = int(os.getenv("SMART_CS_GRADIO_PORT", "7860"))
TIMEOUT = float(os.getenv("SMART_CS_GRADIO_TIMEOUT", "30"))
PLACEHOLDER = "..."


def _format_message(role: str, text: str) -> Dict[str, Any]:
    return {
        "role": role,
        "content": [
            {
                "type": "text",
                "text": text,
            }
        ],
    }


def _extract_text(message: Dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and "text" in block:
                return str(block["text"])
    elif isinstance(content, str):
        return content
    return ""


def _ensure_session(session_id: str | None) -> str:
    return session_id or str(uuid.uuid4())


def _call_backend(message: str, session_id: str) -> Tuple[str, str]:
    try:
        response = httpx.post(
            f"{API_BASE}/chat",
            json={"session_id": session_id, "message": message},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("reply", "(后端未返回 reply 字段)"), data.get("session_id", session_id)
    except Exception as exc:  # noqa: BLE001
        return f"调用后端失败：{exc}", session_id


def _system_message() -> str:
    return (
        "🧠 **智能客服演示**\n\n"
        "左侧输入问题（如“查订单”“申请退款”），系统会通过 LangGraph 与工具完成查询。"
    )


def build_interface() -> gr.Blocks:
    with gr.Blocks(title="Smart Customer Service") as demo:
        gr.Markdown(_system_message())
        chatbot = gr.Chatbot(height=400)
        session_state = gr.State(str(uuid.uuid4()))
        user_box = gr.Textbox(label="输入您的问题", placeholder="例如：查订单202312345的物流", lines=2)
        send_btn = gr.Button("发送", variant="primary")
        clear_btn = gr.Button("清空对话", variant="secondary")

        def user_submit(message: str, history: Optional[List[Dict[str, Any]]]) -> Tuple[str, List[Dict[str, Any]]]:
            history = history or []
            if not message.strip():
                return "", history
            history = history + [
                _format_message("user", message),
                _format_message("assistant", PLACEHOLDER),
            ]
            return "", history

        def bot_reply(history: Optional[List[Dict[str, Any]]], session_id: str) -> Tuple[List[Dict[str, Any]], str]:
            history = history or []
            session_id = _ensure_session(session_id)
            if len(history) < 2:
                return history, session_id
            last_assistant = history[-1]
            last_user = history[-2]
            if last_assistant.get("role") != "assistant" or _extract_text(last_assistant) != PLACEHOLDER:
                return history, session_id
            if last_user.get("role") != "user":
                return history, session_id
            user_message = _extract_text(last_user)
            if not isinstance(user_message, str):
                user_message = str(user_message)
            reply, new_session = _call_backend(user_message, session_id)
            history[-1] = _format_message("assistant", reply)
            return history, new_session

        send_chain = user_box.submit(
            user_submit,
            inputs=[user_box, chatbot],
            outputs=[user_box, chatbot],
            queue=False,
        )
        send_chain.then(bot_reply, inputs=[chatbot, session_state], outputs=[chatbot, session_state])

        click_chain = send_btn.click(
            user_submit,
            inputs=[user_box, chatbot],
            outputs=[user_box, chatbot],
            queue=False,
        )
        click_chain.then(bot_reply, inputs=[chatbot, session_state], outputs=[chatbot, session_state])

        clear_btn.click(
            lambda: ([], str(uuid.uuid4())),
            inputs=None,
            outputs=[chatbot, session_state],
        )

    return demo


def main():
    demo = build_interface()
    demo.queue()
    demo.launch(server_name=GRADIO_HOST, server_port=GRADIO_PORT, share=False)


if __name__ == "__main__":
    main()
