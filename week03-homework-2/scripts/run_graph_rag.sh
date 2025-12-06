#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

QUESTION="${1:-A公司的最大股东是谁}"
NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-neo4j_pass}"
NEO4J_DATABASE="${NEO4J_DATABASE:-neo4j}"

mkdir -p neo4j/data neo4j/logs neo4j/plugins neo4j/import

echo "[info] Starting Neo4j via docker compose..."
docker compose -f docker-compose.neo4j.yml up -d

echo "[info] Waiting for Neo4j bolt endpoint..."
READY=0
for _ in {1..30}; do
  if docker exec neo4j-graph-rag cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "RETURN 1" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 2
  echo "  - retrying..."
done

if [[ "$READY" != "1" ]]; then
  echo "[error] Neo4j is not ready after waiting ~60s"
  exit 1
fi

echo "[info] Bootstrapping shareholder edges to Neo4j"
NEO4J_URI="$NEO4J_URI" \
NEO4J_USER="$NEO4J_USER" \
NEO4J_PASSWORD="$NEO4J_PASSWORD" \
NEO4J_DATABASE="$NEO4J_DATABASE" \
  uv run python -m graph_rag.main bootstrap

echo "[info] Running sample query: $QUESTION"
NEO4J_URI="$NEO4J_URI" \
NEO4J_USER="$NEO4J_USER" \
NEO4J_PASSWORD="$NEO4J_PASSWORD" \
NEO4J_DATABASE="$NEO4J_DATABASE" \
  uv run python -m graph_rag.main query "$QUESTION"
