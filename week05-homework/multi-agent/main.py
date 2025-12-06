from __future__ import annotations
# TEMP

import json
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


class AgentExecutionError(RuntimeError):
    """通用的代理执行异常。"""


class NeedUserInputError(AgentExecutionError):
    """表示代理需要用户补充信息。"""


@dataclass
class WorkflowState:
    user_prompt: str
    tone: str
    target_length: str
    research_package: Dict[str, Any] = field(default_factory=dict)
    draft: str = ""
    review_notes: Dict[str, Any] = field(default_factory=dict)
    final_article: str = ""
    metadata: Dict[str, Any] = field(default_factory=lambda: {"user_feedback": []})

    def clone_snapshot(self) -> Dict[str, Any]:
        return {
            "user_prompt": self.user_prompt,
            "tone": self.tone,
            "target_length": self.target_length,
            "research_package": self.research_package,
            "draft": self.draft,
            "review_notes": self.review_notes,
            "final_article": self.final_article,
            "metadata": self.metadata,
        }


@dataclass
class AgentOutcome:
    agent: str
    role: str
    success: bool
    content: str
    artifacts: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    transcript: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RetryRecord:
    agent: str
    level: int
    attempt: int
    status: str
    detail: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


class BaseAgent:
    def __init__(self, *, name: str, role: str, max_retries: int = 2) -> None:
        self.name = name
        self.role = role
        self.max_retries = max_retries

    def run(self, state: WorkflowState) -> AgentOutcome:  # pragma: no cover - interface
        raise NotImplementedError

    def fallback_payload(self, state: WorkflowState, reason: str) -> AgentOutcome:
        content = f"{self.name} 未完成任务：{reason}"
        return AgentOutcome(
            agent=self.name,
            role=self.role,
            success=False,
            content=content,
            artifacts={"snapshot": state.clone_snapshot()},
            suggestions=["请在提供缺失信息后重新运行流程"],
            transcript=[content],
        )


LOCAL_KNOWLEDGE_BASE = [
    {
        "title": "AI Agent 在企业服务中的应用",
        "summary": "AI Agent 通过工具使用与上下文记忆，在客服、销售赋能、内部知识管理领域带来 30%+ 的效率提升。",
        "highlights": [
            "企业更关注可观测性与安全，将 Agent 嵌入现有 ITSM 流程",
            "MCP 协议让 Agent 可以安全访问检索、数据看板等企业内部工具",
        ],
        "quotes": [
            "Gartner 预测：到 2026 年，70% 的企业将部署面向员工的 Agent 协作系统。"
        ],
    },
    {
        "title": "MCP (Model Context Protocol) 观察",
        "summary": "MCP 通过统一的上下文会话协议，连接模型、插件与数据源，降低多代理协同的开发难度。",
        "highlights": [
            "所有消息都带有结构化 metadata，便于追踪与审计",
            "支持多路并发与回放，便于失败重试",
        ],
        "quotes": [
            "MCP 让 '工具即对话节点' 成为可能，每个代理都可以把自身能力暴露为安全端点。"
        ],
    },
    {
        "title": "行业案例：制造业智能调度",
        "summary": "多代理系统在制造业用于工单分发、库存监控与报警预案，帮助工厂把停机时间下降 18%。",
        "highlights": [
            "研究代理从 MES 报表获取即时数据，审核代理对安全策略负责",
            "润色代理会根据操作人员角色，输出多语言的执行摘要",
        ],
        "quotes": [
            "青岛某工厂引入 agent 后，现场排班透明度提升 42%。"
        ],
    },
    {
        "title": "AI 合规与治理",
        "summary": "多代理写作需要内置合规校验，尤其是引用的准确性与数据脱敏。",
        "highlights": [
            "审核代理应校对事实，确保引用来源",
            "重试策略可以把异常显式记录到 '异常处理日志'",
        ],
        "quotes": [
            "透明的异常记录是 AI 内容进入生产流程的前置条件。"
        ],
    },
]


class LocalSearchTool:
    def __init__(self, corpus: Sequence[Dict[str, Any]]) -> None:
        self._corpus = corpus

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        normalized = [token for token in query.lower().replace("，", " ").split() if token]
        scored: List[Tuple[int, Dict[str, Any]]] = []
        for doc in self._corpus:
            text_blob = " ".join([doc["title"], doc["summary"], " ".join(doc["highlights"])])
            text_lower = text_blob.lower()
            score = sum(text_lower.count(token) for token in normalized)
            scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for score, doc in scored[:top_k] if score > 0] or [self._corpus[0]]


