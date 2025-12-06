# 狼人杀游戏系统设计文档

## 1. 系统概述

本项目使用 **CrewAI** 框架实现了一个基于智能体协作的狼人杀游戏系统，包含 5 名 AI 玩家（2个狼人 + 3个村民），具备角色扮演、策略推理和自然对话能力。

### 技术栈
- **框架**: CrewAI 0.28.0+
- **LLM**: OpenAI GPT-4o-mini (可配置)
- **向量数据库**: ChromaDB
- **记忆系统**: 情景记忆 + 语义记忆 + RAG
- **编程语言**: Python 3.11+

---

## 2. 系统架构

### 2.1 核心模块

```
werewolf/
├── config.py          # 游戏配置和角色定义
├── memory.py          # 记忆管理系统（RAG）
├── agents.py          # Agent 定义
├── tools.py           # Agent 工具
├── tasks.py           # 游戏任务定义
├── game.py            # 游戏主控制器
├── logger.py          # 日志和分析
└── main.py            # 程序入口
```

### 2.2 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Game Controller                       │
│                     (game.py)                            │
└────────┬────────────────────────────────────────────────┘
         │
         ├──► Moderator Agent (主持人)
         │
         ├──► Player Agents (玩家)
         │    ├─ Werewolf Agent 1 (狼人Alpha - 激进型)
         │    ├─ Werewolf Agent 2 (狼人Beta - 谨慎型)
         │    ├─ Villager Agent 1 (村民Alice - 分析型)
         │    ├─ Villager Agent 2 (村民Bob - 情绪化型)
         │    └─ Villager Agent 3 (村民Charlie - 中立型)
         │
         ├──► Memory System (记忆系统)
         │    ├─ Episodic Memory (情景记忆)
         │    ├─ Semantic Memory (语义记忆)
         │    └─ ChromaDB (向量数据库 - RAG)
         │
         ├──► Tools (工具系统)
         │    ├─ Memory Retrieval Tool (记忆检索)
         │    ├─ Player Analysis Tool (玩家分析)
         │    ├─ Vote Analysis Tool (投票分析)
         │    ├─ Game State Query Tool (状态查询)
         │    └─ Suspicion Tracking Tool (嫌疑跟踪)
         │
         └──► Logger (日志系统)
              ├─ Game Log (游戏日志)
              ├─ Analysis Report (分析报告)
              └─ Replay Data (回放数据)
```

---

## 3. 核心功能实现

### 3.1 Agent 角色建模

#### 角色定义
每个 Agent 由以下要素组成：
- **角色类型** (`Role`): `WEREWOLF`（狼人）、`VILLAGER`（村民）、`MODERATOR`（主持人）
- **性格类型** (`Personality`):
  - `AGGRESSIVE`（激进型）: 态度强硬，敢于指责
  - `CAUTIOUS`（谨慎型）: 仔细思考，避免成为焦点
  - `ANALYTICAL`（分析型）: 逻辑推理，客观理性
  - `EMOTIONAL`（情绪化型）: 情感丰富，易受影响
  - `NEUTRAL`（中立型）: 保持平和客观

#### Prompt 工程
```python
# 角色 Prompt + 性格 Prompt 组合
backstory = f"""
{role_prompts[self.role]}      # 基础角色设定
{personality_prompts[self.personality]}  # 性格特点
你的名字是 {self.name}
你需要利用记忆和观察来做出最佳决策
"""
```

示例（狼人+激进型）：
```
你是一个狼人。你的目标是消灭所有村民而不被发现。
在夜晚阶段，你可以与其他狼人协商选择要杀死的村民。
在白天阶段，你必须伪装成村民，隐藏你的真实身份。

你的性格是激进型：
- 发言时态度强硬，敢于直接指责可疑的玩家
- 主动引导话题和讨论方向
- 不轻易妥协，坚持自己的判断
```

### 3.2 游戏流程控制

#### 游戏循环
```python
while round < MAX_ROUNDS:
    1. Night Phase (夜晚)
       - 狼人选择击杀目标
       - 目标玩家死亡
    
    2. Check Win Condition
       - 狼人全灭 → 村民胜
       - 狼人 >= 村民 → 狼人胜
    
    3. Discussion Phase (白天讨论)
       - 主持人宣布死亡
       - 所有存活玩家依次发言
       - 分析局势、指出嫌疑人
    
    4. Vote Phase (投票)
       - 所有玩家投票
       - 统计投票结果
       - 处决得票最多的玩家
    
    5. Check Win Condition
