# 作业二 · Graph RAG + Neo4j 多跳问答报告

## 目标与数据
- **任务**：构建一个能够结合文本向量检索与股权知识图谱推理的问答流程，回答“最大股东 / 最终控制人”等多跳问题。
- **语料**：`data/company_profiles.json` 提供公司画像文档，`data/shareholders.csv` 则列出投资方、被投方、持股比例与边类型。
- **嵌入模型**：`BAAI/bge-small-zh-v1.5`，通过 `llama_index` 的 HuggingFace 接口加载。

## 系统架构
1. **向量检索 (RAG)**：
	- 使用 `SentenceSplitter`(512/80) 切分公司画像，构建 `VectorStoreIndex` (SimpleVectorStore)。
	- `VectorIndexRetriever` 负责以 TopK 检索公司相关文档，输出文本证据与相似度。
2. **图谱推理**：
	- CSV 中的 `investor -> investee` 边会写入 Neo4j（若配置）或回退到 `networkx.DiGraph`。
	- `OwnershipReasoner` 以指定穿透深度沿着最大持股比例向上遍历，输出链路与累计比例。
3. **答案融合**：
	- 将检索出的公司名称与图谱链路结合，生成中文自然语言描述，并提供 joint score（0.7 * 文本相似度 + 0.3 * 第一层持股比例）。

## 使用方式
```bash
uv run python -m graph_rag.main query "A公司的最大股东是谁"
```
可与以下选项搭配：
- `--profiles / --shareholders`：自定义 JSON / CSV。 
- `--neo4j-uri/--neo4j-user/--neo4j-password/--neo4j-database`：连接远端 Neo4j；若省略则默认 networkx 内存图。
- `--reasoning-depth`：控制股权穿透层数（默认 2）。

若想将 CSV 边批量写入 Neo4j：
```bash
uv run python -m graph_rag.main bootstrap --neo4j-uri bolt://localhost:7687 --neo4j-user neo4j --neo4j-password xxx
```

## Neo4j Docker Compose 部署
已经提供 `docker-compose.neo4j.yml`，包含官方 `neo4j:5.18` 镜像、端口映射与 `APOC` 插件。首次使用可执行：

```bash
mkdir -p neo4j/{data,logs,plugins,import}
docker compose -f docker-compose.neo4j.yml up -d
```

> 默认账号密码写在 `NEO4J_AUTH=neo4j/neo4j_pass`，若要修改请同步更新 compose 文件和 CLI 中的 `--neo4j-password`（或环境变量 `NEO4J_PASSWORD`）。

部署完成后，按照顺序运行：

```bash
uv run python -m graph_rag.main bootstrap \
	--neo4j-uri bolt://localhost:7687 \
	--neo4j-user neo4j \
	--neo4j-password neo4j_pass

uv run python -m graph_rag.main query "A公司的最大股东是谁" \
	--neo4j-uri bolt://localhost:7687 \
	--neo4j-user neo4j \
	--neo4j-password neo4j_pass
```

当 Neo4j 连通后，日志会显示 `Connected to Neo4j...`，vector + graph 推理链路即全部落在数据库中。

如果希望“一键完成”上述步骤，可执行：

```bash
scripts/run_graph_rag.sh "A公司的最大股东是谁"
```

脚本会：
1. 自动创建 `neo4j/` 数据卷目录并通过 `docker compose -f docker-compose.neo4j.yml up -d` 启动图数据库；
2. 轮询健康检查直至 Neo4j 可用；
3. 调用 `bootstrap` 将 `shareholders.csv` 写入图谱；
4. 使用传入问题（默认同上）执行 `query`，打印整合后的答案与证据。

## 验证结果
执行 `uv run python -m graph_rag.main query "A公司的最大股东是谁"`，输出节选：

```
question: A公司的最大股东是谁
company: 晨曦能源集团股份有限公司
answer: 针对“A公司的最大股东是谁”，RAG 首先定位公司 晨曦能源集团股份有限公司，图谱推理链路为 曦光资本(45.0%) -> 皓月控股(60.0%)，因此最终控制方为 皓月控股 (穿透比例约 27.00%)。
```

- **graph_chain** 明确列出了每一层股权与累计比例，验证多跳推理正确。
- Neo4j 未配置时自动 fallback 至 NetworkX，保证零依赖体验。

## 后续可拓展点
1. **评估指标**：增加自动化单元测试（例如针对多家公司问题的快照对比）。
2. **Temporal Graph**：加入持股生效时间、投资轮次等属性，回答“截至某年”的问题。
3. **服务化**：暴露 FastAPI / gRPC 服务，便于与 Milvus FAQ 作业形成统一入口。

## 运行日志
```shell
./scripts/run_graph_rag.sh 
[info] Starting Neo4j via docker compose...
WARN[0000] /home/cc/Desktop/code/AIPro/ai-engineer-training/week03-homework-2/docker-compose.neo4j.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
[+] Running 1/1
 ✔ Container neo4j-graph-rag  Running                                                                                                           0.0s 
[info] Waiting for Neo4j bolt endpoint...
[info] Bootstrapping shareholder edges to Neo4j
[INFO] Loading embedding model: BAAI/bge-small-zh-v1.5
[INFO] Load pretrained SentenceTransformer: BAAI/bge-small-zh-v1.5
[INFO] 1 prompt is loaded, with the key: query
Parsing nodes: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████| 2/2 [00:00<00:00, 19.07it/s]
Generating embeddings: 100%|███████████████████████████████████████████████████████████████████████████████████████████| 3/3 [00:00<00:00, 14.89it/s]
[INFO] Connected to Neo4j, 图谱数据将存储在数据库中
Neo4j graph 数据已写入
[info] Running sample query: A公司的最大股东是谁
[INFO] Loading embedding model: BAAI/bge-small-zh-v1.5
[INFO] Load pretrained SentenceTransformer: BAAI/bge-small-zh-v1.5
[INFO] 1 prompt is loaded, with the key: query
Parsing nodes: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████| 2/2 [00:00<00:00, 28.84it/s]
Generating embeddings: 100%|███████████████████████████████████████████████████████████████████████████████████████████| 3/3 [00:00<00:00, 23.92it/s]
[INFO] Connected to Neo4j, 图谱数据将存储在数据库中
{
  "question": "A公司的最大股东是谁",
  "company": "晨曦能源集团股份有限公司",
  "answer": "针对“A公司的最大股东是谁”，RAG 首先定位公司 晨曦能源集团股份有限公司，图谱推理链路为 曦光资本(45.0%) -> 皓月控股(60.0%)，因此最终控制方为 皓月控股 (穿透比例约 27.00%)。",
  "evidence": {
    "document_snippet": "在股权结构上，曦光资本目前直接持有 A 公司 45% 的股权，是最大单一股东；青岚创投和北辰基金分别持有 30% 与 25%。此外，曦光资本自身由皓月控股（60%）与辰极投资（40%）共同持有，因此 A 公司最上层的最终实际控制人链路可追溯至皓月控股。",
    "retrieval_score": 0.4824,
    "graph_chain": [
      {
        "level": 1,
        "investor": "曦光资本",
        "target": "晨曦能源集团股份有限公司",
        "ratio": 0.45,
        "cumulative_ratio": 0.45,
        "relation": "shareholder"
      },
      {
        "level": 2,
        "investor": "皓月控股",
        "target": "曦光资本",
        "ratio": 0.6,
        "cumulative_ratio": 0.27,
        "relation": "shareholder"
      }
    ],
    "joint_score": 0.4726
  }
}
```