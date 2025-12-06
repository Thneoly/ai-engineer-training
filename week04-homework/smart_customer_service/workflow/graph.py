"""LangGraph workflow that powers the smart customer service bot."""
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from ..tools import OrderTools
from ..plugins.manager import PluginManager
from ..workflow.router import IntentRouter
from ..model.local_llm import DeterministicChatModel


class ConversationState(TypedDict, total=False):
    session_id: str
    messages: Annotated[List[BaseMessage], add_messages]
    intent: Optional[str]
    pending_intent: Optional[str]
    pending_slot: Optional[str]
    slots: Dict[str, str]
    tool_events: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class WorkflowFactory:
    def __init__(self, tools: OrderTools, plugin_manager: PluginManager, llm: DeterministicChatModel):
        self.tools = tools
        self.plugin_manager = plugin_manager
        self.router = IntentRouter()
        self.llm = llm
        self.general_chain = (
            ChatPromptTemplate.from_messages(
                [
                    ("system", "{system_prompt}"),
                    MessagesPlaceholder(variable_name="history"),
                    ("human", "{input}"),
                ]
            )
            | self.llm
            | StrOutputParser()
        )

    def default_state(self, session_id: str, system_prompt: str) -> ConversationState:
        return {
            "session_id": session_id,
            "messages": [SystemMessage(content=system_prompt)],
            "slots": {},
            "tool_events": [],
            "metadata": {"system_prompt": system_prompt},
        }

    def build(self):
        graph = StateGraph(ConversationState)

        def route_node(state: ConversationState) -> ConversationState:
            last_message = state["messages"][-1]
            if not isinstance(last_message, HumanMessage):
                return state
            result = self.router.detect(
                last_message.content,
                pending_slot=state.get("pending_slot"),
                pending_intent=state.get("pending_intent"),
            )
            updates: ConversationState = {"intent": result.intent}
            if result.required_slot:
                updates["pending_slot"] = result.required_slot
                updates["pending_intent"] = result.intent
            else:
                updates["pending_slot"] = None
                updates["pending_intent"] = None
            return updates

        def route_next(state: ConversationState):
            if state.get("pending_slot"):
                return "slot"
            intent = state.get("intent")
            return {
                "order": "order",
                "refund": "refund",
                "invoice": "invoice",
            }.get(intent, "general")

        def slot_node(state: ConversationState) -> ConversationState:
            slot = state.get("pending_slot")
            if not slot:
                return state
            prompts = {
                "order_id": "请提供您的订单号，方便我继续处理。",
                "email": "请提供接收发票的邮箱地址。",
            }
            reply = prompts.get(slot, "我需要更多信息才能继续，请补充。")
            ai = AIMessage(content=reply)
            return {
                "messages": [ai],
            }

        def order_node(state: ConversationState) -> ConversationState:
            last_message = state["messages"][-1]
            slots = dict(state.get("slots", {}))
            if isinstance(last_message, HumanMessage):
                order_id = self.router.extract_order_id(last_message.content)
                if order_id:
                    slots["order_id"] = order_id
            order_id = slots.get("order_id")
            if not order_id:
                ai = AIMessage(content="我需要订单号才能继续处理，请您提供 9 位以上的订单编号。")
                return {"messages": [ai], "pending_slot": "order_id", "pending_intent": "order", "slots": slots}
            try:
                summary = self.tools.summarize_order(order_id)
                data = self.tools.query_order(order_id)
            except ValueError as exc:
                return {
                    "messages": [AIMessage(content=str(exc))],
                    "slots": {},
                    "intent": None,
                    "pending_intent": None,
                    "pending_slot": None,
                }
            ai = AIMessage(content=summary)
            return {
                "messages": [ai],
                "slots": {},
                "tool_events": state.get("tool_events", []) + [{"tool": "query_order", "data": data}],
                "intent": None,
                "pending_intent": None,
                "pending_slot": None,
            }

        def refund_node(state: ConversationState) -> ConversationState:
            last_message = state["messages"][-1]
            slots = dict(state.get("slots", {}))
            order_id = self.router.extract_order_id(last_message.content)
            if order_id:
                slots["order_id"] = order_id
            if "order_id" not in slots:
                return {
                    "messages": [AIMessage(content="退款需要先提供订单号哦。")],
                    "pending_slot": "order_id",
                    "pending_intent": "refund",
                    "slots": slots,
                }
            reason = "用户申请退款"
            try:
                message = self.tools.request_refund(slots["order_id"], reason)
            except ValueError as exc:
                return {
                    "messages": [AIMessage(content=str(exc))],
                    "slots": {},
                    "intent": None,
                    "pending_slot": None,
                    "pending_intent": None,
                }
            event = {"tool": "request_refund", "data": {"order_id": slots["order_id"], "reason": reason}}
            return {
                "messages": [AIMessage(content=message)],
                "slots": {},
                "tool_events": state.get("tool_events", []) + [event],
                "intent": None,
                "pending_slot": None,
                "pending_intent": None,
            }

        def invoice_node(state: ConversationState) -> ConversationState:
            last_message = state["messages"][-1]
            slots = dict(state.get("slots", {}))
            order_id = self.router.extract_order_id(last_message.content)
            email = self.router.extract_email(last_message.content)
            if order_id:
                slots["order_id"] = order_id
            if email:
                slots["email"] = email
            missing = [slot for slot in ("order_id", "email") if slot not in slots]
            if missing:
                return {
                    "messages": [AIMessage(content="开具发票需要订单号和接收发票的邮箱地址，请您补充信息。")],
                    "pending_slot": missing[0],
                    "pending_intent": "invoice",
                    "slots": slots,
                }
            try:
                result = self.plugin_manager.dispatch(
                    "invoice.issue",
                    {"order_id": slots["order_id"], "email": slots["email"]},
                )
                content = (
                    f"已为订单 {result['order_id']} 开具电子发票，编号 {result['invoice_no']}，"
                    f"我们已发送至 {result['email']}，也可通过链接 {result['download_url']} 下载。"
                )
            except ValueError as exc:
                return {
                    "messages": [AIMessage(content=str(exc))],
                    "slots": {},
                    "intent": None,
                    "pending_slot": None,
                    "pending_intent": None,
                }
            event = {"tool": "invoice.issue", "data": result}
            return {
                "messages": [AIMessage(content=content)],
                "slots": {},
                "tool_events": state.get("tool_events", []) + [event],
                "intent": None,
                "pending_slot": None,
                "pending_intent": None,
            }

        def general_node(state: ConversationState) -> ConversationState:
            history = [m for m in state["messages"][:-1] if not isinstance(m, SystemMessage)]
            last = state["messages"][-1]
            response = self.general_chain.invoke(
                {
                    "system_prompt": state.get("metadata", {}).get("system_prompt", ""),
                    "history": history,
                    "input": last.content,
                }
            )
            ai = AIMessage(content=response)
            return {"messages": [ai], "intent": None, "pending_slot": None, "pending_intent": None}

        def collect_node(state: ConversationState) -> ConversationState:
            return state

        graph.add_node("route", route_node)
        graph.add_node("slot", slot_node)
        graph.add_node("order", order_node)
        graph.add_node("refund", refund_node)
        graph.add_node("invoice", invoice_node)
        graph.add_node("general", general_node)
        graph.add_node("collect", collect_node)

        graph.set_entry_point("route")
        graph.add_conditional_edges("route", route_next, {"slot": "slot", "order": "order", "refund": "refund", "invoice": "invoice", "general": "general"})
        graph.add_edge("slot", END)
        graph.add_edge("order", END)
        graph.add_edge("refund", END)
        graph.add_edge("invoice", END)
        graph.add_edge("general", END)

        return graph.compile()