```

#### 阶段管理
使用 `game_state` 字典维护游戏状态：
```python
game_state = {
    "round": 当前回合数,
    "phase": 当前阶段（night/day/discussion/vote）,
    "alive_players": 存活玩家列表,
    "dead_players": 死亡玩家列表,
    "werewolves": 狼人列表,
    "villagers": 村民列表
}
```

### 3.3 记忆管理系统

#### 两层记忆架构

**1. 情景记忆 (Episodic Memory)**
- 记录具体游戏事件
- 例如: "村民Alice说: 我怀疑狼人Beta的发言很可疑"
- 包含元数据: `round`, `phase`, `speaker`, `action`

**2. 语义记忆 (Semantic Memory)**
- 存储总结性知识和推理结论
- 例如: "对狼人Beta的怀疑程度为8/10，原因: 投票行为异常"
- 包含元数据: `category`, `related_player`

#### 向量数据库 (ChromaDB)
```python
# 每个玩家独立的 Collection
collection_name = f"werewolf_memory_{player_name}"

# 存储记忆
collection.add(
    documents=[memory.content],
    metadatas=[memory.metadata],
    ids=[unique_id]
)

# RAG 检索
results = collection.query(
    query_texts=[query],
    n_results=top_k,
    where=filter_conditions  # 可按 round, phase 等过滤
)
```

### 3.4 RAG 增强推理

#### RAG 应用场景

1. **发言阶段**
   - 检索与死亡玩家相关的历史信息
   - 检索被怀疑玩家的行为记录
   ```python
   query = f"关于{suspected_player}的发言和行为"
   memories = memory_manager.retrieve_relevant_memories(query, top_k=5)
   ```

2. **投票阶段**
   - 检索候选人的可疑行为
   - 回顾讨论中的关键信息
   ```python
   for candidate in candidates:
       query = f"{candidate}的可疑行为和证据"
       evidence = memory_manager.retrieve_relevant_memories(query)
   ```

3. **狼人决策**
   - 分析村民的威胁程度
   - 回顾谁在接近真相
   ```python
   query = "谁对我们的怀疑最强烈"
   threats = memory_manager.retrieve_relevant_memories(query)
   ```

#### RAG 优势
- **上下文增强**: AI 能够访问完整历史，而非仅依赖短期上下文
- **推理质量**: 基于事实证据的推理，而非臆测
- **角色一致性**: 记忆持久化保证角色行为连贯性

### 3.5 工具系统 (Tools)

每个 Agent 配备以下工具：

| 工具名称 | 功能 | 应用场景 |
|---------|------|----------|
| **Memory Retrieval Tool** | 语义检索相关记忆 | 发言前回顾历史 |
| **Player Analysis Tool** | 分析特定玩家行为 | 判断玩家身份 |
| **Vote Analysis Tool** | 分析候选人可疑度 | 投票决策 |
| **Game State Query Tool** | 查询游戏状态 | 了解当前局势 |
| **Suspicion Tracking Tool** | 记录怀疑程度 | 跟踪嫌疑人 |

示例：记忆检索工具
```python
class MemoryRetrievalTool(BaseTool):
    def _run(self, query: str, top_k: int = 5) -> str:
        memories = self.memory_manager.retrieve_relevant_memories(
            query, top_k=top_k
        )
        return format_memories(memories)
