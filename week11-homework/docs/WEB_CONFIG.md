# Web 界面配置说明

## ❗ 重要说明

### 问题：`WerewolfGame.__init__() got an unexpected keyword argument 'max_rounds'`

**原因分析：**

`WerewolfGame` 类的构造函数签名是：
```python
def __init__(self, player_configs: Optional[List[PlayerConfig]] = None):
```

它只接受 `player_configs` 参数，**不接受** `max_rounds` 参数。

### 正确配置方式

游戏的最大回合数在 `werewolf/config.py` 中定义：

```python
class GameConfig:
    MAX_ROUNDS = 8  # 最大回合数
```

**修改方法：**

如果需要修改最大回合数，编辑 `werewolf/config.py` 文件：

```python
# 找到这一行
MAX_ROUNDS = 8

# 修改为你想要的值
MAX_ROUNDS = 10  # 或其他数值
```

## ✅ 已修复

### 修改内容

1. **web_ui.py** - 移除了动态设置 `max_rounds` 的滑块
2. **web_ui_simple.py** - 改为显示配置信息，不尝试修改

### 当前状态

- ✅ Web 界面用于查看历史对局
- ✅ 新游戏需要在终端运行
- ✅ 游戏配置在 `config.py` 中统一管理

## 🎮 启动新游戏的正确方式

### 方法 1: 使用默认配置（推荐）

```bash
cd /home/cc/Desktop/code/AIPro/ai-engineer-training/week11-homework
source .venv/bin/activate
python -m werewolf.main
```

**默认配置：**
- 玩家: 6 名（2狼人 + 4村民）
- 最大回合数: 8 轮
- 模型: qwen-plus

### 方法 2: 修改配置后运行

1. 编辑 `werewolf/config.py`
2. 修改相关配置（如 MAX_ROUNDS）
3. 保存文件
4. 运行游戏

```bash
# 编辑配置
nano werewolf/config.py  # 或使用其他编辑器

# 运行游戏
python -m werewolf.main
```

### 方法 3: 通过代码自定义

创建自定义启动脚本：

```python
# custom_game.py
from werewolf.game import WerewolfGame
from werewolf.config import game_config

# 临时修改配置
game_config.MAX_ROUNDS = 15

# 启动游戏
game = WerewolfGame()
game.play()
```

运行：
```bash
python custom_game.py
```

## 📝 配置参数说明

### werewolf/config.py 中的可配置项

```python
class GameConfig:
    # 游戏回合
    MAX_ROUNDS = 8          # 最大回合数
    
    # 阶段定义
    PHASE_NIGHT = "night"   # 夜晚阶段
    PHASE_DAY = "day"       # 白天阶段
    
    # 玩家配置
    def create_default_players(self):
        return [
            PlayerConfig("Alpha", Role.WEREWOLF),
            PlayerConfig("Beta", Role.WEREWOLF),
            PlayerConfig("Alice", Role.VILLAGER),
            PlayerConfig("Bob", Role.VILLAGER),
            PlayerConfig("Charlie", Role.VILLAGER),
            PlayerConfig("David", Role.VILLAGER),
        ]
```

### 修改玩家配置

如需修改玩家数量或角色分配，编辑 `create_default_players()` 方法：

```python
def create_default_players(self):
    return [
        PlayerConfig("Alpha", Role.WEREWOLF),
        PlayerConfig("Beta", Role.WEREWOLF),
        PlayerConfig("Gamma", Role.WEREWOLF),  # 添加第3个狼人
        PlayerConfig("Alice", Role.VILLAGER),
        PlayerConfig("Bob", Role.VILLAGER),
        PlayerConfig("Charlie", Role.VILLAGER),
        PlayerConfig("David", Role.VILLAGER),
        PlayerConfig("Eve", Role.VILLAGER),    # 添加更多村民
    ]
```

## 🔧 为什么 Web 界面不支持动态配置？

### 技术原因

1. **配置加载时机**
   - `game_config` 在模块导入时就被初始化
   - 后续修改不会影响已导入的配置

2. **全局单例模式**
   - `game_config` 是全局单例
   - 多个实例共享同一配置

3. **CrewAI 限制**
   - Agent 初始化后配置不可变
   - 需要重新创建所有 Agent

### 设计决策

为了保持简单和一致性：
- ✅ 配置统一在 `config.py` 中管理
- ✅ Web 界面专注于展示和查看
- ✅ 游戏运行在终端，便于调试

## 📊 推荐配置

### 快速测试（3-5分钟）
```python
MAX_ROUNDS = 3
# 玩家: 4名（1狼人 + 3村民）
```

### 标准游戏（5-8分钟）
```python
MAX_ROUNDS = 8
# 玩家: 6名（2狼人 + 4村民）- 默认
```

### 完整体验（10-15分钟）
```python
MAX_ROUNDS = 15
# 玩家: 8名（3狼人 + 5村民）
```

## 🎯 最佳实践

1. **开发调试**: 使用较少回合数（3-5）
2. **展示演示**: 使用标准配置（8回合）
3. **深度分析**: 使用更多回合（10-15）

## ❓ 常见问题

### Q1: 如何临时改变回合数？

**方法 A**: 修改配置文件（推荐）
```bash
# 编辑 werewolf/config.py
MAX_ROUNDS = 10
```

**方法 B**: 运行时修改（临时）
```python
from werewolf.config import game_config
game_config.MAX_ROUNDS = 10

from werewolf.game import WerewolfGame
game = WerewolfGame()
game.play()
```

### Q2: Web 界面能否支持配置？

技术上可以，但需要：
1. 重构配置系统为可变对象
2. 每次启动时重新初始化所有 Agent
3. 处理配置冲突和状态同步

**当前选择**: 保持简单，配置写死在文件中

### Q3: 修改配置后需要重启吗？

- ✅ 修改 `config.py` 后需要重新运行游戏
- ❌ 不需要重启 Streamlit（除非修改了 web_ui.py）

---

**总结**: Web 界面现在专注于查看历史对局，游戏配置通过 `config.py` 统一管理。

**当前状态**: ✅ 已修复，Streamlit 正在运行 http://localhost:8501
