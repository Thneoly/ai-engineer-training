"""Graph-enhanced RAG + KG CLI."""

from __future__ import annotations

import csv
import json
import logging
import os
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import networkx as nx
import typer
from typing_extensions import Protocol

from llama_index.core import Document, Settings, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

try:
    from neo4j import GraphDatabase
except ImportError:  # pragma: no cover
    GraphDatabase = None  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

app = typer.Typer(help="Graph RAG multi-hop QA")


@dataclass(slots=True)
class Neo4jConfig:
    uri: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None

    def enabled(self) -> bool:
        return bool(self.uri and self.user and self.password)


@dataclass(slots=True)
class AppConfig:
    profiles_path: Path
    shareholders_path: Path
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    chunk_size: int = 512
    chunk_overlap: int = 80
    retriever_top_k: int = 2
    reasoning_depth: int = 2
    neo4j: Neo4jConfig = field(default_factory=Neo4jConfig)

    @staticmethod
    def from_cli(
        profiles_path: Path,
        shareholders_path: Path,
        embedding_model: str,
        chunk_size: int,
        chunk_overlap: int,
        retriever_top_k: int,
        reasoning_depth: int,
        neo4j_uri: Optional[str],
        neo4j_user: Optional[str],
        neo4j_password: Optional[str],
        neo4j_database: Optional[str],
    ) -> "AppConfig":
        cfg = Neo4jConfig(
            uri=neo4j_uri or os.getenv("NEO4J_URI"),
            user=neo4j_user or os.getenv("NEO4J_USER"),
            password=neo4j_password or os.getenv("NEO4J_PASSWORD"),
            database=neo4j_database or os.getenv("NEO4J_DATABASE"),
        )
        return AppConfig(
            profiles_path=profiles_path,
            shareholders_path=shareholders_path,
            embedding_model=embedding_model,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            retriever_top_k=retriever_top_k,
            reasoning_depth=reasoning_depth,
            neo4j=cfg,
        )


@dataclass(slots=True)
class OwnershipEdge:
    investor: str
    investee: str
    ratio: float
    relation: str


class GraphBackend(Protocol):
    def ingest_edges(self, edges: Sequence[OwnershipEdge]) -> None:
        ...

    def top_shareholder(self, company: str) -> Optional[OwnershipEdge]:
        ...


class InMemoryGraphBackend:
    def __init__(self) -> None:
        self._graph = nx.DiGraph()

    def ingest_edges(self, edges: Sequence[OwnershipEdge]) -> None:
        for edge in edges:
            self._graph.add_edge(
                edge.investor,
                edge.investee,
                ratio=edge.ratio,
                relation=edge.relation,
            )

    def top_shareholder(self, company: str) -> Optional[OwnershipEdge]:
        incoming = self._graph.in_edges(company, data=True)
        if not incoming:
            return None
        investor, _, payload = max(incoming, key=lambda item: item[2].get("ratio", 0.0))
        return OwnershipEdge(
            investor=investor,
            investee=company,
            ratio=float(payload.get("ratio", 0.0)),
            relation=str(payload.get("relation", "shareholder")),
        )


class Neo4jGraphBackend:
    def __init__(self, driver, database: Optional[str]):
        self._driver = driver
        self._database = database

    def ingest_edges(self, edges: Sequence[OwnershipEdge]) -> None:
        def _merge(tx, edge: OwnershipEdge) -> None:
            tx.run(
                """
                MERGE (investor:Entity {name: $investor})
                MERGE (investee:Entity {name: $investee})
                MERGE (investor)-[r:HOLDS]->(investee)
                SET r.ratio = $ratio, r.relation = $relation
                """,
                investor=edge.investor,
                investee=edge.investee,
                ratio=edge.ratio,
                relation=edge.relation,
            )

        with self._driver.session(database=self._database) as session:
            for edge in edges:
                session.execute_write(_merge, edge)

    def top_shareholder(self, company: str) -> Optional[OwnershipEdge]:
        query = (
            "MATCH (investor)-[r:HOLDS]->(target {name: $company}) "
            "RETURN investor.name AS investor, r.ratio AS ratio, coalesce(r.relation, 'shareholder') AS relation "
            "ORDER BY r.ratio DESC LIMIT 1"
        )
        with self._driver.session(database=self._database) as session:
            record = session.run(query, company=company).single()
        if not record:
            return None
        return OwnershipEdge(
            investor=record["investor"],
            investee=company,
            ratio=float(record["ratio"] or 0.0),
            relation=record["relation"],
        )

    def close(self) -> None:
        self._driver.close()