```

---

## 4. CrewAI 任务设计

### 4.1 夜晚行动任务
```python
Task(
    description="""
    狼人们需要讨论并决定今晚要杀死的目标。
    存活的村民有: {villager_list}
    
    作为狼人，你需要:
    1. 分析每个村民的威胁程度
    2. 回忆之前的发言和投票情况
    3. 选择一个最佳的击杀目标
    
    使用你的工具（记忆检索、玩家分析）来帮助决策。
    
    输出格式: 
    目标: [玩家名字]
    理由: [详细理由]
    """,
    agent=werewolf_agent,
    expected_output="选择一个击杀目标并给出理由"
)
```

### 4.2 讨论发言任务
```python
Task(
    description="""
    昨晚 {victim} 被狼人杀害了！
    
    现在是发言环节，作为 {player_name}，你需要:
    1. 使用记忆检索工具回顾之前的游戏过程
    2. 分析昨晚死亡的玩家和可能的嫌疑人
    3. 表达你的观点和推理
    4. 指出你认为可疑的玩家
    5. 发言要符合你的角色身份和性格特点
    
    {'你是狼人，要隐藏身份！' if is_werewolf else '仔细分析，找出狼人！'}
    
    输出你的发言内容（200字以内）
    """,
    agent=player_agent,
    expected_output="一段分析和发言内容"
)
```

### 4.3 投票任务
```python
Task(
    description="""
    你需要投票处决一名玩家。
    候选人: {candidates_list}
    
    作为 {player_name}，你需要:
    1. 回顾刚才的讨论发言
    2. 使用投票分析工具分析各个候选人
    3. 检索关于嫌疑人的记忆
    4. 做出你的投票决策
    
    输出格式:
    投票: [玩家名字]
    理由: [简要理由]
    """,
    agent=player_agent,
    expected_output="投票给一名玩家并给出理由"
)
```

---

## 5. 调试方法

### 5.1 日志系统

**三层日志**:
1. **控制台输出**: 实时显示游戏进程
2. **JSON 日志**: 完整的结构化数据 (`werewolf_game_YYYYMMDD_HHMMSS.json`)
3. **可读文本日志**: 人类友好格式 (`werewolf_game_YYYYMMDD_HHMMSS.txt`)

### 5.2 调试技巧

**1. 观察 Agent 思考链**
CrewAI 的 `verbose=True` 会输出：
- **Thought**: Agent 的思考过程
- **Action**: 使用了哪个工具
- **Observation**: 工具返回的结果

**2. 检查记忆系统**
```python
# 查看玩家记忆统计
memory_stats = memory_manager.get_memory_stats()
print(memory_stats)

# 导出所有记忆
memories = memory_manager.export_memories()
```

**3. 分析 RAG 效果**
```python
# 测试检索质量
query = "谁最可疑"
results = memory_manager.retrieve_relevant_memories(query, top_k=5)
for r in results:
    print(f"相似度: {r['distance']}, 内容: {r['content']}")
```

**4. 常见问题排查**

| 问题 | 可能原因 | 解决方案 |
|------|---------|----------|
| Agent 不使用工具 | Prompt 不清晰 | 明确指示"使用你的工具" |
| 狼人身份暴露 | Role Prompt 不够强调 | 增强"隐藏身份"指令 |
| 决策无法解析 | 输出格式不规范 | 使用更严格的输出格式示例 |
| RAG 检索无结果 | ChromaDB 未正确初始化 | 检查 collection 创建 |
| Token 超限 | 记忆过多 | 限制 `top_k` 参数 |

### 5.3 开发迭代建议

**第一版：基础流程**
- 实现简单的轮次循环
- 固定决策（随机/规则）
- 验证游戏流程完整性

**第二版：加入 Agent**
- 引入 CrewAI Agent
- 简单 Prompt
- 观察 AI 行为

**第三版：记忆系统**
- 添加情景记忆
- 观察 Agent 是否能记住历史

**第四版：RAG 优化**
- 接入 ChromaDB
- 优化检索 Query
- 观察推理质量提升

**第五版：性格多样化**
- 引入性格 Prompt
- 观察角色差异性

---

## 6. 成本与性能分析

### 6.1 Token 使用估算

**单轮游戏 Token 消耗**:
- 夜晚阶段: ~1,000 tokens
- 讨论阶段 (5人): ~5,000 tokens
- 投票阶段 (5人): ~2,500 tokens
- **总计**: ~8,500 tokens/轮

**完整游戏 (假设5轮)**:
- 总 Token: ~42,500 tokens
- 使用 GPT-4o-mini:
  - Input: $0.15/1M tokens ≈ $0.006
  - Output: $0.60/1M tokens ≈ $0.025
  - **总成本**: ~$0.03 / 局

### 6.2 延迟分析

- Agent 单次决策: 3-10秒
- 讨论阶段 (5人顺序): 15-50秒
- 投票阶段 (5人): 15-50秒
- **单轮总时长**: 40-120秒
- **完整游戏**: 3-10分钟

### 6.3 优化建议

**降低成本**:
- 使用更小的模型（如 GPT-3.5-turbo）
- 减少 `max_iter` 限制思考轮次
- 优化 Prompt 长度

**提升速度**:
- 并行执行投票任务
- 减少 RAG 检索数量 (`top_k`)
- 使用流式输出

**资源预估**:
- CPU: 普通 2核+ 即可
- 内存: 4GB+
- GPU: 不需要（云端 API 调用）
- 存储: ChromaDB 数据 < 100MB

---

## 7. 扩展性设计

### 7.1 支持更多角色
```python
# 添加新角色（如预言家、女巫）
class Role(Enum):
    WEREWOLF = "werewolf"
    VILLAGER = "villager"
    SEER = "seer"  # 预言家
    WITCH = "witch"  # 女巫
