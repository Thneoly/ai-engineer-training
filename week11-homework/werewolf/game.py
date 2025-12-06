"""
游戏主控制器 - 管理游戏流程和状态
"""
from typing import List, Dict, Optional, Tuple
from crewai import Crew
import time
import re
from collections import Counter

from .config import Role, game_config, PlayerConfig
from .agents import (
    WerewolfAgent, ModeratorAgent, 
    create_game_agents, get_werewolf_agents, 
    get_villager_agents, get_alive_agents
)
from .memory import GameMemoryManager
from .tasks import (
    create_night_action_task,
    create_discussion_task,
    create_vote_task,
    create_moderator_announcement_task
)


class WerewolfGame:
    """狼人杀游戏控制器"""
    
    def __init__(self, player_configs: Optional[List[PlayerConfig]] = None):
        """
        初始化游戏
        
        Args:
            player_configs: 玩家配置列表，如果为 None 则使用默认配置
        """
        # 游戏配置
        self.player_configs = player_configs or game_config.create_default_players()
        
        # 游戏状态
        self.game_state = {
            "round": 0,
            "phase": game_config.PHASE_NIGHT,
            "alive_players": [p.name for p in self.player_configs],
            "dead_players": [],
            "werewolves": [p.name for p in self.player_configs if p.role == Role.WEREWOLF],
            "villagers": [p.name for p in self.player_configs if p.role == Role.VILLAGER],
        }
        
        # 记忆管理
        self.memory_manager = GameMemoryManager()
        self.player_memories = {}
        for player in self.player_configs:
            self.player_memories[player.name] = self.memory_manager.create_player_memory(player.name)
        
        # 创建 Agents
        self.agents = create_game_agents(
            self.player_configs,
            self.player_memories,
            self.game_state
        )
        
        # 主持人
        self.moderator = ModeratorAgent(self.game_state)
        
        # 游戏记录
        self.game_log = []
        self.token_usage = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
        self.start_time = None
        self.end_time = None
    
    def log(self, message: str, category: str = "INFO"):
        """记录游戏日志"""
        log_entry = {
            "round": self.game_state["round"],
            "phase": self.game_state["phase"],
            "category": category,
            "message": message,
            "timestamp": time.time()
        }
        self.game_log.append(log_entry)
        print(f"[{category}] {message}")
    
    def werewolf_recognition_phase(self):
        """
        狼人确认身份环节 - 第一个夜晚让狼人互相认识
        这是标准狼人杀流程的一部分
        """
        self.log("\n" + "="*50, "PHASE")
        self.log("🌙 第一个夜晚 - 狼人确认身份", "PHASE")
        self.log("="*50, "PHASE")
        
        # 获取所有狼人
        werewolf_names = self.game_state["werewolves"]
        
        if len(werewolf_names) < 2:
            self.log("只有一个狼人，无需确认", "INFO")
            return
        
        # 为每个狼人添加队友信息到记忆
        for werewolf_name in werewolf_names:
            teammates = [name for name in werewolf_names if name != werewolf_name]
            teammates_str = "、".join(teammates)
            
            # 添加到狼人的记忆中
            self.player_memories[werewolf_name].add_episodic_memory(
                f"【狼人身份确认】我的狼人队友是: {teammates_str}。我们是同一阵营，需要互相配合消灭所有村民。",
                round_num=0,  # 第0轮表示游戏开始前
                phase="recognition",
                action="team_recognition"
            )
            
            self.log(f"✓ {werewolf_name} 已确认队友: {teammates_str}", "INFO")
        
        self.log("\n狼人身份确认完成！游戏正式开始...\n", "PHASE")
    
    def check_win_condition(self) -> Optional[str]:
        """
        检查胜利条件
        
        Returns:
            "werewolves" 如果狼人获胜
            "villagers" 如果村民获胜
            None 如果游戏继续
        """
        alive_werewolves = [
            name for name in self.game_state["werewolves"]
            if name in self.game_state["alive_players"]
        ]
        
        alive_villagers = [
            name for name in self.game_state["villagers"]
            if name in self.game_state["alive_players"]
        ]
        
        # 狼人全部死亡，村民获胜
        if len(alive_werewolves) == 0:
            return "villagers"
        
        # 狼人数量 > 村民数量，狼人获胜（修改为严格大于，让游戏更公平）
        if len(alive_werewolves) > len(alive_villagers):
            return "werewolves"
        
        return None
    
    def night_phase(self) -> Optional[str]:
        """
        夜晚阶段 - 狼人行动
        
        Returns:
            被杀死的玩家名字
        """
        self.log(f"\n{'='*50}\n第{self.game_state['round']}轮 - 夜晚降临\n{'='*50}", "PHASE")
        self.game_state["phase"] = game_config.PHASE_NIGHT
        
        # 获取存活的狼人
        werewolf_agents = [
            self.agents[name] for name in self.game_state["werewolves"]
            if name in self.game_state["alive_players"]
        ]
        
        if not werewolf_agents:
            self.log("没有存活的狼人", "WARNING")
            return None
        
        # 获取存活的村民
        alive_villagers = [
            name for name in self.game_state["villagers"]
            if name in self.game_state["alive_players"]
        ]
        
        if not alive_villagers:
            return None
        
        # 创建狼人行动任务
        task = create_night_action_task(
            werewolf_agents,
            alive_villagers,
            self.game_state["round"]
        )
        
        if not task:
            return None
        
        # 执行任务
        self.log("狼人们正在商议目标...", "ACTION")
        
        try:
            # 让所有狼人都参与讨论（使用 CrewAI 的多 Agent 协作）
            crew = Crew(
                agents=[w.agent for w in werewolf_agents],  # 所有狼人参与
                tasks=[task],
                verbose=True
            )
            
            result = crew.kickoff()
            self.log(f"狼人决策结果:\n{result}", "RESULT")
            
            # 解析结果，提取目标
            victim = self._parse_target_from_result(str(result), alive_villagers)
            
            if victim:
                self.log(f"狼人选择目标: {victim}", "DECISION")
                
                # 添加到所有狼人的记忆
                for werewolf in werewolf_agents:
                    self.player_memories[werewolf.name].add_episodic_memory(
                        f"我们狼人团队讨论后，决定让{victim}出局",
                        self.game_state["round"],
                        game_config.PHASE_NIGHT,
                        action="eliminate"
                    )
                
                return victim
            else:
                # 如果无法解析，随机选择
                import random
                victim = random.choice(alive_villagers)
                self.log(f"无法解析狼人决策，随机选择: {victim}", "WARNING")
                return victim
                
        except Exception as e:
            self.log(f"夜晚阶段执行出错: {e}", "ERROR")
            # 出错时随机选择
            import random
            return random.choice(alive_villagers) if alive_villagers else None
    
    def discussion_phase(self, night_victim: str):
        """
        白天讨论阶段
        
        Args:
            night_victim: 昨晚出局的玩家
        """
        self.log(f"\n{'='*50}\n第{self.game_state['round']}轮 - 白天到来\n{'='*50}", "PHASE")
        self.log(f"昨晚，{night_victim} 出局了！", "ANNOUNCEMENT")
        
        self.game_state["phase"] = game_config.PHASE_DISCUSSION
        
        # 记录出局事件
        self.memory_manager.add_game_event(
            "night_elimination",
            f"{night_victim} 在第{self.game_state['round']}轮夜晚出局",
            self.game_state["round"],
            game_config.PHASE_NIGHT,
            [night_victim]
        )
        
        # 所有玩家添加记忆
        for player_name in self.game_state["alive_players"]:
            self.player_memories[player_name].add_episodic_memory(
                f"{night_victim} 在昨晚出局了",
                self.game_state["round"],
                game_config.PHASE_DAY,
                speaker="moderator"
            )
        
        # 所有存活玩家依次发言
        alive_agents = get_alive_agents(self.agents)
        
        for agent in alive_agents:
            self.log(f"\n--- {agent.name} 发言 ---", "DISCUSSION")
            
            task = create_discussion_task(
                agent,
                self.game_state["round"],
                night_victim,
                self.game_state["alive_players"]
            )
            
            try:
                crew = Crew(
                    agents=[agent.agent],
                    tasks=[task],
                    verbose=False
                )
                
                speech = crew.kickoff()
                self.log(f"{agent.name}: {speech}", "SPEECH")
                
                # 记录发言到所有玩家的记忆
                for player_name in self.game_state["alive_players"]:
                    self.player_memories[player_name].add_episodic_memory(
                        f"{agent.name}说: {speech}",
                        self.game_state["round"],
                        game_config.PHASE_DISCUSSION,
                        speaker=agent.name
                    )
                
            except Exception as e:
                self.log(f"{agent.name} 发言时出错: {e}", "ERROR")
    
    def vote_phase(self) -> Optional[str]:
        """
        投票阶段
        
        Returns:
            被投票处决的玩家名字
        """
        self.log(f"\n{'='*50}\n第{self.game_state['round']}轮 - 投票环节\n{'='*50}", "PHASE")
        self.game_state["phase"] = game_config.PHASE_VOTE
        
        alive_agents = get_alive_agents(self.agents)
        candidates = self.game_state["alive_players"].copy()
        
        votes = {}  # 投票统计
        
        # 所有玩家投票
        for agent in alive_agents:
            self.log(f"\n{agent.name} 正在投票...", "VOTE")
            
            task = create_vote_task(
                agent,
                self.game_state["round"],
                candidates
            )
            
            try:
                crew = Crew(
                    agents=[agent.agent],
                    tasks=[task],
                    verbose=False
                )
                
                vote_result = crew.kickoff()
                self.log(f"{agent.name} 的投票: {vote_result}", "VOTE")
                
                # 解析投票
                voted_player = self._parse_vote_from_result(str(vote_result), candidates)
                
                if voted_player:
                    votes[agent.name] = voted_player
                    self.log(f"{agent.name} 投票给 {voted_player}", "DECISION")
                    
                    # 记录投票到记忆
                    self.player_memories[agent.name].add_episodic_memory(
                        f"我投票给了{voted_player}",
                        self.game_state["round"],
                        game_config.PHASE_VOTE,
                        action="vote"
                    )
                else:
                    self.log(f"{agent.name} 的投票无效", "WARNING")
                    
            except Exception as e:
                self.log(f"{agent.name} 投票时出错: {e}", "ERROR")
        
        # 统计投票结果
        if not votes:
            self.log("没有有效投票", "WARNING")
            return None
        
        vote_counts = Counter(votes.values())
        executed = vote_counts.most_common(1)[0][0]
        
        self.log(f"\n投票统计: {dict(vote_counts)}", "RESULT")
        self.log(f"{executed} 被投票淘汰！", "ANNOUNCEMENT")
        
        # 记录投票结果到所有玩家的记忆
        for player_name in self.game_state["alive_players"]:
            self.player_memories[player_name].add_episodic_memory(
                f"投票结果: {executed} 被淘汰了。投票统计: {dict(vote_counts)}",
                self.game_state["round"],
                game_config.PHASE_VOTE,
                speaker="moderator"
            )
        
        return executed
    
    def _parse_target_from_result(self, result: str, candidates: List[str]) -> Optional[str]:
        """从 AI 结果中解析目标玩家"""
        result_lower = result.lower()
        
        # 尝试多种模式匹配
        patterns = [
            r"目标[：:]\s*([^\n]+)",
            r"选择[：:]\s*([^\n]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, result)
            if match:
                target_text = match.group(1).strip()
                # 检查是否在候选人中
                for candidate in candidates:
                    if candidate in target_text:
                        return candidate
        
        # 直接查找候选人名字
        for candidate in candidates:
            if candidate in result:
                return candidate
        
        return None
    
    def _parse_vote_from_result(self, result: str, candidates: List[str]) -> Optional[str]:
        """从 AI 结果中解析投票对象"""
        result_lower = result.lower()
        
        # 尝试多种模式匹配
        patterns = [
            r"投票[：:]\s*([^\n]+)",
            r"我投[：:]\s*([^\n]+)",
            r"选择[：:]\s*([^\n]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, result)
            if match:
                vote_text = match.group(1).strip()
                # 检查是否在候选人中
                for candidate in candidates:
                    if candidate in vote_text:
                        return candidate
        
        # 直接查找候选人名字
        for candidate in candidates:
            if candidate in result:
                return candidate
        
        return None
    
    def remove_player(self, player_name: str):
        """移除玩家（死亡）"""
        if player_name in self.game_state["alive_players"]:
            self.game_state["alive_players"].remove(player_name)
            self.game_state["dead_players"].append(player_name)
            
            if player_name in self.agents:
                self.agents[player_name].kill()
    
    def play_round(self) -> Optional[str]:
        """
        进行一轮游戏
        
        Returns:
            获胜方 ("werewolves" 或 "villagers") 或 None（游戏继续）
        """
        self.game_state["round"] += 1
        
        # 夜晚阶段
        night_victim = self.night_phase()
        
        if night_victim:
            self.remove_player(night_victim)
        
        # 注意：夜晚阶段后不立即检查胜利条件
        # 需要给村民一个讨论和投票的机会
        
        # 白天讨论
        self.discussion_phase(night_victim)
        
        # 投票阶段
        executed = self.vote_phase()
        
        if executed:
            self.remove_player(executed)
        
        # 在投票后检查胜利条件
        winner = self.check_win_condition()
        return winner
    
    def play(self) -> Dict:
        """
        开始游戏
        
        Returns:
            游戏结果字典
        """
        self.start_time = time.time()
        self.log("\n" + "="*50, "GAME")
        self.log("狼人杀游戏开始！", "GAME")
        self.log("="*50 + "\n", "GAME")
        
        # 显示玩家信息（仅用于调试）
        self.log("玩家信息:", "INFO")
        for player in self.player_configs:
            self.log(f"  {player.name} - {player.role.value} ({player.personality.value})", "INFO")
        
        # 第一个夜晚：狼人确认身份环节
        self.werewolf_recognition_phase()
        
        # 游戏主循环
        winner = None
        while self.game_state["round"] < game_config.MAX_ROUNDS:
            winner = self.play_round()
            
            if winner:
                break
        
        self.end_time = time.time()
        
        # 游戏结束
        if winner:
            self.log(f"\n{'='*50}", "GAME")
            self.log(f"游戏结束！{winner.upper()} 获胜！", "GAME")
            self.log(f"{'='*50}\n", "GAME")
        else:
            self.log("游戏达到最大回合数", "GAME")
        
        # 返回游戏结果
        return self.get_game_summary()
    
    def get_game_summary(self) -> Dict:
        """获取游戏总结"""
        duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        return {
            "total_rounds": self.game_state["round"],
            "winner": self.check_win_condition(),
            "duration_seconds": duration,
            "alive_players": self.game_state["alive_players"],
            "dead_players": self.game_state["dead_players"],
            "game_log": self.game_log,
            "memory_stats": self.memory_manager.get_all_stats(),
        }