class OwnershipReasoner:
    def __init__(self, backend: GraphBackend, depth: int) -> None:
        self.backend = backend
        self.depth = depth

    def trace(self, company: str) -> List[Dict[str, Any]]:
        chain: List[Dict[str, Any]] = []
        current = company
        cumulative_ratio = 1.0
        for level in range(self.depth):
            edge = self.backend.top_shareholder(current)
            if not edge:
                break
            cumulative_ratio *= edge.ratio
            chain.append(
                {
                    "level": level + 1,
                    "investor": edge.investor,
                    "target": edge.investee,
                    "ratio": round(edge.ratio, 4),
                    "cumulative_ratio": round(cumulative_ratio, 4),
                    "relation": edge.relation,
                }
            )
            current = edge.investor
        return chain


class GraphRAGService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._documents = self._load_documents()
        self._vector_index, self._retriever = self._build_index(self._documents)
        self._edges = self._load_edges()
        self._graph_backend = self._resolve_graph_backend()
        self._graph_backend.ingest_edges(self._edges)
        self._reasoner = OwnershipReasoner(self._graph_backend, self.config.reasoning_depth)

    def answer(self, question: str) -> Dict[str, Any]:
        company_hit = self._retrieve_company(question)
        if not company_hit:
            return {
                "question": question,
                "answer": "暂未在知识库中匹配到相关公司，请先扩充 company_profiles.json",
                "evidence": [],
            }

        legal_name = company_hit["metadata"]["legal_name"]
        chain = self._reasoner.trace(legal_name)
        top_holder = chain[0]["investor"] if chain else None
        final_holder = chain[-1]["investor"] if chain else top_holder
        doc_score = float(company_hit.get("score", 0.0))
        ratio_score = chain[0]["ratio"] if chain else 0.0
        joint_score = round(0.7 * doc_score + 0.3 * ratio_score, 4)

        narrative = self._compose_answer(question, legal_name, top_holder, final_holder, chain)
        evidence = {
            "document_snippet": company_hit["text"],
            "retrieval_score": round(doc_score, 4),
            "graph_chain": chain,
            "joint_score": joint_score,
        }
        return {
            "question": question,
            "company": legal_name,
            "answer": narrative,
            "evidence": evidence,
        }

    def bootstrap_graph(self) -> str:
        neo_backend = self._connect_neo4j(strict=True)
        neo_backend.ingest_edges(self._edges)
        neo_backend.close()
        return "Neo4j graph 数据已写入"

    def _load_documents(self) -> List[Document]:
        with self.config.profiles_path.open("r", encoding="utf-8") as fp:
            entries = json.load(fp)
        documents: List[Document] = []
        for entry in entries:
            text_blocks = [
                f"公司名称：{entry['legal_name']}",
                f"别名：{'、'.join(entry.get('aliases', []))}",
                f"行业：{entry.get('sector', 'N/A')}",
                f"总部：{entry.get('headquarters', 'N/A')}",
                entry.get("summary", "") + " " + entry.get("strategic_focus", ""),
            ] + entry.get("documents", [])
            text = "\n".join(filter(None, text_blocks))
            documents.append(
                Document(
                    text=text,
                    metadata={
                        "legal_name": entry["legal_name"],
                        "aliases": entry.get("aliases", []),
                        "sector": entry.get("sector"),
                        "summary": entry.get("summary"),
                    },
                )
            )
        return documents

    def _build_index(self, documents: List[Document]):
        splitter = SentenceSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        Settings.embed_model = self._embed_model
        Settings.node_parser = splitter
        index = VectorStoreIndex.from_documents(
            documents,
            vector_store=SimpleVectorStore(),
            show_progress=True,
            transformations=[splitter],
        )
        retriever = VectorIndexRetriever(index=index, similarity_top_k=self.config.retriever_top_k)
        return index, retriever

    def _load_edges(self) -> List[OwnershipEdge]:
        edges: List[OwnershipEdge] = []
        with self.config.shareholders_path.open("r", encoding="utf-8") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                edges.append(
                    OwnershipEdge(
                        investor=row["investor"].strip(),
                        investee=row["investee"].strip(),
                        ratio=float(row["ratio"]),
                        relation=row.get("relation", "shareholder"),
                    )
                )
        return edges

    def _resolve_graph_backend(self) -> GraphBackend:
        neo = self._connect_neo4j(strict=False)
        if neo:
            LOGGER.info("Connected to Neo4j, 图谱数据将存储在数据库中")
            return neo
        LOGGER.info("Neo4j 未配置，使用内存 NetworkX 图作为后端")
        return InMemoryGraphBackend()

    def _connect_neo4j(self, strict: bool) -> Optional[Neo4jGraphBackend]:
        if not (GraphDatabase and self.config.neo4j.enabled()):
            if strict:
                raise RuntimeError("Neo4j 配置缺失，无法执行该操作")
            return None
        try:
            driver = GraphDatabase.driver(
                self.config.neo4j.uri,
                auth=(self.config.neo4j.user, self.config.neo4j.password),
            )
            with driver.session(database=self.config.neo4j.database) as session:
                session.run("RETURN 1 AS ok").single()
            return Neo4jGraphBackend(driver, self.config.neo4j.database)
        except Exception as exc:  # pragma: no cover
            if strict:
                raise
            LOGGER.warning("Neo4j 连接失败，错误：%s", exc)
            return None

    def _retrieve_company(self, question: str) -> Optional[Dict[str, Any]]:
        nodes = self._retriever.retrieve(question)
        if not nodes:
            return None
        best = nodes[0]
        return {
            "text": best.get_text(),
            "metadata": best.metadata,
            "score": float(best.score or 0.0),
        }

    @cached_property
    def _embed_model(self) -> HuggingFaceEmbedding:
        LOGGER.info("Loading embedding model: %s", self.config.embedding_model)
        return HuggingFaceEmbedding(model_name=self.config.embedding_model)

    def _compose_answer(
        self,
        question: str,
        company: str,
        top_holder: Optional[str],
        final_holder: Optional[str],
        chain: List[Dict[str, Any]],
    ) -> str:
        if not chain or not top_holder:
            return f"未能在图谱中找到 {company} 的股权链路，请检查 Neo4j/CSV 数据。"
        if top_holder == final_holder:
            return (
                f"针对“{question}”，检索结果显示 {company} 的最大股东为 {top_holder}，"
                f"持股比例 {chain[0]['ratio']*100:.1f}%。"
            )
        final_ratio = chain[-1]["cumulative_ratio"]
        steps = " -> ".join(
            f"{step['investor']}({step['ratio']*100:.1f}%)" for step in chain
        )
        return (
            f"针对“{question}”，RAG 首先定位公司 {company}，"
            f"图谱推理链路为 {steps}，因此最终控制方为 {final_holder} (穿透比例约 {final_ratio*100:.2f}%)。"
        )