```

### 7.2 支持更多玩家
修改 `config.py`:
```python
NUM_WEREWOLVES = 3
NUM_VILLAGERS = 5
```

### 7.3 可视化界面
使用 Streamlit 创建 Web UI：
```python
# visualizer.py
import streamlit as st

st.title("狼人杀游戏实时观战")
st.write(f"当前回合: {game_state['round']}")
st.write(f"存活玩家: {game_state['alive_players']}")
```

---

## 8. 项目特色

### 8.1 技术亮点
✅ **CrewAI 多 Agent 协作**: 充分利用框架的任务分配和角色定义能力  
✅ **双层记忆系统**: 情景记忆 + 语义记忆，模拟人类记忆机制  
✅ **RAG 增强推理**: 基于向量检索的上下文增强决策  
✅ **性格多样化**: 5种性格模板，提升角色真实感  
✅ **完整可观测性**: 日志、分析报告、回放数据三位一体  

### 8.2 能力展示
- **提示工程**: 角色 Prompt + 性格 Prompt 组合设计
- **多 Agent 调度**: 游戏流程的有序控制
- **记忆管理**: 跨轮次的记忆存储和检索
- **RAG 应用**: 语义检索在决策链中的实际应用
- **成本评估**: Token 使用和延迟的量化分析

---

## 9. 运行指南

### 9.1 环境配置
```bash
# 1. 安装依赖
uv sync

# 2. 配置 API Key
# 创建 .env 文件
echo "OPENAI_API_KEY=your_api_key_here" > .env

# 3. 运行游戏
python -m werewolf.main
```

### 9.2 查看结果
```bash
# 游戏日志保存在 ./logs 目录
ls logs/

# 包含:
# - werewolf_game_YYYYMMDD_HHMMSS.json  # 结构化日志
# - werewolf_game_YYYYMMDD_HHMMSS.txt   # 可读日志
# - replay_YYYYMMDD_HHMMSS.json         # 回放数据
```

### 9.3 自定义配置
编辑 `werewolf/config.py`:
```python
# 修改 LLM 模型
LLM_MODEL = "gpt-4o"  # 或 "gpt-3.5-turbo"

# 修改玩家数量
NUM_WEREWOLVES = 3
NUM_VILLAGERS = 5

# 修改最大回合数
MAX_ROUNDS = 15
```

---

## 10. 总结

本项目完整实现了作业要求的所有核心功能：

| 功能模块 | 实现方式 | 文件位置 |
|---------|---------|---------|
| Agent 角色建模 | Role + Personality 组合 Prompt | `config.py`, `agents.py` |
| 游戏流程控制 | 主持人协调 + 阶段管理 | `game.py` |
| 记忆管理 | 情景+语义记忆 + ChromaDB | `memory.py` |
| RAG 增强推理 | 向量检索 + 工具调用 | `memory.py`, `tools.py` |
| 可视化追踪 | 三层日志系统 | `logger.py` |
| 成本分析 | Token 统计 + 延迟分析 | 本文档 Section 6 |

项目采用模块化设计，易于扩展和维护。通过 CrewAI 框架的强大能力，成功实现了具备"角色扮演+策略推理+自然对话"能力的智能玩家系统。