class ResearchAgent(BaseAgent):
    def __init__(self, tool: LocalSearchTool) -> None:
        super().__init__(name="研究代理", role="Research Agent")
        self._tool = tool
        self._warmed_up = False

    def run(self, state: WorkflowState) -> AgentOutcome:
        if not self._warmed_up:
            self._warmed_up = True
            raise AgentExecutionError("搜索服务正在预热，触发一次自动重试")

        results = self._tool.search(state.user_prompt)
        key_points = [doc["summary"] for doc in results]
        outline = [f"部分 {idx + 1}: {doc['title']}" for idx, doc in enumerate(results)]

        research_package = {
            "findings": key_points,
            "highlights": [highlight for doc in results for highlight in doc["highlights"]],
            "quotes": [quote for doc in results for quote in doc["quotes"]],
            "outline": outline,
        }
        state.research_package = research_package

        content = "\n".join([
            "- 关键结论: " + key_points[0],
            "- 支撑亮点: " + "；".join(research_package["highlights"][:3]),
            "- 推荐框架: " + " → ".join(outline),
        ])
        transcript = [json.dumps(research_package, ensure_ascii=False, indent=2)]
        return AgentOutcome(
            agent=self.name,
            role=self.role,
            success=True,
            content=content,
            artifacts={"research": research_package},
            suggestions=outline,
            transcript=transcript,
        )


class WritingAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="撰写代理", role="Writing Agent")

    def run(self, state: WorkflowState) -> AgentOutcome:
        if not state.research_package:
            raise AgentExecutionError("缺少研究资料，无法起草")

        intro = textwrap.dedent(
            f"""
            随着 MCP 协议的成熟，AI Agent 正在从单体技能走向团队协作。{state.research_package['findings'][0]}
            """
        ).strip()
        body_sections = []
        for idx, highlight in enumerate(state.research_package["highlights"][:3]):
            body_sections.append(f"### 场景 {idx + 1}\n{highlight}")
        quotes = "\n".join(f"> {quote}" for quote in state.research_package["quotes"][:2])
        conclusion = (
            "当我们把 MCP 的可观测性与分层重试策略结合，企业就可以把多代理写作纳入标准流程，"
            "在保证质量的同时缩短从调研到发布的周期。"
        )
        article = "\n\n".join([intro, *body_sections, quotes, conclusion])
        state.draft = article

        suggestions = [
            "检查是否引用了最新数据",
            f"保持语调：{state.tone}",
            f"篇幅控制在 {state.target_length}",
        ]
        return AgentOutcome(
            agent=self.name,
            role=self.role,
            success=True,
            content="初稿完成，包含引言、三个场景与总结",
            artifacts={"draft": article},
            suggestions=suggestions,
            transcript=[article[:400] + ("..." if len(article) > 400 else "")],
        )


class ReviewAgent(BaseAgent):
    def __init__(self, *, force_fail: bool = True) -> None:
        super().__init__(name="审核代理", role="Review Agent")
        self._force_fail = force_fail
        self._attempt = 0

    def run(self, state: WorkflowState) -> AgentOutcome:
        if not state.draft:
            raise AgentExecutionError("没有初稿，无法审核")

        self._attempt += 1
        if self._force_fail and self._attempt <= 2:
            raise AgentExecutionError("模拟事实核查失败，触发备用代理")

        issues = self._evaluate_draft(state.draft)
        feedback = {
            "issues": issues,
            "actions": ["补充行业案例引用", "强化落地步骤"],
            "logic_score": 8.5,
        }
        state.review_notes = feedback
        content = "；".join(issues)
        return AgentOutcome(
            agent=self.name,
            role=self.role,
            success=True,
            content="审核完成，给出 2 条修改建议",
            artifacts={"review": feedback},
            suggestions=feedback["actions"],
            transcript=[content],
        )

    @staticmethod
    def _evaluate_draft(draft: str) -> List[str]:
        issues = []
        if "###" not in draft:
            issues.append("缺少结构化小节标题")
        if len(draft) < 300:
            issues.append("篇幅偏短")
        issues.append("需要更明确的数据引用")
        return issues