def _build_config(  # noqa: PLR0913
    profiles: Path,
    shareholders: Path,
    embedding_model: str,
    chunk_size: int,
    chunk_overlap: int,
    top_k: int,
    reasoning_depth: int,
    neo4j_uri: Optional[str],
    neo4j_user: Optional[str],
    neo4j_password: Optional[str],
    neo4j_database: Optional[str],
) -> AppConfig:
    return AppConfig.from_cli(
        profiles_path=profiles,
        shareholders_path=shareholders,
        embedding_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        retriever_top_k=top_k,
        reasoning_depth=reasoning_depth,
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        neo4j_database=neo4j_database,
    )


def _service_from_cli(
    profiles: Path,
    shareholders: Path,
    embedding_model: str,
    chunk_size: int,
    chunk_overlap: int,
    top_k: int,
    reasoning_depth: int,
    neo4j_uri: Optional[str],
    neo4j_user: Optional[str],
    neo4j_password: Optional[str],
    neo4j_database: Optional[str],
) -> GraphRAGService:
    config = _build_config(
        profiles,
        shareholders,
        embedding_model,
        chunk_size,
        chunk_overlap,
        top_k,
        reasoning_depth,
        neo4j_uri,
        neo4j_user,
        neo4j_password,
        neo4j_database,
    )
    return GraphRAGService(config)


