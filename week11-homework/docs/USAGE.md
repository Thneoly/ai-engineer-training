# 狼人杀游戏系统使用说明

## 目录
1. [快速开始](#快速开始)
2. [游戏说明](#游戏说明)
3. [配置选项](#配置选项)
4. [查看日志](#查看日志)
5. [可视化界面](#可视化界面)
6. [常见问题](#常见问题)

---

## 快速开始

### 1. 环境准备

**系统要求**:
- Python 3.11 或更高版本
- 网络连接（调用 OpenAI API）

**安装依赖**:
```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 配置 API Key

创建 `.env` 文件：
```bash
cp .env.example .env
```

编辑 `.env` 文件，添加你的 OpenAI API Key：
```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
```

### 3. 运行游戏

```bash
# 使用 uv run（推荐）
uv run python -m werewolf.main

# 或者直接使用 python（确保已激活虚拟环境）
python -m werewolf.main
```

游戏会自动开始，你将看到实时的游戏过程输出。

---

## 游戏说明

### 角色设定

本游戏包含 **5 名玩家**:

| 玩家名 | 角色 | 性格类型 | 特点 |
|--------|------|----------|------|
| 狼人Alpha | 狼人 | 激进型 | 态度强硬，主动引导 |
| 狼人Beta | 狼人 | 谨慎型 | 小心翼翼，避免暴露 |
| 村民Alice | 村民 | 分析型 | 逻辑推理，客观理性 |
| 村民Bob | 村民 | 情绪化型 | 感情丰富，易受影响 |
| 村民Charlie | 村民 | 中立型 | 平和客观，综合判断 |

### 游戏流程

每一轮包含以下阶段：

#### 1️⃣ 夜晚阶段 (Night)
- 狼人商议选择击杀目标
- 系统执行击杀

#### 2️⃣ 白天讨论阶段 (Day Discussion)
- 主持人宣布昨晚死亡的玩家
- 所有存活玩家依次发言
- 分析局势，指出嫌疑人

#### 3️⃣ 投票阶段 (Vote)
- 所有存活玩家投票
- 得票最多的玩家被处决

#### 4️⃣ 胜负判定
- **村民获胜**: 所有狼人被处决
- **狼人获胜**: 狼人数量 ≥ 村民数量

### 游戏特色

✨ **智能推理**: AI 使用工具检索历史记忆，基于证据做出决策

✨ **角色扮演**: 不同性格的玩家有不同的发言风格

✨ **记忆系统**: 每个玩家都有独立的记忆，能够回忆历史事件

✨ **策略博弈**: 狼人需要隐藏身份，村民需要找出狼人

---

## 配置选项

### 修改游戏配置

编辑 `werewolf/config.py`:

```python
class GameConfig:
    # 玩家数量配置
    NUM_WEREWOLVES = 2  # 狼人数量
    NUM_VILLAGERS = 3   # 村民数量
    
    # LLM 配置
    LLM_MODEL = "gpt-4o-mini"  # 可选: gpt-4o, gpt-3.5-turbo
    LLM_TEMPERATURE = 0.7      # 0-1，越高越随机
    
    # 记忆配置
    MEMORY_TOP_K = 5  # RAG 检索返回的记忆数量
    
    # 游戏规则
    MAX_ROUNDS = 10   # 最大回合数
```

### 自定义玩家

修改 `create_default_players()` 方法：

```python
@staticmethod
def create_default_players() -> List[PlayerConfig]:
    return [
        # 添加更多玩家
        PlayerConfig("狼人Gamma", Role.WEREWOLF, Personality.ANALYTICAL),
        PlayerConfig("村民David", Role.VILLAGER, Personality.AGGRESSIVE),
        # ...
    ]
```

### 使用不同的 LLM

在 `.env` 文件中配置：

```bash
# 使用 Azure OpenAI
OPENAI_API_KEY=your_azure_key
OPENAI_API_BASE=https://your-resource.openai.azure.com/
OPENAI_API_VERSION=2023-05-15

# 或使用本地模型（需要兼容 OpenAI API）
OPENAI_API_BASE=http://localhost:8000/v1
```

---

## 查看日志

### 日志文件位置

游戏结束后，日志保存在 `./logs` 目录：

```
logs/
├── werewolf_game_20241206_153045.json  # 结构化日志
├── werewolf_game_20241206_153045.txt   # 可读文本日志
└── replay_20241206_153045.json         # 回放数据
```

### JSON 日志结构

```json
{
  "total_rounds": 5,
  "winner": "villagers",
  "duration_seconds": 145.32,
  "alive_players": ["村民Alice", "村民Charlie"],
  "dead_players": ["狼人Alpha", "狼人Beta", "村民Bob"],
  "game_log": [
    {
      "round": 1,
      "phase": "night",
      "category": "DECISION",
      "message": "狼人选择击杀: 村民Bob"
    },
    // ...
  ],
  "memory_stats": {
    "村民Alice": {
      "total_memories": 45,
      "episodic_memories": 32,
      "semantic_memories": 13
    }
  }
}
```

### 文本日志示例

```
================================================================================
狼人杀游戏日志
================================================================================

总回合数: 5
获胜方: VILLAGERS
游戏时长: 145.32 秒
存活玩家: 村民Alice, 村民Charlie
死亡玩家: 狼人Alpha, 狼人Beta, 村民Bob

================================================================================
游戏过程记录
================================================================================

============================================================
第 1 轮
============================================================

[PHASE] [night] 第1轮 - 夜晚降临
[ACTION] [night] 狼人们正在商议击杀目标...
[DECISION] [night] 狼人选择击杀: 村民Bob
[PHASE] [day] 第1轮 - 白天到来
[ANNOUNCEMENT] [day] 昨晚，村民Bob 被狼人杀害了！
[SPEECH] [discussion] 村民Alice: 我认为狼人Alpha的发言很可疑...
...
```

---

## 可视化界面

### 启动 Streamlit 界面

```bash
# 使用 uv run
uv run streamlit run werewolf/visualizer.py

# 或直接使用（需要已激活虚拟环境）
streamlit run werewolf/visualizer.py
```

浏览器会自动打开 `http://localhost:8501`

### 界面功能

📊 **游戏概况**
- 总回合数、获胜方、游戏时长
- 存活/死亡玩家列表

📜 **游戏过程**
- 按回合过滤查看
- 彩色标记不同类型的事件
- 发言、决策、投票全记录

🧠 **记忆统计**
- 每个玩家的记忆数量
- 情景记忆 vs 语义记忆
- 可视化图表

💾 **数据下载**
- 下载 JSON 格式的完整日志

---

## 常见问题

### Q1: 游戏运行很慢

**原因**: API 调用延迟
**解决方案**:
- 使用更快的模型（如 `gpt-3.5-turbo`）
- 减少 `max_iter` 参数
- 使用本地部署的模型

### Q2: Token 使用过多

**解决方案**:
- 降低 `MEMORY_TOP_K` 参数（减少 RAG 检索数量）
- 使用更便宜的模型
- 减少 `MAX_ROUNDS`

### Q3: Agent 不使用工具

**原因**: Prompt 不清晰
**解决方案**:
- 在任务描述中明确指示"使用你的工具"
- 在 Agent 的 backstory 中强调工具的重要性

### Q4: 狼人身份容易暴露

**解决方案**:
- 增强狼人角色的 Prompt，强调"隐藏身份"
- 增加狼人的谨慎性格设定
- 降低 Temperature 参数

### Q5: 决策结果无法解析

**原因**: AI 输出格式不规范
**解决方案**:
- 在任务描述中提供明确的输出格式示例
- 使用正则表达式增强解析逻辑
- 增加容错处理（随机选择）

### Q6: ChromaDB 初始化失败

**解决方案**:
```bash
# 清除旧的数据
rm -rf ./chroma_db

# 重新运行游戏
uv run python -m werewolf.main
```

### Q7: 如何调试 Agent 的思考过程？

**方法**:
1. 在 `agents.py` 中设置 `verbose=True`
2. 查看控制台输出的 Thought-Action-Observation 链
3. 检查 `./logs` 目录的详细日志

### Q8: 如何添加新角色（如预言家）？

**步骤**:
1. 在 `config.py` 的 `Role` 枚举中添加新角色
2. 为新角色编写 Prompt
3. 在 `agents.py` 中创建对应的 Agent 类
4. 在 `tasks.py` 中创建新角色的任务
5. 在 `game.py` 中集成新角色的流程

---

## 性能优化建议

### 降低成本
- 使用 `gpt-3.5-turbo` 代替 `gpt-4o-mini`
- 减少玩家数量（如 3人局）
- 限制每轮的讨论发言长度

### 提升速度
- 使用流式输出
- 并行执行独立任务（如投票）
- 使用本地 LLM（如 Ollama）

### 提升质量
- 使用更强的模型（如 `gpt-4o`）
- 增加 RAG 检索数量（`MEMORY_TOP_K`）
- 细化 Prompt 设计

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

改进方向：
- 添加更多角色（预言家、女巫、猎人等）
- 优化 Agent 的策略和推理能力
- 改进可视化界面
- 添加多语言支持
- 支持实时对战（人类 vs AI）

---

## 技术支持

如有问题，请查看：
1. [DESIGN.md](./DESIGN.md) - 详细的技术文档
2. [GitHub Issues](your_repo_url/issues) - 提交问题

---

## 许可证

MIT License - 详见 LICENSE 文件
