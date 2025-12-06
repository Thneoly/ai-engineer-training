# 第五周作业
## 基于MCP协议的多代理文章自动编写系统

### 项目概述
开发一个使用MCP (Model Context Protocol) 的多代理系统，能够协作完成文章写作任务。系统包含四个专业化代理，按顺序协作完成从研究到最终成稿的完整流程。

### 核心功能要求
- **输入**：用户问题（如"帮我写一篇关于AI Agent的文章"）
- **输出**：完成的文章文档和执行过程记录

### 系统架构
系统需要包含以下四个代理，按顺序协作：

1. **研究代理 (Research Agent)**
   - 使用搜索工具收集相关信息
   - 输出结构化的研究资料

2. **撰写代理 (Writing Agent)**
   - 基于研究结果生成文章初稿
   - 支持调整文章风格和长度

3. **审核代理 (Review Agent)**
   - 检查内容质量和逻辑一致性
   - 提供修改建议

4. **润色代理 (Polishing Agent)**
   - 优化语言表达和文章结构
   - 确保风格一致性

### 技术实现
- 可以使用现有的MCP库
- 代理间通过结构化消息进行通信
- 终端实时展示协作过程
- 生成: 示例输出文档（展示完整代理协作过程与最终成果）

### 扩展项（选做）
 - 实现基于MCP上下文的自动重试：当代理执行失败时，系统保留完整上下文并尝试替代方案 
   - 设置三级重试策略：
     * 一级：相同代理重新执行（最多2次）
     * 二级：切换至备用代理执行（如审核失败转由高级审核代理处理）
     * 三级：向用户请求补充信息
   - 所有重试过程需记录在最终文档的"异常处理日志"部分 


### 提交要求
在以下目录完成编码作业：
- [week05-homework/multi-agent](./multi-agent)

其中:
- `main.py` 是作业入口文件
- `report.md` 是示例输出文档（展示完整代理协作过程与最终成果）

### 提交方式
1. Fork本仓库
2. 在你的仓库中完成代码
3. 在【极客时间】提交fork仓库链接，格式为：
```
https://github.com/your-username/ai-engineer-training/tree/main/week05-homework
```

### 运行方式（最新版流程）

#### 1. 环境准备
- 推荐使用 [uv](https://github.com/astral-sh/uv) 管理依赖、Docker (含 `docker compose`) 运行远程 MCP 服务。
- 在项目根目录创建 `.env`：
  ```bash
  DASHSCOPE_API_KEY=你的千问Key
  MODEL_NAME=qwen-plus        # 可选覆盖模型
  RESEARCH_MOCK=false         # 可针对各代理设置 *_MOCK
  ```

#### 2. 启动远程 MCP SSE 服务（推荐）
- **一键部署并构建**：
  ```bash
  ./scripts/deploy.sh
  ```
  自动执行 `docker compose up --build -d`，校验 `.env` 与 Docker 依赖，可透传 compose 额外参数。
- **常用脚本速览**：
  | 脚本 | 功能 | 说明 |
  | --- | --- | --- |
  | `./scripts/deploy.sh` | 首次构建并启动全部服务 | 适合升级或首次部署，可附加 `service` 名称或 compose 参数 |
  | `./scripts/start.sh` | 启动已有容器（不重建） | 等价于 `docker compose up -d`，同样会加载 `.env` |
  | `./scripts/stop.sh` | 安全停止服务 | 默认 `docker compose stop`，结束后输出 `docker compose ps` |
  | `docker compose down` | 彻底清理 | 停止并删除容器/网络，需要时手动执行 |
- **手动模式**（如需定制）：
  ```bash
  docker compose up --build
  ```
  - 四个服务分别监听 `8101-8104`，已经配置 `/healthz` 健康检查与 json-file 日志滚动。
  - 服务加入同一 `mcp-net` 网络，便于 LangGraph 或其他 MCP 客户端通信。

#### 3. 执行 LangGraph 多代理工作流
```bash
uv sync                                      # 首次安装依赖
uv run python -m multi-agent.main \
  --prompt "帮我写一篇关于 AI Agent 如何提效知识管理" \
  --tone "专业且友好" --length "1200 字左右" --audience "企业数字化负责人"
```
- 默认 `--mcp-mode remote`，使用上一步启动的 SSE 服务。
- 通过 `--model` 指定千问模型；`--research-url / --writing-url / ...` 可覆盖远程端点；`--service-timeout` 控制 SSE 调用超时。
- 研究代理实时调用 ddgs 搜索并把引用写入报告（`multi-agent/report.md`）。

#### 4. 本地/离线回退
当没有 Docker 或外网时，可改用本地链路：
```bash
uv run python -m multi-agent.main --prompt "离线演示" --mock --mcp-mode local
```
这会启用项目内置的 `LocalFallbackLLM` 模拟四个代理的响应，仍然会生成报告文件，便于快速演示流程。

#### 5. 调试与观测
- 查看容器状态：`docker compose ps`，实时日志：`docker compose logs -f`。
- 单独调试研究代理：
  ```bash
  curl -N "http://localhost:8101/events?prompt=%E5%B8%AE%E6%88%91%E6%9F%A5%E6%89%BEAI%20Agent"
  ```
  返回标准 SSE 流（包含 `log` / `result` 事件），可直接被任意支持 EventSource 的 MCP 客户端或现有 LangGraph orchestrator 消费。

> 如需将 LangGraph 客户端部署在其他机器，只需把上面的 `/events` 地址改成容器所在的可达地址即可。

### 使用输出
```shell
(demo) cc@cc-pc:~/Desktop/code/AIPro/ai-engineer-training/week05-homework$ docker compose up -d
WARN[0000] /home/cc/Desktop/code/AIPro/ai-engineer-training/week05-homework/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
[+] Running 5/5
 ✔ Network week05-homework_mcp-net               Created                                                           0.0s 
 ✔ Container week05-homework-writing-service-1   Started                                                           0.3s 
 ✔ Container week05-homework-review-service-1    Started                                                           0.3s 
 ✔ Container week05-homework-research-service-1  Started                                                           0.4s 
 ✔ Container week05-homework-polish-service-1    Started                                                           0.3s 
(demo) cc@cc-pc:~/Desktop/code/AIPro/ai-engineer-training/week05-homework$ uv run python -m multi-agent.main \
  --prompt "帮我写一篇关于 AI Agent 如何提效知识管理" \
  --tone "专业且友好" --length "1200 字左右" --audience "企业数字化负责人"
Installed 1 package in 1ms
[LangGraph] research 完成：完成研究资料
[LangGraph] writing 完成：生成文章初稿
[LangGraph] review 完成：文章系统阐述了AI Agent在知识管理中的变革作用，逻辑清晰、观点前瞻，但缺乏对关键数据和案例的技术来源标注，影响内容可验证性。
[LangGraph] polish 完成：润色完成，生成终稿
[LangGraph] 执行完成，报告已写入 /home/cc/Desktop/code/AIPro/ai-engineer-training/week05-homework/multi-agent/report.md
```