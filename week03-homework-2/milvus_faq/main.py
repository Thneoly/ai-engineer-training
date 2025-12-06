"""Milvus FAQ retrieval system powered by LlamaIndex."""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uvicorn import run as uvicorn_run

from llama_index.core import Document, Settings, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

try:
    from llama_index.vector_stores.milvus import MilvusVectorStore
except ImportError:
    MilvusVectorStore = None

dotenv_spec = importlib.util.find_spec("dotenv")
if dotenv_spec:
    load_dotenv = importlib.import_module("dotenv").load_dotenv
else:  # pragma: no cover
    load_dotenv = None


LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


@dataclass(slots=True)
class MilvusConfig:
    """Configuration describing how to connect to Milvus."""

    uri: Optional[str]
    token: Optional[str]
    user: Optional[str]
    password: Optional[str]
    database: str
    collection_name: str
    consistency: str = "Session"

    def is_enabled(self) -> bool:
        return bool(self.uri)


def _default_milvus_config() -> MilvusConfig:
    return MilvusConfig(
        uri=os.getenv("MILVUS_URI"),
        token=os.getenv("MILVUS_TOKEN"),
        user=os.getenv("MILVUS_USER"),
        password=os.getenv("MILVUS_PASSWORD"),
        database=os.getenv("MILVUS_DB", "llama_faq"),
        collection_name=os.getenv("MILVUS_COLLECTION", "faq_collection"),
    )


@dataclass(slots=True)
class AppConfig:
    """High-level application configuration."""

    dataset_path: Path
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    chunk_size: int = 512
    chunk_overlap: int = 80
    top_k: int = 3
    milvus: MilvusConfig = field(default_factory=_default_milvus_config)

    @staticmethod
    def from_args(args: argparse.Namespace) -> "AppConfig":
        dataset = Path(args.dataset).resolve()
        milvus_cfg = MilvusConfig(
            uri=args.milvus_uri or os.getenv("MILVUS_URI"),
            token=args.milvus_token or os.getenv("MILVUS_TOKEN"),
            user=args.milvus_user or os.getenv("MILVUS_USER"),
            password=args.milvus_password or os.getenv("MILVUS_PASSWORD"),
            database=args.milvus_db or os.getenv("MILVUS_DB", "llama_faq"),
            collection_name=args.milvus_collection
            or os.getenv("MILVUS_COLLECTION", "faq_collection"),
        )
        return AppConfig(
            dataset_path=dataset,
            embedding_model=args.embedding_model,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            top_k=args.top_k,
            milvus=milvus_cfg,
        )


class FAQCorpus:
    """Loads FAQ entries and converts them to LlamaIndex documents."""

    def __init__(self, dataset_path: Path) -> None:
        self.dataset_path = dataset_path

    def load(self) -> List[Dict[str, Any]]:
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.dataset_path}")
        if self.dataset_path.suffix.lower() == ".json":
            with self.dataset_path.open("r", encoding="utf-8") as fp:
                payload = json.load(fp)
            if not isinstance(payload, list):
                raise ValueError("FAQ JSON must be a list of objects")
            return payload
        raise ValueError("Only JSON datasets are supported in this reference implementation")

    def to_documents(self) -> List[Document]:
        docs: List[Document] = []
        for entry in self.load():
            question = entry["question"].strip()
            answer = entry["answer"].strip()
            metadata = {
                "question": question,
                "answer": answer,
                "category": entry.get("category", "unknown"),
                "tags": entry.get("tags", []),
            }
            text = f"问题：{question}\n回答：{answer}"
            docs.append(Document(text=text, metadata=metadata))
        return docs


