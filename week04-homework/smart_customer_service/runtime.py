"""Runtime orchestrator tying together sessions, workflow, tools, and plugins."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage

from .config import Settings
from .model.local_llm import DeterministicChatModel
from .orders import ORDER_STORE
from .plugins.manager import PluginManager
from .session import SessionStore, SessionState
from .tools import OrderTools
from .workflow.graph import WorkflowFactory


@dataclass
class RuntimeResponse:
    session_id: str
    reply: str
    intent: str | None
    slot_state: Dict[str, str]
    tool_events: list[dict]


class ServiceRuntime:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.order_tools = OrderTools(ORDER_STORE)
        self.plugin_manager = PluginManager(order_store=ORDER_STORE)
        self.session_store = SessionStore()
        self._refresh_workflow()

    def process(self, session_id: str, user_message: str) -> RuntimeResponse:
        state = self.session_store.get(session_id)
        if not state:
            default = self.workflow_factory.default_state(session_id, self.settings.system_prompt)
            state = SessionState(
                session_id=session_id,
                messages=default["messages"],
                context={},
                slots=default["slots"],
                tool_events=default["tool_events"],
            )
        state.messages.append(HumanMessage(content=user_message))
        result_state_dict = {
            "session_id": state.session_id,
            "messages": state.messages,
            "slots": state.slots,
            "tool_events": state.tool_events,
            "metadata": {"system_prompt": self.settings.system_prompt},
            "intent": state.intent,
            "pending_intent": state.pending_intent,
            "pending_slot": state.pending_slot,
        }
        updated = self.workflow.invoke(result_state_dict, config={"configurable": {"session_id": session_id}})
        ai_message = self._extract_ai(updated["messages"])
        state.messages.append(ai_message)
        state.slots = updated.get("slots", state.slots)
        state.intent = updated.get("intent", state.intent)
        state.pending_slot = updated.get("pending_slot", state.pending_slot)
        state.pending_intent = updated.get("pending_intent", state.pending_intent)
        state.tool_events = updated.get("tool_events", state.tool_events)
        self.session_store.save(state)
        return RuntimeResponse(
            session_id=session_id,
            reply=ai_message.content,
            intent=state.intent,
            slot_state=state.slots,
            tool_events=state.tool_events,
        )

    def reload_model(
        self,
        system_prompt: str | None = None,
        style: str | None = None,
        provider: str | None = None,
        dashscope_model: str | None = None,
        temperature: float | None = None,
    ):
        if system_prompt:
            self.settings.system_prompt = system_prompt
        if style:
            self.settings.model_style = style
        if provider:
            self.settings.llm_provider = provider
        if dashscope_model:
            self.settings.dashscope_model = dashscope_model
        if temperature is not None:
            self.settings.llm_temperature = temperature
        self._refresh_workflow()

    def reload_plugins(self):
        self.plugin_manager.reload()

    def _extract_ai(self, messages: list) -> AIMessage:
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                return msg
        raise ValueError("workflow 没有返回 AIMessage")

    def _refresh_workflow(self):
        self.model = self._build_llm()
        self.workflow_factory = WorkflowFactory(
            tools=self.order_tools,
            plugin_manager=self.plugin_manager,
            llm=self.model,
        )
        self.workflow = self.workflow_factory.build()

    def _build_llm(self):
        provider = self.settings.llm_provider.lower()
        if provider == "tongyi":
            if self.settings.dashscope_api_key:
                os.environ.setdefault("DASHSCOPE_API_KEY", self.settings.dashscope_api_key)
            from langchain_community.chat_models import ChatTongyi

            return ChatTongyi(
                model=self.settings.dashscope_model,
                temperature=self.settings.llm_temperature,
            )
        return DeterministicChatModel(
            system_prompt=self.settings.system_prompt,
            style=self.settings.model_style,
            timezone=self.settings.timezone,
        )
