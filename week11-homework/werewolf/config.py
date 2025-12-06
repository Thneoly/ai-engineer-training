"""
游戏配置和角色定义
"""
from enum import Enum
from typing import Dict, List
from dataclasses import dataclass


class Role(Enum):
    """角色类型"""
    WEREWOLF = "werewolf"
    VILLAGER = "villager"
    MODERATOR = "moderator"


class Personality(Enum):
    """性格类型"""
    AGGRESSIVE = "aggressive"  # 激进型
    CAUTIOUS = "cautious"  # 谨慎型
    ANALYTICAL = "analytical"  # 分析型
    EMOTIONAL = "emotional"  # 情绪化型
    NEUTRAL = "neutral"  # 中立型


@dataclass
class PlayerConfig:
    """玩家配置"""
    name: str
    role: Role
    personality: Personality
    alive: bool = True


class GameConfig:
    """游戏配置"""
    
    # 玩家数量配置
    NUM_WEREWOLVES = 2
    NUM_VILLAGERS = 4  # 调整为 4 个村民，让游戏更快但仍然平衡 (2狼 vs 4村民)
    TOTAL_PLAYERS = NUM_WEREWOLVES + NUM_VILLAGERS
    
    # 游戏阶段
    PHASE_NIGHT = "night"
    PHASE_DAY = "day"
    PHASE_DISCUSSION = "discussion"
    PHASE_VOTE = "vote"
    
    # LLM 配置
    LLM_MODEL = "qwen-plus"  # 千问模型：qwen-plus, qwen-turbo, qwen-max
    LLM_TEMPERATURE = 0.7
    LLM_PROVIDER = "dashscope"  # 使用阿里云通义千问
    
    # 记忆配置
    MEMORY_TOP_K = 5  # RAG 检索时返回的相关记忆数量
    MEMORY_COLLECTION_NAME = "werewolf_game_memory"
    
    # 游戏规则
    MAX_ROUNDS = 8  # 减少最大回合数，让游戏更快结束
    
    @staticmethod
    def get_role_prompts() -> Dict[Role, str]:
        """获取角色基础 Prompt"""
        return {
            Role.WEREWOLF: """你是狼人阵营的玩家。你的目标是让所有村民阵营玩家出局而不被发现。

【游戏背景】
- 本局游戏只有两种角色：狼人和村民
- 狼人数量：2人（你和另一个狼人）
- 村民数量：4人（普通村民，没有特殊技能）
- 没有女巫、预言家、猎人等其他神职角色

【你的任务】
在夜晚阶段，你可以与其他狼人协商选择一个村民玩家让其出局。
在白天阶段，你必须伪装成村民，隐藏你的真实身份，引导其他玩家投票淘汰无辜的好人。
记住：不要暴露自己的狼人身份！这是一个推理游戏，需要策略和伪装。""",
            
            Role.VILLAGER: """你是村民阵营的玩家。你的目标是找出并投票淘汰所有狼人阵营的玩家。

【游戏背景】
- 本局游戏只有两种角色：狼人和村民
- 狼人数量：2人（隐藏在玩家中）
- 村民数量：4人（包括你，都是普通村民）
- 没有女巫、预言家、猎人等其他神职角色
- 你没有特殊技能，只能通过观察和推理找出狼人

【你的任务】
在白天阶段，仔细聆听每个人的发言，分析他们的逻辑和行为。
通过推理和观察来识别可疑的狼人，并说服其他村民投票淘汰狼人。
保持警惕，这是一个策略推理游戏！""",
            
            Role.MODERATOR: """你是游戏主持人。你的职责是：
1. 管理游戏流程，确保夜晚和白天阶段的正确执行
2. 宣布游戏结果（哪些玩家出局、投票结果）
3. 判断游戏胜负条件（村民获胜或狼人获胜）
4. 保持公平公正，不泄露任何玩家的身份信息

【游戏配置】
- 玩家总数：6人
- 狼人阵营：2人
- 村民阵营：4人（普通村民，无特殊技能）
- 没有女巫、预言家、猎人等其他神职角色

【完整游戏流程】

1️⃣ **游戏开始阶段**
   - 条件：游戏启动
   - 操作：宣布游戏开始，介绍玩家信息（不透露身份）
   - 流出：进入狼人确认身份环节

2️⃣ **狼人确认身份环节 (recognition)**
   - 进入条件：游戏开始后，第一个夜晚之前
   - 操作内容：
     * 宣布"第一个夜晚 - 狼人确认身份"
     * 让狼人玩家互相认识队友
     * 狼人记住队友身份，以便后续配合
   - 重要性：这是标准狼人杀流程，确保狼人知道彼此身份
   - 流出条件：狼人确认完成
   - 流出去向：进入第1轮

3️⃣ **夜晚阶段 (night)**
   - 进入条件：每轮开始时
   - 操作内容：
     * 宣布"夜晚降临"
     * 狼人玩家秘密协商并选择一个村民出局
     * 记录狼人的选择
   - 流出条件：狼人完成选择后
   - 流出去向：直接进入白天讨论阶段（不检查胜利条件）

4️⃣ **白天讨论阶段 (discussion)**
   - 进入条件：夜晚阶段结束后
   - 操作内容：
     * 宣布昨晚出局的玩家
     * 所有存活玩家依次发言讨论
     * 分析可疑对象，表达观点
   - 流出条件：所有存活玩家都发言完毕
   - 流出去向：进入投票阶段

5️⃣ **投票阶段 (vote)**
   - 进入条件：讨论阶段结束后
   - 操作内容：
     * 宣布进入投票环节
     * 所有存活玩家进行投票
     * 统计投票结果
     * 宣布得票最多的玩家被淘汰
   - 流出条件：投票完成并淘汰一名玩家
   - 流出去向：检查胜利条件

6️⃣ **胜利条件检查**
   - 检查时机：每轮投票阶段结束后
   - 检查条件：
     * 如果狼人全部出局（0个狼人存活） → 村民获胜，游戏结束
     * 如果狼人数量 > 村民数量 → 狼人获胜，游戏结束
     * 如果达到最大回合数（8轮） → 游戏平局，结束
     * 否则 → 进入下一轮（回到夜晚阶段）

【重要规则】
- ⚠️ 夜晚出局后不立即判断胜负，必须给村民讨论和投票的机会
- ✅ 只在投票阶段结束后检查胜利条件
- 🔄 每轮流程：狼人确认(仅第一次) → 夜晚 → 白天讨论 → 投票 → 检查胜负 → （如继续）下一轮夜晚
- 🎯 狼人需要数量严格大于村民才能获胜（不是等于）
- 🐺 狼人在游戏开始时就知道队友是谁，不会互相指控
- 📊 游戏最多进行8轮，超过则判定为平局"""
        }
    
    @staticmethod
    def get_personality_prompts() -> Dict[Personality, str]:
        """获取性格 Prompt"""
        return {
            Personality.AGGRESSIVE: """你的性格是激进型：
- 发言时态度强硬，敢于直接指责可疑的玩家
- 主动引导话题和讨论方向
- 不轻易妥协，坚持自己的判断""",
            
            Personality.CAUTIOUS: """你的性格是谨慎型：
- 发言前会仔细思考，不轻易下结论
- 倾向于观察和收集信息
- 避免成为焦点，但会在关键时刻表态""",
            
            Personality.ANALYTICAL: """你的性格是分析型：
- 善于逻辑推理和数据分析
- 发言时会列举证据和推理链
- 客观理性，较少受情绪影响""",
            
            Personality.EMOTIONAL: """你的性格是情绪化型：
- 容易受情绪影响，发言带有强烈的个人感情
- 可能因为被怀疑而激动辩解
- 善于用情感打动他人""",
            
            Personality.NEUTRAL: """你的性格是中立型：
- 保持平和客观的态度
- 既不过分激进也不过分谨慎
- 倾听各方意见后做出判断"""
        }
    
    @staticmethod
    def create_default_players() -> List[PlayerConfig]:
        """创建默认玩家配置 - 使用中性名字隐藏身份"""
        return [
            # 2 个狼人 - 使用中性名字
            PlayerConfig("Alpha", Role.WEREWOLF, Personality.AGGRESSIVE),
            PlayerConfig("Beta", Role.WEREWOLF, Personality.CAUTIOUS),
            
            # 4 个村民 - 使用中性名字
            PlayerConfig("Alice", Role.VILLAGER, Personality.ANALYTICAL),
            PlayerConfig("Bob", Role.VILLAGER, Personality.EMOTIONAL),
            PlayerConfig("Charlie", Role.VILLAGER, Personality.NEUTRAL),
            PlayerConfig("David", Role.VILLAGER, Personality.AGGRESSIVE),
        ]


# 导出配置实例
game_config = GameConfig()
