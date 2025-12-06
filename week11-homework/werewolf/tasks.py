"""
游戏任务定义 - 使用 CrewAI Task
"""
from crewai import Task
from typing import List, Dict
from .agents import WerewolfAgent, ModeratorAgent


def create_night_action_task(
    werewolf_agents: List[WerewolfAgent],
    alive_villagers: List[str],
    round_num: int
) -> Task:
    """
    创建夜晚行动任务 - 狼人选择目标
    
    Args:
        werewolf_agents: 狼人 Agent 列表
        alive_villagers: 存活的村民名单
        round_num: 当前回合数
    """
    if not werewolf_agents:
        return None
    
    # 使用第一个狼人作为主要决策者
    leader = werewolf_agents[0]
    
    # 获取狼人名单
    werewolf_names = [w.name for w in werewolf_agents]
    werewolf_list = "、".join(werewolf_names)
    
    villager_list = ", ".join(alive_villagers)
    
    task = Task(
        description=f"""
第{round_num}轮 - 夜晚阶段

【游戏信息】
- 本局只有狼人和村民两种角色，没有其他特殊角色
- 狼人团队: {werewolf_list}（你们可以互相认识）
- 当前存活的村民有: {villager_list}

【你的任务】
与其他狼人讨论并决定今晚让哪个村民玩家出局。

作为狼人，你需要:
1. 分析每个村民的威胁程度
2. 回忆之前的发言和投票情况
3. 选择一个最佳的目标
4. 给出充分的理由

请使用你的工具（记忆检索、玩家分析等）来帮助做出决策。

最终输出格式: 
目标: [玩家名字]
理由: [详细理由]
""",
        agent=leader.agent,
        expected_output="选择一个目标并给出理由"
    )
    
    return task


def create_discussion_task(
    player_agent: WerewolfAgent,
    round_num: int,
    night_death: str,
    all_alive_players: List[str]
) -> Task:
    """
    创建讨论发言任务
    
    Args:
        player_agent: 玩家 Agent
        round_num: 当前回合数
        night_death: 昨晚死亡的玩家
        all_alive_players: 所有存活玩家
    """
    players_list = ", ".join(all_alive_players)
    
    task = Task(
        description=f"""
第{round_num}轮 - 白天讨论阶段

【游戏背景】
- 本局只有狼人和村民两种角色
- 没有女巫、预言家、猎人等特殊角色
- 狼人数量：2人（隐藏在玩家中）
- 村民数量：4人（普通村民，无特殊技能）

【当前情况】
昨晚 {night_death} 出局了！
当前存活的玩家有: {players_list}

【你的任务】
现在是发言环节，作为 {player_agent.name}，你需要:

1. 使用记忆检索工具回顾之前的游戏过程
2. 分析昨晚出局的玩家和可能的嫌疑人
3. 表达你的观点和推理
4. 指出你认为可疑的玩家
5. 发言要符合你的角色身份和性格特点

{'注意：你是狼人，要隐藏身份，伪装成村民！不要暴露自己！' if player_agent.role.value == 'werewolf' else '注意：仔细分析，找出狼人！记住游戏里只有狼人和村民两种角色。'}

请使用你的工具来:
- 检索相关记忆
- 分析其他玩家的行为
- 跟踪你的怀疑对象
- 查询游戏状态

最终输出你的发言内容（200字以内）。
""",
        agent=player_agent.agent,
        expected_output="一段分析和发言内容，表达对局势的看法和怀疑对象"
    )
    
    return task


def create_vote_task(
    player_agent: WerewolfAgent,
    round_num: int,
    candidates: List[str]
) -> Task:
    """
    创建投票任务
    
    Args:
        player_agent: 玩家 Agent
        round_num: 当前回合数
        candidates: 候选人列表（所有存活玩家）
    """
    candidates_list = ", ".join(candidates)
    
    task = Task(
        description=f"""
第{round_num}轮 - 投票阶段

【游戏信息】
- 本局只有狼人（2人）和村民（4人）两种角色
- 没有其他特殊角色和技能

【投票任务】
你需要投票淘汰一名玩家。
候选人: {candidates_list}

作为 {player_agent.name}，你需要:

1. 回顾刚才的讨论发言
2. 使用投票分析工具分析各个候选人
3. 检索关于嫌疑人的记忆
4. 做出你的投票决策

{'提示：作为狼人，要投票给村民，避免暴露身份' if player_agent.role.value == 'werewolf' else '提示：投票给你最怀疑的狼人，记住本局只有2个狼人'}

使用你的工具:
- 记忆检索：回顾相关信息
- 投票分析：分析候选人
- 玩家分析：深入分析特定玩家
- 嫌疑跟踪：查看你的怀疑记录

最终输出格式:
投票: [玩家名字]
理由: [简要理由]
""",
        agent=player_agent.agent,
        expected_output="投票给一名玩家并给出理由"
    )
    
    return task


def create_moderator_announcement_task(
    moderator: ModeratorAgent,
    announcement_type: str,
    details: Dict
) -> Task:
    """
    创建主持人宣布任务
    
    Args:
        moderator: 主持人 Agent
        announcement_type: 宣布类型 (night_death, vote_result, game_end)
        details: 详细信息
    """
    if announcement_type == "night_death":
        description = f"""
作为游戏主持人，宣布昨晚的死亡情况。

昨晚死亡的玩家: {details.get('victim', 'unknown')}

请用简洁、正式的语言宣布这个消息。
"""
    
    elif announcement_type == "vote_result":
        description = f"""
作为游戏主持人，宣布投票结果。

被投票处决的玩家: {details.get('executed', 'unknown')}
投票统计: {details.get('votes', {})}

请宣布投票结果和被处决的玩家。
"""
    
    elif announcement_type == "game_end":
        winner = details.get('winner', 'unknown')
        description = f"""
作为游戏主持人，宣布游戏结束。

获胜方: {winner}
存活的{winner}: {details.get('survivors', [])}

请宣布游戏结果和获胜方。
"""
    
    else:
        description = "宣布游戏信息"
    
    task = Task(
        description=description,
        agent=moderator.agent,
        expected_output="主持人的宣布内容"
    )
    
    return task
