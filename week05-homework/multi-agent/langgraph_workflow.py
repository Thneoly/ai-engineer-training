from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, TypedDict

from dotenv import load_dotenv
from ddgs import DDGS
import httpx
from langchain_community.chat_models import ChatTongyi
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph


class GraphState(TypedDict, total=False):
    question: str
    tone: str
    length: str
    audience: str
    model_name: str
    search_results: List[Dict[str, Any]]
    research: Dict[str, Any]
    draft: str
    review: Dict[str, Any]
    final_article: str
    timeline: List[Dict[str, Any]]
    retry_log: List[str]


def now_ts() -> str:
    return datetime.utcnow().strftime("%H:%M:%S")


def extend_timeline(state: GraphState, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [*state.get("timeline", []), entry]


def extend_retry(state: GraphState, message: str) -> List[str]:
    return [*state.get("retry_log", []), f"{now_ts()} · {message}"]


def safe_json(payload: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    try:
        data = json.loads(payload)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    merged = dict(fallback)
    merged["raw"] = payload
    return merged


class SSEClientError(RuntimeError):
    """Raised when SSE 服务不可用或返回异常。"""


@dataclass
class SSEServiceClient:
    name: str
    url: str
    timeout: float = 60.0

    def __post_init__(self) -> None:
        timeout_config = httpx.Timeout(self.timeout, connect=10.0)
        self._client = httpx.Client(timeout=timeout_config)

    def invoke(self, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        headers = {"accept": "text/event-stream"}
        logs: List[Dict[str, Any]] = []
        final_payload: Optional[Dict[str, Any]] = None
        try:
            with self._client.stream("POST", self.url, json=payload, headers=headers) as response:
                response.raise_for_status()
                for event, data in _iter_sse_events(response):
                    if event == "log":
                        logs.append(data if isinstance(data, dict) else {"message": str(data)})
                    elif event == "result":
                        if isinstance(data, dict):
                            final_payload = data
                        else:
                            raise SSEClientError(f"{self.name} result 事件不是 JSON 对象")
        except httpx.HTTPError as exc:  # pragma: no cover - 网络相关
            raise SSEClientError(f"{self.name} 服务调用失败：{exc}") from exc
        if final_payload is None:
            raise SSEClientError(f"{self.name} 服务未返回 result 事件")
        return final_payload, logs


def _iter_sse_events(response: httpx.Response) -> Iterator[Tuple[str, Any]]:
    event_name: Optional[str] = None
    data_lines: List[str] = []
    for raw_line in response.iter_lines():
        if raw_line is None:
            continue
        line = raw_line.strip()
        if not line:
            if event_name and data_lines:
                yield event_name, _decode_sse_data("\n".join(data_lines))
            event_name = None
            data_lines = []
            continue
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())
    if event_name and data_lines:
        yield event_name, _decode_sse_data("\n".join(data_lines))


def _decode_sse_data(payload: str) -> Any:
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return payload


@dataclass
class MCPServiceClients:
    research: SSEServiceClient
    writing: SSEServiceClient
    review: SSEServiceClient
    polish: SSEServiceClient


class DuckDuckGoSearchTool:
    def __init__(self, *, max_results: int = 4, region: str = "cn-zh", timelimit: str | None = None) -> None:
        self.max_results = max_results
        self.region = region
        self.timelimit = timelimit

    def search(self, query: str) -> List[Dict[str, str]]:
        items: List[Dict[str, str]] = []
        try:
            with DDGS(timeout=10) as client:
                for result in client.text(
                    query,
                    max_results=self.max_results,
                    region=self.region,
                    timelimit=self.timelimit,
                ):
                    items.append(
                        {
                            "title": result.get("title", ""),
                            "snippet": result.get("body", ""),
                            "url": result.get("href") or result.get("url", ""),
                        }
                    )
        except Exception as exc:  # pragma: no cover - 网络相关
            items.append(
                {
                    "title": "DuckDuckGo 搜索失败",
                    "snippet": str(exc),
                    "url": "",
                }
            )
        return items or [
            {
                "title": "未获取到搜索结果",
                "snippet": "请稍后重试或更换关键词",
                "url": "",
            }
        ]


class PromptLibrary:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        self.research_chain = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "你是研究代理，负责输出结构化研究包。"
                        "请只返回 JSON，包含 outline(列表)、bullet_points(列表)、citations(列表)、insight(字符串)。",
                    ),
                    (
                        "human",
                        "问题：{question}\n语气：{tone}\n篇幅：{length}\n"
                        "以下是真实检索结果摘要，可用作引用依据：\n{search_summary}",
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
                        "你是审核代理，输出 JSON：status(approved/needs_revision)、issues(列表)、actions(列表)、summary(字符串)。",
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
                        "你是高级审核代理，针对上一轮问题给出最终决策，务必输出 JSON：status、actions、summary、compliance_notes。",
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


def research_node(prompts: PromptLibrary, search_tool: DuckDuckGoSearchTool):
    def _node(state: GraphState) -> GraphState:
        search_results = search_tool.search(state["question"])
        search_summary = "\n".join(
            f"- {item['title']}（{item['url']}）: {item['snippet']}".strip()
            for item in search_results
            if item.get("title") or item.get("snippet")
        )
        raw = prompts.research_chain.invoke(
            {
                "question": state["question"],
                "tone": state["tone"],
                "length": state["length"],
                "search_summary": search_summary or "(检索结果为空)",
            }
        )
        research = safe_json(
            raw,
            {
                "outline": ["引言", "应用场景", "落地策略"],
                "bullet_points": ["默认要点"],
                "citations": [],
                "insight": "",
            },
        )
        entry = {
            "agent": "研究代理",
            "summary": "完成研究资料",
            "artifacts": {
                "search_results": search_results,
                "package": research,
            },
            "timestamp": now_ts(),
        }
        return {
            "research": research,
            "search_results": search_results,
            "timeline": extend_timeline(state, entry),
        }

    return _node


def writing_node(prompts: PromptLibrary):
    def _node(state: GraphState) -> GraphState:
        bullets = state.get("research", {}).get("bullet_points", [])
        summary = "\n".join(f"- {item}" for item in bullets)
        draft = prompts.writing_chain.invoke(
            {
                "tone": state["tone"],
                "length": state["length"],
                "summary": summary,
            }
        )
        entry = {
            "agent": "撰写代理",
            "summary": "生成文章初稿",
            "artifacts": {"preview": draft[:200]},
            "timestamp": now_ts(),
        }
        return {"draft": draft, "timeline": extend_timeline(state, entry)}

    return _node


def review_node(prompts: PromptLibrary):
    def _node(state: GraphState) -> GraphState:
        draft = state.get("draft", "")
        review_raw = prompts.review_chain.invoke({"draft": draft})
        review = safe_json(
            review_raw,
            {
                "status": "needs_revision",
                "issues": ["缺少引用"],
                "actions": ["增加数据"],
                "summary": "默认审核结果",
            },
        )
        retry_log = state.get("retry_log", [])
        if review.get("status") != "approved":
            retry_log = extend_retry(state, "一级审核未通过，启动高级审核")
            senior_raw = prompts.senior_chain.invoke(
                {"draft": draft, "issues": "; ".join(review.get("issues", []))}
            )
            senior = safe_json(
                senior_raw,
                {
                    "status": "approved",
                    "actions": review.get("actions", []),
                    "summary": "高级审核补充说明",
                    "compliance_notes": "",
                },
            )
            senior["escalated_from"] = review
            review = senior
        entry = {
            "agent": "审核代理",
            "summary": review.get("summary", "审核完成"),
            "artifacts": review,
            "timestamp": now_ts(),
        }
        return {
            "review": review,
            "timeline": extend_timeline(state, entry),
            "retry_log": retry_log,
        }

    return _node


def polish_node(prompts: PromptLibrary):
    def _node(state: GraphState) -> GraphState:
        review = state.get("review", {})
        draft = state.get("draft", "")
        actions = "\n".join(review.get("actions", []))
        final_article = prompts.polish_chain.invoke(
            {
                "tone": state["tone"],
                "audience": state["audience"],
                "draft": draft,
                "actions": actions,
            }
        )
        entry = {
            "agent": "润色代理",
            "summary": "润色完成，生成终稿",
            "artifacts": {"preview": final_article[:200]},
            "timestamp": now_ts(),
        }
        return {
            "final_article": final_article,
            "timeline": extend_timeline(state, entry),
        }

    return _node


def remote_research_node(client: SSEServiceClient):
    def _node(state: GraphState) -> GraphState:
        payload = {
            "question": state["question"],
            "tone": state["tone"],
            "length": state["length"],
        }
        data, logs = client.invoke(payload)
        research = data.get("research", {})
        search_results = data.get("search_results", [])
        artifacts: Dict[str, Any] = {
            "search_results": search_results,
            "package": research,
        }
        if logs:
            artifacts["logs"] = logs
        entry = {
            "agent": "研究代理",
            "summary": "完成研究资料",
            "artifacts": artifacts,
            "timestamp": now_ts(),
        }
        return {
            "research": research,
            "search_results": search_results,
            "timeline": extend_timeline(state, entry),
        }

    return _node


def remote_writing_node(client: SSEServiceClient):
    def _node(state: GraphState) -> GraphState:
        bullets = state.get("research", {}).get("bullet_points", [])
        summary = "\n".join(f"- {item}" for item in bullets)
        data, logs = client.invoke(
            {
                "tone": state["tone"],
                "length": state["length"],
                "summary": summary,
            }
        )
        draft = data.get("draft", "")
        artifacts: Dict[str, Any] = {"preview": draft[:200]}
        if logs:
            artifacts["logs"] = logs
        entry = {
            "agent": "撰写代理",
            "summary": "生成文章初稿",
            "artifacts": artifacts,
            "timestamp": now_ts(),
        }
        return {"draft": draft, "timeline": extend_timeline(state, entry)}

    return _node


def remote_review_node(client: SSEServiceClient):
    def _node(state: GraphState) -> GraphState:
        data, logs = client.invoke({"draft": state.get("draft", "")})
        review = data.get("review", {})
        retry_log = [*state.get("retry_log", []), *data.get("retry_log", [])]
        artifacts: Dict[str, Any] = review.copy()
        if logs:
            artifacts["logs"] = logs
        entry = {
            "agent": "审核代理",
            "summary": review.get("summary", "审核完成"),
            "artifacts": artifacts,
            "timestamp": now_ts(),
        }
        return {
            "review": review,
            "timeline": extend_timeline(state, entry),
            "retry_log": retry_log,
        }

    return _node


def remote_polish_node(client: SSEServiceClient):
    def _node(state: GraphState) -> GraphState:
        review = state.get("review", {})
        actions = review.get("actions", [])
        data, logs = client.invoke(
            {
                "tone": state["tone"],
                "audience": state["audience"],
                "draft": state.get("draft", ""),
                "actions": actions,
            }
        )
        final_article = data.get("final_article", "")
        artifacts: Dict[str, Any] = {"preview": final_article[:200]}
        if logs:
            artifacts["logs"] = logs
        entry = {
            "agent": "润色代理",
            "summary": "润色完成，生成终稿",
            "artifacts": artifacts,
            "timestamp": now_ts(),
        }
        return {
            "final_article": final_article,
            "timeline": extend_timeline(state, entry),
        }

    return _node


def build_local_graph(prompts: PromptLibrary, search_tool: DuckDuckGoSearchTool):
    graph = StateGraph(GraphState)
    graph.add_node("research", research_node(prompts, search_tool))
    graph.add_node("writing", writing_node(prompts))
    graph.add_node("review", review_node(prompts))
    graph.add_node("polish", polish_node(prompts))

    graph.add_edge(START, "research")
    graph.add_edge("research", "writing")
    graph.add_edge("writing", "review")
    graph.add_edge("review", "polish")
    graph.add_edge("polish", END)
    return graph.compile(checkpointer=MemorySaver())


def build_remote_graph(clients: MCPServiceClients):
    graph = StateGraph(GraphState)
    graph.add_node("research", remote_research_node(clients.research))
    graph.add_node("writing", remote_writing_node(clients.writing))
    graph.add_node("review", remote_review_node(clients.review))
    graph.add_node("polish", remote_polish_node(clients.polish))

    graph.add_edge(START, "research")
    graph.add_edge("research", "writing")
    graph.add_edge("writing", "review")
    graph.add_edge("review", "polish")
    graph.add_edge("polish", END)
    return graph.compile(checkpointer=MemorySaver())


class LocalFallbackLLM(BaseChatModel):
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
                    "outline": ["引言", "行业背景", "落地路径", "总结"],
                    "bullet_points": [
                        "千问模型通过工具调用支撑知识管理",
                        "MCP 让多代理上下文更可观测",
                        "LangGraph 易于构建顺序型协作流程",
                    ],
                    "citations": ["Gartner 2024", "阿里云千问案例"],
                    "insight": "企业可以把 Agent 视作知识运营流水线。",
                },
                ensure_ascii=False,
            )
        if "撰写代理" in prompt:
            return (
                "# AI Agent 驱动的知识管理升级\n\n"
                "### 1. 背景\nMCP 协议提供统一通信层。\n\n"
                "### 2. 场景\n千问模型与检索工具结合，交付一致答案。\n\n"
                "### 3. 落地\n借助 LangGraph 设定重试策略，保障质量。\n\n"
                "### 4. 结语\n多代理写作成为企业知识工作的第二大脑。"
            )
        if "审核代理" in prompt and "高级" not in prompt:
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
        if "高级审核代理" in prompt:
            return json.dumps(
                {
                    "status": "approved",
                    "actions": ["已添加案例引用", "保留异常日志"],
                    "summary": "高级审核确认可发布",
                    "compliance_notes": "所有引用已在脚注",
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


def build_llm(model: str, mock: bool) -> BaseChatModel:
    if mock:
        return LocalFallbackLLM()
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 DASHSCOPE_API_KEY 环境变量，可使用 --mock 体验。")
    return ChatTongyi(model=model, temperature=0.2)


@dataclass
class ReportBuilder:
    prompt: str

    def build(self, state: GraphState) -> str:
        lines: List[str] = []
        lines.append("# MCP + LangGraph 多代理执行报告")
        lines.append("")
        lines.append(f"- **用户问题**：{self.prompt}")
        lines.append(f"- **语气**：{state.get('tone')}")
        lines.append(f"- **篇幅**：{state.get('length')}")
        lines.append(f"- **目标读者**：{state.get('audience')}")
        lines.append(f"- **模型**：{state.get('model_name')}")
        lines.append("")
        if state.get("search_results"):
            lines.append("## 检索结果摘要")
            for item in state["search_results"]:
                lines.append(
                    f"- {item.get('title') or '(无标题)'} | {item.get('url') or '无链接'}\n  {item.get('snippet', '')}"
                )
            lines.append("")
        lines.append("## 协作过程")
        for item in state.get("timeline", []):
            lines.append(f"### {item['timestamp']} · {item['agent']}")
            lines.append(item.get("summary", ""))
            if item.get("artifacts"):
                lines.append("```json")
                lines.append(json.dumps(item["artifacts"], ensure_ascii=False, indent=2))
                lines.append("```")
            lines.append("")
        if state.get("retry_log"):
            lines.append("## 异常处理日志")
            for record in state["retry_log"]:
                lines.append(f"- {record}")
            lines.append("")
        lines.append("## 最终文章")
        final_article = state.get("final_article", "(未生成)")
        lines.append("```markdown")
        lines.append(final_article)
        lines.append("```")
        return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LangGraph 多代理写作")
    parser.add_argument(
        "--prompt",
        default="帮我写一篇关于 AI Agent 如何提升企业知识管理效率的文章",
        help="用户输入的问题",
    )
    parser.add_argument("--tone", default="专业且友好", help="文章语气")
    parser.add_argument("--length", default="1200 字左右", help="目标篇幅")
    parser.add_argument("--audience", default="企业数字化负责人", help="目标读者")
    parser.add_argument("--model", default="qwen-plus", help="千问模型名称")
    parser.add_argument(
        "--report",
        default=str(Path(__file__).with_name("report.md")),
        help="报告输出路径",
    )
    parser.add_argument("--mock", action="store_true", help="使用本地假模型运行")
    parser.add_argument(
        "--mcp-mode",
        choices=["remote", "local"],
        default=os.getenv("MCP_MODE", "remote"),
        help="remote 模式会调用独立的 SSE 服务，local 模式回退到进程内链路",
    )
    parser.add_argument(
        "--research-url",
        default=os.getenv("MCP_RESEARCH_URL", "http://localhost:8101/events"),
        help="研究代理 SSE 端点",
    )
    parser.add_argument(
        "--writing-url",
        default=os.getenv("MCP_WRITING_URL", "http://localhost:8102/events"),
        help="撰写代理 SSE 端点",
    )
    parser.add_argument(
        "--review-url",
        default=os.getenv("MCP_REVIEW_URL", "http://localhost:8103/events"),
        help="审核代理 SSE 端点",
    )
    parser.add_argument(
        "--polish-url",
        default=os.getenv("MCP_POLISH_URL", "http://localhost:8104/events"),
        help="润色代理 SSE 端点",
    )
    parser.add_argument(
        "--service-timeout",
        type=float,
        default=float(os.getenv("MCP_SERVICE_TIMEOUT", "60")),
        help="调用 SSE 服务的超时时间（秒）",
    )
    return parser.parse_args()


def run_cli() -> None:
    load_dotenv()
    args = parse_args()
    if args.mcp_mode == "remote":
        clients = MCPServiceClients(
            research=SSEServiceClient("research", args.research_url, timeout=args.service_timeout),
            writing=SSEServiceClient("writing", args.writing_url, timeout=args.service_timeout),
            review=SSEServiceClient("review", args.review_url, timeout=args.service_timeout),
            polish=SSEServiceClient("polish", args.polish_url, timeout=args.service_timeout),
        )
        app = build_remote_graph(clients)
    else:
        llm = build_llm(args.model, args.mock)
        prompts = PromptLibrary(llm)
        search_tool = DuckDuckGoSearchTool()
        app = build_local_graph(prompts, search_tool)
    initial_state: GraphState = {
        "question": args.prompt,
        "tone": args.tone,
        "length": args.length,
        "audience": args.audience,
        "model_name": args.model,
        "timeline": [],
        "retry_log": [],
        "search_results": [],
    }
    config = {"configurable": {"thread_id": f"cli-{int(datetime.utcnow().timestamp())}"}}
    final_state: Optional[GraphState] = None
    for event in app.stream(initial_state, config=config):
        for node_name, payload in event.items():
            if node_name == "__root__":
                final_state = payload
                continue
            summary = None
            timeline = payload.get("timeline", [])
            if timeline:
                summary = timeline[-1].get("summary")
            print(f"[LangGraph] {node_name} 完成：{summary or '已执行'}")
    if final_state is None:
        snapshot = app.get_state(config)
        final_state = snapshot.values  # type: ignore[assignment]
    builder = ReportBuilder(args.prompt)
    report_text = builder.build(final_state)
    report_path = Path(args.report)
    report_path.write_text(report_text, encoding="utf-8")
    print(f"[LangGraph] 执行完成，报告已写入 {report_path}")


def main() -> None:
    run_cli()


if __name__ == "__main__":  # pragma: no cover
    main()
