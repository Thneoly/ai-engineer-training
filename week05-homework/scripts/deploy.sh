#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
ENV_FILE="$PROJECT_ROOT/.env"

if [[ -f "$ENV_FILE" ]]; then
  echo "[deploy] 检测到 .env，加载环境变量"
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
fi

if [[ -z "${DASHSCOPE_API_KEY:-}" ]]; then
  echo "[deploy] 需要先在环境变量或 .env 中设置 DASHSCOPE_API_KEY" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[deploy] 未检测到 docker，请先安装 Docker Desktop / Engine" >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_BIN=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_BIN=(docker-compose)
else
  echo "[deploy] 未找到 docker compose，请安装新版 docker 或 docker-compose" >&2
  exit 1
fi

cd "$PROJECT_ROOT"

echo "[deploy] 开始构建并启动所有 MCP 服务..."
"${COMPOSE_BIN[@]}" -f "$COMPOSE_FILE" up --build -d "$@"

echo "[deploy] 当前容器状态："
"${COMPOSE_BIN[@]}" -f "$COMPOSE_FILE" ps

echo "[deploy] 如需查看实时日志，可执行："
echo "${COMPOSE_BIN[*]} -f $COMPOSE_FILE logs -f"
