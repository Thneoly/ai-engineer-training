# 狼人杀多智能体游戏 - Docker 镜像
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml ./
COPY uv.toml ./

# 安装 uv 和项目依赖
RUN pip install uv && \
    uv pip install --system -e .

# 额外安装 Streamlit
RUN uv pip install --system streamlit

# 复制项目文件
COPY werewolf/ ./werewolf/
COPY docs/ ./docs/
COPY README.md ./

# 创建日志目录
RUN mkdir -p logs

# 暴露端口
EXPOSE 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 启动 Streamlit
CMD ["streamlit", "run", "werewolf/web_ui.py", "--server.port=8501", "--server.address=0.0.0.0"]
