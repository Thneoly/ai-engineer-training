# Milvus FAQ 检索系统实验报告

## 1. 项目概述
- **目标**：构建一个基于 LlamaIndex + Milvus 的 FAQ 检索服务，支持热更新与 RESTful API。
- **入口**：`python -m milvus_faq.main`，通过子命令支持 `reindex` / `query` / `serve`。
- **数据源**：`milvus_faq/data/faqs.json`，包含 5 条示例 FAQ，可在运行期替换为业务数据。

## 2. 系统架构
| 模块 | 说明 |
| --- | --- |
| `FAQCorpus` | 加载 JSON FAQ，并将问答映射为 `Document` 元数据（类别、标签）。 |
| `FAQRetrieverService` | 负责索引重建、向量检索、热更新；内部封装 LlamaIndex + Milvus/SimpleVectorStore。 |
| FastAPI | `/query` 提供检索接口，`/reload` 触发热更新；内置 CORS。 |
| CLI | `query`、`reindex`、`serve` 子命令，便于脚本化操作。 |

**切片策略**：使用 `SentenceSplitter(chunk_size=512, overlap=80)`；兼顾中文语义切分与重叠上下文。

**向量存储**：
- 默认读取 `MILVUS_URI` 等环境变量直连 Milvus；
- 未配置 Milvus 时自动回退 `SimpleVectorStore`，保证开发体验。

**Embedding**：`BAAI/bge-small-zh-v1.5`（HuggingFace sentence-transformers），通过 `llama-index-embeddings-huggingface` 提供本地推理。

## 3. 使用指南
1. 安装依赖：`UV_INDEX_URL=https://pypi.org/simple uv sync`
2. 重建索引：
	```bash
	uv run python -m milvus_faq.main reindex
	```
3. 单次问答：
	```bash
	uv run python -m milvus_faq.main query "如何退货"
	```
4. 启动 API：
	```bash
	uv run python -m milvus_faq.main serve --host 0.0.0.0 --port 8000
	```
	- POST `/query`：`{"question": "如何退货？", "top_k": 3}`
	- POST `/reload`：即时重新索引（支持热更新知识库）。

## 4. 验证结果
- `uv run python -m milvus_faq.main reindex`
  - ✅ 成功：5 条 FAQ 全部切片入库，日志显示索引构建完成。
- `uv run python -m milvus_faq.main query "如何退货"`
  - ✅ 返回预期答案：“请在订单完成后30天内登录个人中心…”，Top-5 支持证据按相似度排序。

## 5. 关键工程点
- **配置抽象**：`AppConfig`+`MilvusConfig` 统一集中，支持命令行覆盖。
- **可插拔向量库**：Milvus 首选、SimpleVectorStore 兜底，便于本地调试。
- **热更新**：FastAPI `/reload`、CLI `reindex` 共用同一 `refresh()` 流程。
- **可解释性**：返回 `support` 列表（分数、原问答、截断片段），方便前端展示检索链路。

## 6. 后续优化建议
1. 对接真实 Milvus（standalone/cluster），并开启 Hybrid Search（BM25 + 向量）。
2. 增加向量去重与分层召回策略，提升长文档覆盖率。
3. 在 API 中集成流式大模型生成（如调用 `response_synthesizer`）提供更自然回答。
4. 构建 CI，自动运行 `reindex` + 典型 `query`，保障数据热更新流程的稳定性。

## 7. 附录：典型运行日志
以下为 `reindex` 和 `query` 的关键日志片段，确认系统行为：

```
$ uv run python -m milvus_faq.main reindex
[INFO] Loading embedding model: BAAI/bge-small-zh-v1.5
[INFO] Parsed 5 FAQ entries into 5 documents / 8 nodes
[INFO] Vector index rebuilt successfully (SimpleVectorStore)

$ uv run python -m milvus_faq.main query "如何退货"
{
  "question": "如何退货",
  "answer": "请在订单完成后30天内登录个人中心，选择“申请退货”...",
  "support": [
    {"score": 0.78, "faq": "如何退货", "category": "售后"},
    {...}
  ]
}
```

如需长时间运行在线服务，建议配合 `uvicorn --reload` 或容器化部署，并在生产环境中替换为真实 Milvus 集群。