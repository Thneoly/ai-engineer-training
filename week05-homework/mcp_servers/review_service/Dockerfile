FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

COPY mcp_servers/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY mcp_servers/common /app/common
COPY mcp_servers/review_service /app/service

CMD ["uvicorn", "service.server:app", "--host", "0.0.0.0", "--port", "8100"]
