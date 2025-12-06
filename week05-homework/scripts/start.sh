#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
ENV_FILE="$PROJECT_ROOT/.env"

if [[ -f "$ENV_FILE" ]]; then
  echo "[start] 读取 .env 并导入变量"
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
fi

if [[ -z "${DASHSCOPE_API_KEY:-}" ]]; then
  echo "[start] 缺少 DASHSCOPE_API_KEY，无法启动远程服务" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[start] 未安装 docker，请先安装 Docker Desktop / Engine" >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_BIN=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_BIN=(docker-compose)
else
  echo "[start] 未找到 docker compose，请安装新版 docker 或 docker-compose" >&2
  exit 1
fi

cd "$PROJECT_ROOT"

echo "[start] 启动 MCP 服务（不重新构建镜像）..."
"${COMPOSE_BIN[@]}" -f "$COMPOSE_FILE" up -d "$@"

echo "[start] 容器状态："
"${COMPOSE_BIN[@]}" -f "$COMPOSE_FILE" ps
*** End Patch