# 快速开始指南

本指南将帮助你快速启动狼人杀多智能体游戏。

## 📋 前置要求

### 系统要求
- **操作系统**: Linux / macOS / Windows (WSL)
- **Python**: 3.11 或更高版本
- **包管理器**: uv（推荐）或 pip

### API 密钥
- **阿里云 DashScope API Key** - [免费注册](https://dashscope.aliyun.com/)
  - 新用户有免费额度
  - 每月前 100 万 tokens 免费

---

## 🚀 5 分钟快速启动

### 步骤 1: 克隆项目

```bash
git clone <your-repo-url>
cd week11-homework
```

### 步骤 2: 安装 uv（如果未安装）

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 步骤 3: 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
nano .env  # 或使用你喜欢的编辑器
```

在 `.env` 文件中添加：
```bash
DASHSCOPE_API_KEY=sk-your-api-key-here
```

### 步骤 4: 安装依赖

```bash
# 使用 uv 安装（推荐）
uv pip install -e .

# 或使用 pip
pip install -e .
```

### 步骤 5: 运行游戏！

```bash
python -m werewolf.main
```

就这么简单！🎉

---

## 📖 详细说明

### 项目结构

```
week11-homework/
├── werewolf/           # 主要代码
│   ├── __init__.py
│   ├── main.py        # 游戏入口
│   ├── game.py        # 游戏逻辑
│   ├── agents.py      # Agent 定义
│   ├── tools.py       # 工具函数
│   ├── config.py      # 配置文件
│   └── memories.py    # 记忆系统
├── docs/              # 文档
│   ├── DESIGN.md
│   ├── USAGE.md
│   └── ...
├── logs/              # 日志输出
├── .env.example       # 环境变量模板
├── pyproject.toml     # 项目配置
└── README.md          # 项目说明
```

### 游戏配置

默认配置（在 `werewolf/config.py`）：

```python
PLAYERS = [
    {"name": "Alpha", "role": "werewolf"},   # 狼人
    {"name": "Beta", "role": "werewolf"},    # 狼人
    {"name": "Alice", "role": "villager"},   # 村民
    {"name": "Bob", "role": "villager"},     # 村民
    {"name": "Charlie", "role": "villager"}, # 村民
    {"name": "David", "role": "villager"},   # 村民
]

MAX_ROUNDS = 10  # 最大回合数
```

### 日志文件

每次游戏会生成两个日志文件：

```bash
logs/
├── werewolf_game_20241206_143025.txt   # 文本日志
└── werewolf_game_20241206_143025.json  # JSON 日志（包含记忆）
```

---

## 🎮 游戏流程

### 完整流程

```
1. 游戏开始
   ↓
2. 狼人确认环节（狼人知道队友）
   ↓
3. 夜晚阶段（狼人协商淘汰目标）
   ↓
4. 白天讨论（所有玩家发言）
   ↓
5. 投票淘汰（全员投票）
   ↓
6. 胜负判定
   ├─ 所有狼人被淘汰 → 村民获胜 ✅
   ├─ 狼人数量 ≥ 村民数量 → 狼人获胜 ✅
   └─ 继续游戏 → 回到步骤 3
```

### 胜利条件

- **村民获胜**: 淘汰所有狼人
- **狼人获胜**: 狼人数量 ≥ 村民数量

---

## 🛠️ 自定义配置

### 修改玩家数量

编辑 `werewolf/config.py`:

```python
PLAYERS = [
    {"name": "Alpha", "role": "werewolf"},
    {"name": "Beta", "role": "werewolf"},
    {"name": "Gamma", "role": "werewolf"},  # 添加第三个狼人
    {"name": "Alice", "role": "villager"},
    {"name": "Bob", "role": "villager"},
    {"name": "Charlie", "role": "villager"},
    {"name": "David", "role": "villager"},
    {"name": "Eve", "role": "villager"},    # 添加更多村民
]
```

**注意**: 保持狼人和村民的平衡，推荐比例 1:2 或 1:3。

### 修改模型参数

编辑 `werewolf/agents.py`:

```python
# 模型选择
llm_model = "qwen-plus"  # 可选: qwen-turbo, qwen-max

# 温度设置（控制创造性）
LLM_TEMPERATURE = 0.7    # 0.0-1.0，越高越有创造性

# Agent 迭代次数
max_iter = 5             # 增加以支持更复杂的推理
```

### 修改最大回合数

编辑 `werewolf/config.py`:

```python
MAX_ROUNDS = 10  # 修改为你想要的回合数
```

---

## 🔍 查看游戏日志

### 实时查看

```bash
# 运行游戏并实时查看输出
python -m werewolf.main | tee output.txt
```

### 查看历史日志

```bash
# 查看最新的文本日志
cat logs/werewolf_game_*.txt | tail -n 100

# 查看 JSON 日志（记忆数据）
cat logs/werewolf_game_*.json | jq '.memories'

# 搜索特定玩家的行动
grep "Alpha" logs/werewolf_game_*.txt
```

---

## 🧪 测试与验证

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_agents.py

# 查看覆盖率
pytest --cov=werewolf
```

### 验证配置

```bash
# 检查环境变量
python -c "import os; print(os.getenv('DASHSCOPE_API_KEY'))"

# 测试 API 连接
python -c "
import os
from openai import OpenAI
client = OpenAI(
    api_key=os.getenv('DASHSCOPE_API_KEY'),
    base_url='https://dashscope.aliyuncs.com/compatible-mode/v1'
)
response = client.chat.completions.create(
    model='qwen-plus',
    messages=[{'role': 'user', 'content': '你好'}]
)
print('API 连接成功！')
"
```

---

## ❓ 常见问题

### Q1: 提示 "DASHSCOPE_API_KEY not found"

**解决方案**:
```bash
# 确保 .env 文件存在
ls -la .env

# 确保 .env 文件内容正确
cat .env

# 确保环境变量已加载
source .env  # 或重启终端
```

### Q2: 游戏卡住不动

**可能原因**:
1. API 限流 - 等待几秒后重试
2. 网络问题 - 检查网络连接
3. API Key 无效 - 验证 API Key

**解决方案**:
```bash
# 查看详细错误
python -m werewolf.main --verbose

# 检查 API Key
curl -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-plus","messages":[{"role":"user","content":"test"}]}'
```

### Q3: 游戏结果不符合预期

**可能原因**:
1. Agent 迭代次数不足
2. 温度设置过高/过低
3. Prompt 不够清晰

**解决方案**:
```python
# 增加迭代次数
max_iter = 10  # 在 agents.py 中

# 调整温度
LLM_TEMPERATURE = 0.5  # 更保守
LLM_TEMPERATURE = 0.9  # 更有创造性

# 优化 Prompt（在 config.py 中）
```

### Q4: 内存占用过高

**解决方案**:
```python
# 限制记忆条目数量
max_memory_items = 50  # 在 memories.py 中

# 定期清理旧记忆
memory.clear_old_entries(age_limit=100)
```

### Q5: 游戏速度太慢

**优化建议**:
1. 使用 `qwen-turbo` 代替 `qwen-plus`
2. 减少 `max_iter` 次数
3. 减少玩家数量
4. 缩短 Prompt 长度

---

## 🎯 进阶使用

### 启用 CrewAI 追踪

在 `.env` 中添加：
```bash
CREWAI_TRACING_ENABLED=true
```

每次游戏后会生成追踪链接，可查看详细执行过程。

### 调试模式

```bash
# 启用详细日志
export CREWAI_VERBOSE=true
python -m werewolf.main

# 使用 Python 调试器
python -m pdb werewolf/main.py
```

### 自定义工具

在 `werewolf/tools.py` 中添加新工具：

```python
@tool("你的工具名称")
def your_tool(param: str) -> str:
    """工具描述"""
    # 实现你的逻辑
    return result
```

然后在 `agents.py` 中注册工具：

```python
tools = [
    query_history,
    suspicion_tracking,
    your_tool,  # 添加你的工具
]
```

---

## 📚 延伸阅读

- [设计文档](./docs/DESIGN.md) - 架构设计详解
- [使用指南](./docs/USAGE.md) - 详细使用说明
- [千问配置](./docs/QWEN_CONFIG.md) - 模型配置详解
- [改进记录](./docs/IMPROVEMENTS.md) - 最新改进说明
- [项目总结](./docs/PROJECT_SUMMARY.md) - 项目完整总结

---

## 💡 最佳实践

### 1. 成本控制

```python
# 使用较便宜的模型
llm_model = "qwen-turbo"  # ¥0.002/1K tokens

# 限制迭代次数
max_iter = 3

# 减少玩家数量
PLAYERS = [...只保留 4 名玩家...]
```

### 2. 性能优化

```python
# 并行执行（在 game.py 中）
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(agent.execute) for agent in agents]
    results = [f.result() for f in futures]
```

### 3. 可靠性保障

```python
# 添加重试逻辑
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def call_llm(...):
    # LLM 调用
```

---

## 🤝 获取帮助

遇到问题？

1. **查看日志**: `logs/werewolf_game_*.txt`
2. **阅读文档**: `docs/` 目录下的文档
3. **检查配置**: `.env` 和 `config.py`
4. **提交 Issue**: 在 GitHub 上提问

---

## 🎉 开始游戏！

现在你已经掌握了所有基础知识，可以开始游戏了：

```bash
python -m werewolf.main
```

祝游戏愉快！🐺🌙