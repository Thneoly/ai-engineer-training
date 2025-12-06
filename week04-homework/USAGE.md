# 智能客服使用手册

> 适用于 `week04-homework/smart_customer_service` 工程，覆盖环境准备、运行方式、接口说明以及测试用交互语录。

## 1. 环境准备

| 组件 | 版本 / 要求 | 说明 |
| --- | --- | --- |
| Python | 3.11+ | 建议使用 `pyenv` 或系统自带 Python 3.11 |
| [uv](https://github.com/astral-sh/uv) | 最新版 | 用于安装依赖并运行命令 |
| DashScope API Key（可选） | `SMART_CS_LLM_PROVIDER=tongyi` 时必需 | 访问千问模型 |

初始化步骤：

```bash
# 进入本周目录
cd week04-homework

# 安装依赖
uv sync
```

> 已提供 `.python-version`/`.venv` 时，可直接激活对应环境再执行 `uv` 命令。

## 2. 启动方式

### 2.1 启动 FastAPI 后端

```bash
uv run python -m smart_customer_service.main
```

默认监听 `0.0.0.0:8000`，可通过以下变量覆盖：

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `SMART_CS_HOST` | `0.0.0.0` | 绑定地址 |
| `SMART_CS_PORT` | `8000` | 监听端口 |
| `SMART_CS_SYSTEM_PROMPT` | 见代码默认值 | 客服语气提示词 |
| `SMART_CS_LLM_PROVIDER` | `local` | `local` / `tongyi` |
| `SMART_CS_DASHSCOPE_MODEL` | `qwen-plus` | 切换千问模型 |

健康检查：

```bash
curl http://127.0.0.1:8000/health | jq
```

### 2.2 启动 Gradio Web 前端

一键脚本（自动管理后端进程）：

```bash
chmod +x scripts/run_with_gradio.sh
./scripts/run_with_gradio.sh
```

或单独指定后端地址：

```bash
SMART_CS_GRADIO_BACKEND=http://127.0.0.1:8000 \
uv run python -m smart_customer_service.gradio_ui
```

Gradio 监听 `SMART_CS_GRADIO_HOST:SMART_CS_GRADIO_PORT`（默认 `0.0.0.0:7860`）。

## 3. 核心接口速览

| 方法 | 路径 | 功能 | 示例 |
| --- | --- | --- | --- |
| `GET` | `/health` | 查看 LLM provider、插件加载状态、路由可用性 | `curl http://127.0.0.1:8000/health` |
| `POST` | `/chat` | 多轮客服入口，Body: `{"session_id":"demo","message":"查订单"}` | 详见下方交互语录 |
| `POST` | `/reload/model` | 热更新模型/提示词 | `{"provider":"tongyi","system_prompt":"新语气"}` |
| `POST` | `/reload/plugins` | 热加载 `plugins/` 目录 | 无需 body |

所有接口均返回 JSON，`/chat` 附带 `intent`、`slots` 与 `tool_events`，方便调试。

## 4. 热更新操作

### 4.1 切换到千问模型

```bash
curl -X POST http://127.0.0.1:8000/reload/model \
     -H "Content-Type: application/json" \
     -d '{
           "provider": "tongyi",
           "dashscope_model": "qwen-max",
           "system_prompt": "You are a concise English agent.",
           "temperature": 0.1
         }'
```

### 4.2 重新加载插件

```bash
curl -X POST http://127.0.0.1:8000/reload/plugins
```

收到 `{"status":"ok"}` 即表示新插件已接入。

## 5. 自动化测试

```bash
uv run pytest
```

- `tests/test_invoice_plugin.py`：验证发票插件可正确写入邮箱。
- `tests/test_hot_reload.py`：验证模型与插件热更新后，会话上下文保持有效。

## 6. 测试用交互语录（推荐在 Gradio 或 `curl` 验证）

| 场景 | 用户输入顺序 | 期望助手行为 | 涉及工具 |
| --- | --- | --- | --- |
| 订单物流查询（先问后补单号） | 1. `查订单` → 2. `订单号202312345` | 第一句提示“请提供订单号”；第二句调用 `query_order`，返回状态“已发货”、顺丰运单 `SF123456789`，给出预计送达日期 | `OrderTools.query_order` |
| 直接查询 132465 物流 | `查订单132465的物流` | 直接识别 6 位数字，返回菜鸟裹裹物流、最新进度“杭州发出”及次日送达时间 | `OrderTools.query_order` |
| 退款申请 | `我要为订单202399999申请退款，商品有质量问题` | 检查订单状态（该单已退款完成），提示退款已完成或符合业务规则的说明 | `OrderTools.request_refund` |
| 发票开具 | 1. `帮我开票` → 2. `订单202312345` → 3. `邮箱 test@example.com` | 引导补齐订单号和邮箱，完成后提示“已向 test@example.com 发送电子发票” | 发票插件 `InvoicePlugin` |
| 一般问答 | `你们客服的服务时间是？` | 返回内置客服提示词中的营业时间说明，无需工具调用 | LLM 回复 |

> 若通过 `curl` 驱动同一会话，请复用同一个 `session_id`，以便多轮追问生效：
>
> ```bash
> curl -X POST http://127.0.0.1:8000/chat \
>      -H "Content-Type: application/json" \
>      -d '{"session_id":"demo","message":"查订单"}'
> ```
>
> ```bash
> curl -X POST http://127.0.0.1:8000/chat \
>      -H "Content-Type: application/json" \
>      -d '{"session_id":"demo","message":"订单号202312345"}'
> ```

## 7. 常见问题排查

1. **端口占用**：运行脚本时如果提示 8000 已被占用，可先停止旧进程或设置 `SMART_CS_PORT=8010`。
2. **Gradio 超时**：设置 `SMART_CS_GRADIO_TIMEOUT`（默认 30s）避免长时间调用导致前端报错。
3. **无权访问千问**：检查 `DASHSCOPE_API_KEY` 是否导出且额度充足；如不需要外部模型，可把 provider 切回 `local`。
4. **插件逻辑变化**：修改 `plugins/` 下文件后调用 `/reload/plugins`，无需重启服务。

---
若还有定制化诉求，可在 `USAGE.md` 上继续补充场景或 FAQ。祝体验愉快！
