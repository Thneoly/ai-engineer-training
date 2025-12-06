# 狼人杀游戏系统 - 快速开始

## 项目简介

使用 **CrewAI** 框架实现的智能体协作狼人杀游戏系统，包含：
- 5名 AI 玩家（2狼人 + 3村民）
- 完整的角色扮演和策略推理
- 记忆管理系统（情景记忆 + 语义记忆 + RAG）
- 可观测的游戏日志和分析

## 快速开始

### 1. 安装依赖

```bash
# 使用 uv 安装依赖
uv sync
```

### 2. 配置 API Key

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env 文件，添加你的 OpenAI API Key
# OPENAI_API_KEY=your_api_key_here
```

### 3. 运行游戏

```bash
# 使用 uv run（推荐）
uv run python -m werewolf.main
```

## 游戏输出

游戏结束后，会在 `./logs` 目录生成以下文件：

1. **JSON 日志**: `werewolf_game_YYYYMMDD_HHMMSS.json`
   - 完整的结构化游戏数据
   
2. **可读日志**: `werewolf_game_YYYYMMDD_HHMMSS.txt`
   - 人类友好的文本格式
   
3. **回放数据**: `replay_YYYYMMDD_HHMMSS.json`
   - 用于可视化的关键事件数据

## 项目结构

```
werewolf/
├── config.py      # 游戏配置和角色定义
├── memory.py      # 记忆管理系统（RAG）
├── agents.py      # Agent 定义
├── tools.py       # Agent 工具
├── tasks.py       # 游戏任务定义
├── game.py        # 游戏主控制器
├── logger.py      # 日志和分析
└── main.py        # 程序入口
```

## 核心特性

✅ **角色扮演**: 5种性格类型（激进、谨慎、分析、情绪化、中立）  
✅ **记忆系统**: 情景记忆 + 语义记忆，使用 ChromaDB 向量数据库  
✅ **RAG 推理**: 基于历史记忆的智能决策  
✅ **完整流程**: 夜晚 → 讨论 → 投票 → 胜负判定  
✅ **可观测性**: 详细的日志和分析报告  

## 自定义配置

编辑 `werewolf/config.py` 可以修改：

- LLM 模型（默认: gpt-4o-mini）
- 玩家数量（默认: 2狼人 + 3村民）
- 最大回合数（默认: 10）
- 记忆检索参数

## 设计文档

详细的系统设计、架构说明和调试方法请查看 [DESIGN.md](./DESIGN.md)

## 作业要求对照

| 要求 | 实现 | 文件位置 |
|-----|------|---------|
| CrewAI 框架 | ✅ | `agents.py`, `tasks.py` |
| 5名 AI 玩家 | ✅ | `config.py` |
| 角色身份记忆 | ✅ | `memory.py` |
| 发言策略生成 | ✅ | `tasks.py` |
| 身份伪装/揭露 | ✅ | `agents.py` (Prompt) |
| 记忆管理 | ✅ | `memory.py` (ChromaDB) |
| RAG 增强推理 | ✅ | `tools.py`, `memory.py` |
| 可视化追踪 | ✅ | `logger.py` |
| 成本分析 | ✅ | `DESIGN.md` Section 6 |

## 许可证

MIT