@app.command(help="自然而然的多轮问题：联合向量检索 + 图推理")
def query(
    question: str = typer.Argument(..., help="提问，如“某公司最大股东”"),
    profiles: Path = typer.Option(
        Path(__file__).parent / "data/company_profiles.json",
        "--profiles",
        help="公司画像 JSON",
        show_default=True,
    ),
    shareholders: Path = typer.Option(
        Path(__file__).parent / "data/shareholders.csv",
        "--shareholders",
        help="股权 CSV",
        show_default=True,
    ),
    embedding_model: str = typer.Option(
        "BAAI/bge-small-zh-v1.5",
        "--embedding-model",
        help="向量模型",
        show_default=True,
    ),
    chunk_size: int = typer.Option(512, "--chunk-size", show_default=True),
    chunk_overlap: int = typer.Option(80, "--chunk-overlap", show_default=True),
    top_k: int = typer.Option(2, "--top-k", show_default=True, help="RAG 检索 TopK"),
    reasoning_depth: int = typer.Option(
        2,
        "--reasoning-depth",
        show_default=True,
        help="股权穿透层级 (图谱推理深度)",
    ),
    neo4j_uri: Optional[str] = typer.Option(None, "--neo4j-uri", help="Neo4j bolt URI"),
    neo4j_user: Optional[str] = typer.Option(None, "--neo4j-user", help="Neo4j 用户名"),
    neo4j_password: Optional[str] = typer.Option(None, "--neo4j-password", help="Neo4j 密码"),
    neo4j_database: Optional[str] = typer.Option(None, "--neo4j-database", help="Neo4j 数据库"),
) -> None:
    service = _service_from_cli(
        profiles,
        shareholders,
        embedding_model,
        chunk_size,
        chunk_overlap,
        top_k,
        reasoning_depth,
        neo4j_uri,
        neo4j_user,
        neo4j_password,
        neo4j_database,
    )
    result = service.answer(question)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command(help="将 CSV 股权边写入 Neo4j")
def bootstrap(
    profiles: Path = typer.Option(
        Path(__file__).parent / "data/company_profiles.json",
        "--profiles",
        help="公司画像 JSON",
        show_default=True,
    ),
    shareholders: Path = typer.Option(
        Path(__file__).parent / "data/shareholders.csv",
        "--shareholders",
        help="股权 CSV",
        show_default=True,
    ),
    embedding_model: str = typer.Option(
        "BAAI/bge-small-zh-v1.5",
        "--embedding-model",
        help="向量模型",
        show_default=True,
    ),
    chunk_size: int = typer.Option(512, "--chunk-size", show_default=True),
    chunk_overlap: int = typer.Option(80, "--chunk-overlap", show_default=True),
    top_k: int = typer.Option(2, "--top-k", show_default=True, help="RAG 检索 TopK"),
    reasoning_depth: int = typer.Option(
        2,
        "--reasoning-depth",
        show_default=True,
        help="股权穿透层级",
    ),
    neo4j_uri: Optional[str] = typer.Option(
        None,
        "--neo4j-uri",
        help="Neo4j bolt URI，优先于环境变量",
    ),
    neo4j_user: Optional[str] = typer.Option(None, "--neo4j-user", help="Neo4j 用户名"),
    neo4j_password: Optional[str] = typer.Option(None, "--neo4j-password", help="Neo4j 密码"),
    neo4j_database: Optional[str] = typer.Option(None, "--neo4j-database", help="Neo4j 数据库"),
) -> None:
    service = _service_from_cli(
        profiles,
        shareholders,
        embedding_model,
        chunk_size,
        chunk_overlap,
        top_k,
        reasoning_depth,
        neo4j_uri,
        neo4j_user,
        neo4j_password,
        neo4j_database,
    )
    message = service.bootstrap_graph()
    typer.echo(message)


def run_cli() -> None:
    app()