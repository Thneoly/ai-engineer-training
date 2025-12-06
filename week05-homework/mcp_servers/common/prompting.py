from __future__ import annotations

import json
import os
from typing import Any, List, Optional

from langchain_community.chat_models import ChatTongyi
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.prompts import ChatPromptTemplate


class PromptLibrary:
    """Reusable prompt chains for all MCP services."""

    def __init__(self, llm: BaseChatModel) -> None:
        self.llm = llm
        self.research_chain = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "你是研究代理，负责输出结构化研究包。只返回 JSON："
                        "outline(列表)、bullet_points(列表)、citations(列表)、insight(字符串)。",
                    ),
                    (
                        "human",
                        "问题：{question}\n语气：{tone}\n篇幅：{length}\n"
                        "以下是真实检索摘要，可引用：\n{search_summary}",
                    ),
                ]
            )
            | llm
            | StrOutputParser()
        )
        self.writing_chain = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "你是撰写代理，使用 Markdown 生成文章初稿，包含引言、3 个要点与结论。"
                        "保持 {tone} 语气，长度接近 {length}。",
                    ),
                    (
                        "human",
                        "研究摘要：{summary}",
                    ),
                ]
            )
            | llm
            | StrOutputParser()
        )
        self.review_chain = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "你是审核代理，输出 JSON：status(approved/needs_revision)、issues(列表)、"
                        "actions(列表)、summary(字符串)。",
                    ),
                    (
                        "human",
                        "请审核以下文章：{draft}",
                    ),
                ]
            )
            | llm
            | StrOutputParser()
        )
        self.senior_chain = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "你是高级审核代理，针对上一轮问题给出最终决策，务必输出 JSON："
                        "status、actions、summary、compliance_notes。",
                    ),
                    (
                        "human",
                        "文章内容：{draft}\n上一轮问题：{issues}",
                    ),
                ]
            )
            | llm
            | StrOutputParser()
        )
        self.polish_chain = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "你是润色代理，结合审核建议与受众信息，输出最终 Markdown 文章，保持 {tone} 语气，目标读者：{audience}。",
                    ),
                    (
                        "human",
                        "初稿：{draft}\n审核建议：{actions}",
                    ),
                ]
            )
            | llm
            | StrOutputParser()
        )


class LocalFallbackLLM(BaseChatModel):
    """Lightweight stub model to emulate 千问 for local testing."""

    def __init__(self) -> None:
        super().__init__()
        self._review_calls = 0

    @property
    def _llm_type(self) -> str:  # pragma: no cover - required by BaseChatModel
        return "local-fallback"

    def _route(self, prompt: str) -> str:
        if "研究代理" in prompt:
            return json.dumps(
                {
                    "outline": ["引言", "行业现状", "落地路径", "总结"],
                    "bullet_points": [
                        "MCP 保障多代理通信一致性",
                        "千问模型擅长中文知识写作",
                        "企业实践关注可观测与合规",
                    ],
                    "citations": ["Gartner 2024", "阿里云千问案例"],
                    "insight": "AI Agent 正在成为企业知识工作的第二大脑",
                },
                ensure_ascii=False,
            )
        if "撰写代理" in prompt:
            return (
                "# AI Agent 驱动的知识管理升级\n\n"
                "### 背景\nMCP 协议提供统一通信层。\n\n"
                "### 场景\n千问模型与检索工具结合，交付一致答案。\n\n"
                "### 落地\n借助 LangGraph 设定重试策略，保障质量。\n\n"
                "### 结语\n多代理写作成为企业知识工作的第二大脑。"
            )
        if "高级审核代理" in prompt:
            return json.dumps(
                {
                    "status": "approved",
                    "actions": ["加入数据引用", "补充项目里程碑"],
                    "summary": "高级审核确认可发布",
                    "compliance_notes": "所有引用已在脚注",
                },
                ensure_ascii=False,
            )
        if "审核代理" in prompt:
            self._review_calls += 1
            return json.dumps(
                {
                    "status": "needs_revision" if self._review_calls == 1 else "approved",
                    "issues": ["请补充案例数据"],
                    "actions": ["补充制造业案例"],
                    "summary": "初审建议强化引用",
                },
                ensure_ascii=False,
            )
        if "润色代理" in prompt:
            return (
                "# 最终稿\n\n"
                "结合审核建议后，文章突出千问 + MCP 的协同价值。"
            )
        return "{}"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        prompt = "\n".join(message.content for message in messages)
        content = self._route(prompt)
        generation = ChatGeneration(message=AIMessage(content=content))
        return ChatResult(generations=[generation])


def build_llm(model: str, *, mock: bool = False, temperature: float = 0.2) -> BaseChatModel:
    if mock or os.getenv("MOCK_MODE", "false").lower() == "true":
        return LocalFallbackLLM()
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 DASHSCOPE_API_KEY，可设置 MOCK_MODE=true 进行本地调试")
    return ChatTongyi(model=model, temperature=temperature)