class SeniorReviewAgent(ReviewAgent):
    def __init__(self) -> None:
        super().__init__(force_fail=False)
        self.name = "高级审核代理"

    def run(self, state: WorkflowState) -> AgentOutcome:
        outcome = super().run(state)
        outcome.suggestions.append("在异常日志中保留引用来源")
        outcome.content = "高级审核代理完成复核"
        return outcome


class PolishingAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="润色代理", role="Polishing Agent")
        self._needs_feedback = True

    def run(self, state: WorkflowState) -> AgentOutcome:
        if not state.draft:
            raise AgentExecutionError("缺少草稿，无法润色")

        if self._needs_feedback and not state.metadata.get("user_feedback"):
            raise NeedUserInputError("需要用户指定目标读者与语气")

        self._needs_feedback = False
        tone_hint = state.metadata.get("user_feedback", [state.tone])[-1]
        final_article = self._polish(state, tone_hint)
        state.final_article = final_article
        suggestions = ["已结合用户需求完成润色", "最终稿已同步异常日志信息"]
        return AgentOutcome(
            agent=self.name,
            role=self.role,
            success=True,
            content="润色完成，交付终稿",
            artifacts={"final_article": final_article},
            suggestions=suggestions,
            transcript=[final_article[:400] + ("..." if len(final_article) > 400 else "")],
        )

    def _polish(self, state: WorkflowState, tone_hint: str) -> str:
        review_actions = state.review_notes.get("actions", [])
        actionable = "，".join(review_actions) or "整体结构"
        polished = textwrap.dedent(
            f"""
            # AI Agent 协作写作方案

            {state.draft}

            ---
            **执行要点（来自审核代理）**：{actionable}

            **风格/读者提示**：{tone_hint}
            """
        ).strip()
        return polished


class UserFeedbackProvider:
    def request(self, agent_name: str, question: Optional[str], state: WorkflowState) -> str:
        catalog = {
            "润色代理": "目标读者是企业数字化负责人，请保持务实且友好的语气",
            "研究代理": "优先关注中国企业案例",
            "审核代理": "请确保引用数据来源于近两年",
        }
        base = catalog.get(agent_name, "请突出可执行步骤与风险提示")
        if question:
            return f"{base}（因 {question} ）"
        return base


class RetryManager:
    def __init__(self, feedback_provider: UserFeedbackProvider) -> None:
        self._feedback_provider = feedback_provider

    def execute(
        self,
        agent: BaseAgent,
        state: WorkflowState,
        *,
        fallback: Optional[BaseAgent] = None,
    ) -> Tuple[AgentOutcome, List[RetryRecord]]:
        records: List[RetryRecord] = []
        needs_feedback_reason: Optional[str] = None

        for attempt in range(1, agent.max_retries + 1):
            try:
                outcome = agent.run(state)
                records.append(
                    RetryRecord(
                        agent=agent.name,
                        level=1,
                        attempt=attempt,
                        status="success",
                        detail="重试成功" if attempt > 1 else "一次完成",
                    )
                )
                return outcome, records
            except NeedUserInputError as exc:
                needs_feedback_reason = str(exc)
                records.append(
                    RetryRecord(
                        agent=agent.name,
                        level=1,
                        attempt=attempt,
                        status="need_user_feedback",
                        detail=str(exc),
                    )
                )
                break
            except AgentExecutionError as exc:
                records.append(
                    RetryRecord(
                        agent=agent.name,
                        level=1,
                        attempt=attempt,
                        status="failed",
                        detail=str(exc),
                    )
                )

        if fallback is not None:
            try:
                outcome = fallback.run(state)
                records.append(
                    RetryRecord(
                        agent=fallback.name,
                        level=2,
                        attempt=1,
                        status="success",
                        detail="备用代理完成任务",
                    )
                )
                return outcome, records
            except AgentExecutionError as exc:
                records.append(
                    RetryRecord(
                        agent=fallback.name,
                        level=2,
                        attempt=1,
                        status="failed",
                        detail=str(exc),
                    )
                )

        feedback = self._feedback_provider.request(agent.name, needs_feedback_reason, state)
        state.metadata.setdefault("user_feedback", []).append(feedback)
        records.append(
            RetryRecord(
                agent=agent.name,
                level=3,
                attempt=1,
                status="user_feedback",
                detail=f"注入反馈：{feedback}",
            )
        )
        try:
            outcome = agent.run(state)
            records.append(
                RetryRecord(
                    agent=agent.name,
                    level=3,
                    attempt=2,
                    status="success",
                    detail="结合用户反馈完成",
                )
            )
            return outcome, records
        except AgentExecutionError as exc:
            records.append(
                RetryRecord(
                    agent=agent.name,
                    level=3,
                    attempt=2,
                    status="failed",
                    detail=str(exc),
                )
            )
            return agent.fallback_payload(state, str(exc)), records