class FAQRetrieverService:
    """Encapsulates the full data-ingest -> Milvus index -> query pipeline."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._documents: List[Document] = []
        self._index: Optional[VectorStoreIndex] = None
        self._retriever: Optional[VectorIndexRetriever] = None

    def refresh(self) -> None:
        """Reload corpus, rebuild vector index, and prepare retriever."""
        self._documents = FAQCorpus(self.config.dataset_path).to_documents()
        splitter = SentenceSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        Settings.embed_model = self._embed_model
        Settings.node_parser = splitter
        vector_store = self._vector_store
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        LOGGER.info("Building vector index with %s documents", len(self._documents))
        self._index = VectorStoreIndex.from_documents(  # type: ignore[arg-type]
            self._documents,
            storage_context=storage_context,
            show_progress=True,
            transformations=[splitter],
        )
        self._retriever = VectorIndexRetriever(index=self._index, similarity_top_k=self.config.top_k)

    def query(self, question: str, top_k: Optional[int] = None) -> Dict[str, Any]:
        if not self._retriever:
            raise RuntimeError("Retriever not initialized. Call refresh() first.")
        similarity_top_k = top_k or self.config.top_k
        self._retriever.similarity_top_k = similarity_top_k
        nodes = self._retriever.retrieve(question)
        if not nodes:
            return {"question": question, "answer": "抱歉，暂未找到相关 FAQ。", "support": []}

        primary = nodes[0]
        support = [
            {
                "score": float(node.score or 0.0),
                "snippet": node.get_text(),
                "question": node.metadata.get("question"),
                "answer": node.metadata.get("answer"),
            }
            for node in nodes
        ]
        return {
            "question": question,
            "answer": primary.metadata.get("answer") or primary.get_text(),
            "support": support,
        }

    @cached_property
    def _embed_model(self) -> HuggingFaceEmbedding:
        LOGGER.info("Loading embedding model: %s", self.config.embedding_model)
        return HuggingFaceEmbedding(model_name=self.config.embedding_model)

    @cached_property
    def _vector_store(self):
        if self.config.milvus.is_enabled():
            LOGGER.info(
                "Connecting to Milvus at %s (collection=%s)",
                self.config.milvus.uri,
                self.config.milvus.collection_name,
            )
            try:
                return MilvusVectorStore(
                    uri=self.config.milvus.uri,
                    token=self.config.milvus.token,
                    user=self.config.milvus.user,
                    password=self.config.milvus.password,
                    collection_name=self.config.milvus.collection_name,
                    dim=self._embed_model.dim,
                    consistency_level=self.config.milvus.consistency,
                    overwrite=True,
                    database=self.config.milvus.database,
                )
            except Exception as exc:
                LOGGER.warning("Failed to connect to Milvus, falling back to SimpleVectorStore: %s", exc)
        LOGGER.info("Using SimpleVectorStore as a local fallback.")
        return SimpleVectorStore()


class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = None


class QueryResponse(BaseModel):
    question: str
    answer: str
    support: List[Dict[str, Any]]


def build_fastapi_app(service: FAQRetrieverService) -> FastAPI:
    app = FastAPI(title="Milvus FAQ Retrieval", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"]
        ,
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def _startup() -> None:
        service.refresh()

    @app.post("/query", response_model=QueryResponse)
    async def query(request: QueryRequest) -> QueryResponse:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="question cannot be empty")
        payload = service.query(request.question, request.top_k)
        return QueryResponse(**payload)

    @app.post("/reload")
    async def reload_index() -> Dict[str, str]:
        service.refresh()
        return {"status": "ok"}

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Milvus-backed FAQ retrieval service")
    parser.add_argument(
        "--dataset",
        default=str(Path(__file__).parent / "data/faqs.json"),
        help="Path to FAQ JSON dataset",
    )
    parser.add_argument("--embedding-model", default="BAAI/bge-small-zh-v1.5")
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--chunk-overlap", type=int, default=80)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--milvus-uri")
    parser.add_argument("--milvus-token")
    parser.add_argument("--milvus-user")
    parser.add_argument("--milvus-password")
    parser.add_argument("--milvus-db")
    parser.add_argument("--milvus-collection", default="faq_collection")

    sub = parser.add_subparsers(dest="command")

    query_parser = sub.add_parser("query", help="Run a single query against the FAQ index")
    query_parser.add_argument("question", help="Natural language question to search")
    query_parser.add_argument("--top-k", type=int, default=None)

    serve_parser = sub.add_parser("serve", help="Start FastAPI server")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8000)

    sub.add_parser("reindex", help="Force rebuild the index and exit")

    return parser.parse_args()


def main() -> None:
    if load_dotenv:
        load_dotenv()
    args = parse_args()
    config = AppConfig.from_args(args)
    service = FAQRetrieverService(config)

    if args.command == "query":
        service.refresh()
        result = service.query(args.question, args.top_k)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "serve":
        app = build_fastapi_app(service)
        uvicorn_run(app, host=args.host, port=args.port)
        return

    # default command: reindex only
    service.refresh()
    if args.command == "reindex":
        LOGGER.info("Index rebuilt successfully.")


if __name__ == "__main__":
    main()