class MCPWorkflow:
    def __init__(self) -> None:
        tool = LocalSearchTool(LOCAL_KNOWLEDGE_BASE)
        self._pipeline: List[Tuple[BaseAgent, Optional[BaseAgent]]] = [
            (ResearchAgent(tool), None),
            (WritingAgent(), None),
            (ReviewAgent(), SeniorReviewAgent()),
            (PolishingAgent(), None),
        ]
        self._retry_manager = RetryManager(UserFeedbackProvider())

    def run(self, prompt: str, *, tone: str, length: str) -> Dict[str, Any]:
        state = WorkflowState(user_prompt=prompt, tone=tone, target_length=length)
        outcomes: List[AgentOutcome] = []
        retry_records: List[RetryRecord] = []

        for agent, fallback in self._pipeline:
            print(f"[MCP] {agent.name} 开始执行……")
            outcome, records = self._retry_manager.execute(agent, state, fallback=fallback)
            success_flag = "✅" if outcome.success else "⚠️"
            print(f"[MCP] {agent.name} 完成状态 {success_flag}: {outcome.content}")
            outcomes.append(outcome)
            retry_records.extend(records)

        summary = {
            "state": state,
            "outcomes": outcomes,
            "retry_records": retry_records,
        }
        return summary


class ReportBuilder:
    def build(
        self,
        *,
        prompt: str,
        state: WorkflowState,
        outcomes: Sequence[AgentOutcome],
        retry_records: Sequence[RetryRecord],
    ) -> str:
        lines: List[str] = []
        lines.append("# MCP 多代理文章写作执行报告")
        lines.append("")
        lines.append(f"- **用户问题**：{prompt}")
        lines.append(f"- **语气偏好**：{state.tone}")
        lines.append(f"- **目标篇幅**：{state.target_length}")
        lines.append("")
        lines.append("## 代理完成情况")
        lines.append("代理 | 角色 | 成功 | 关键信息")
        lines.append("--- | --- | --- | ---")
        for outcome in outcomes:
            success = "是" if outcome.success else "否"
            lines.append(
                f"{outcome.agent} | {outcome.role} | {success} | {outcome.content}"
            )

        lines.append("")
        lines.append("## 协作过程记录")
        for idx, outcome in enumerate(outcomes, start=1):
            lines.append(f"### 步骤 {idx}: {outcome.agent}")
            lines.append(outcome.content)
            if outcome.suggestions:
                lines.append("- 建议：" + "；".join(outcome.suggestions))
            if outcome.artifacts:
                pretty = json.dumps(outcome.artifacts, ensure_ascii=False, indent=2)
                lines.append("```json")
                lines.append(pretty)
                lines.append("```")

        lines.append("")
        lines.append("## 最终文章")
        final_article = state.final_article or state.draft
        lines.append("```markdown")
        lines.append(final_article)
        lines.append("```")

        lines.append("")
        lines.append("## 异常处理日志")
        for record in retry_records:
            timestamp = record.timestamp.strftime("%H:%M:%S")
            lines.append(
                f"- [{timestamp}] 级别{record.level} 第{record.attempt}次 {record.agent}：{record.status} → {record.detail}"
            )

        lines.append("")
        lines.append("## 后续可执行建议")
        lines.append("1. 将报告同步到知识库，便于团队复用。")
        lines.append("2. 连接真实搜索/检索插件，替换本地样例数据。")
        lines.append("3. 根据业务需要扩展更多备用代理，细化异常分流。")

        return "\n".join(lines)


def main() -> None:
    """Delegate到 LangGraph 工作流实现，保留旧代码做参考。"""

    # 懒加载，避免在未安装 LangChain/LangGraph 时导入失败
    from .langgraph_workflow import run_cli

    run_cli()


if __name__ == "__main__":
    main()