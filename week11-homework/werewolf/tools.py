"""
游戏工具 - 为 Agent 提供操作能力
"""
from crewai.tools import tool
from typing import Dict, List, Optional
import re


def sanitize_output(text: str) -> str:
    """
    清理输出文本，移除可能泄露身份的信息
    移除"狼人"和"村民"等角色前缀
    """
    # 移除"狼人"和"村民"前缀，但保留玩家名字
    # 例如: "狼人Alpha" -> "Alpha", "村民Bob" -> "Bob"
    text = re.sub(r'狼人(Alpha|Beta|Charlie|David|Alice|Bob)', r'\1', text)
    text = re.sub(r'村民(Alpha|Beta|Charlie|David|Alice|Bob)', r'\1', text)
    
    return text


def create_player_tools(memory_manager, game_state) -> List:
    """为玩家创建工具集"""
    
    @tool("记忆检索")
    def memory_retrieval(query: str, top_k: int = 5) -> str:
        """根据查询内容检索相关的历史记忆和信息，帮助做出更好的决策"""
        memories = memory_manager.retrieve_relevant_memories(query, top_k=top_k)
        
        if not memories:
            return "没有找到相关记忆"
        
        result = "检索到的相关记忆:\n"
        for i, mem in enumerate(memories, 1):
            # 清理可能泄露身份的内容
            content = sanitize_output(mem['content'])
            result += f"{i}. {content}\n"
            if mem.get('metadata'):
                result += f"   (轮次: {mem['metadata'].get('round', 'N/A')}, "
                result += f"阶段: {mem['metadata'].get('phase', 'N/A')})\n"
        
        return result
    
    @tool("玩家分析")
    def player_analysis(player_name: str) -> str:
        """分析特定玩家的历史行为和发言，帮助判断其身份"""
        memories = memory_manager.get_memories_about_player(player_name, top_k=5)
        
        if not memories:
            return f"没有关于{player_name}的记录"
        
        result = f"关于{player_name}的分析:\n"
        for i, mem in enumerate(memories, 1):
            # 清理可能泄露身份的内容
            content = sanitize_output(mem['content'])
            result += f"{i}. {content}\n"
        
        return result
    
    @tool("投票分析")
    def vote_analysis(candidates: str) -> str:
        """分析各个候选人的可疑程度，帮助做出投票决策。candidates 参数应该是逗号分隔的玩家名字"""
        candidate_list = [c.strip() for c in candidates.split(',') if c.strip()]
        result = "投票候选人分析:\n"
        
        for candidate in candidate_list:
            if candidate not in game_state.get("alive_players", []):
                continue
            
            # 检索关于该候选人的记忆
            memories = memory_manager.get_memories_about_player(candidate, top_k=3)
            
            result += f"\n【{candidate}】\n"
            if memories:
                for mem in memories:
                    # 清理可能泄露身份的内容
                    content = sanitize_output(mem['content'])
                    result += f"  - {content}\n"
            else:
                result += "  - 暂无相关信息\n"
        
        return result
    
    @tool("游戏状态查询")
    def game_state_query(query_type: str) -> str:
        """查询当前游戏状态，包括存活玩家、死亡玩家、回合数等信息。query_type 可选值: alive_players, dead_players, round_number, phase"""
        if query_type == "alive_players":
            players = game_state.get("alive_players", [])
            return f"当前存活玩家: {', '.join(players)}"
        
        elif query_type == "dead_players":
            players = game_state.get("dead_players", [])
            if not players:
                return "目前没有玩家死亡"
            return f"已死亡玩家: {', '.join(players)}"
        
        elif query_type == "round_number":
            round_num = game_state.get("round", 0)
            return f"当前是第{round_num}轮"
        
        elif query_type == "phase":
            phase = game_state.get("phase", "unknown")
            return f"当前阶段: {phase}"
        
        else:
            return "未知的查询类型，可选: alive_players, dead_players, round_number, phase"
    
    @tool("嫌疑跟踪")
    def suspicion_tracking(action: str, player_name: str, suspicion_level: Optional[int] = None, reason: Optional[str] = None) -> str:
        """记录和查询对其他玩家的怀疑程度，帮助做出推理和投票决策。
        
        参数:
        - action: 操作类型，'add' 表示添加怀疑记录，'query' 表示查询记录
        - player_name: 目标玩家名字
        - suspicion_level: 怀疑程度(1-10)，仅在 action='add' 时需要
        - reason: 怀疑原因，仅在 action='add' 时需要
        """
        if action == "add":
            # 添加到语义记忆
            level = suspicion_level if suspicion_level is not None else 5
            reason_text = reason if reason else "未说明原因"
            memory_manager.add_semantic_memory(
                f"对{player_name}的怀疑程度为{level}/10，原因: {reason_text}",
                category="suspicion",
                related_player=player_name
            )
            return f"已记录对{player_name}的怀疑: {level}/10 - {reason_text}"
        
        elif action == "query":
            # 查询记忆
            memories = memory_manager.get_memories_about_player(player_name, top_k=3)
            if not memories:
                return f"暂无对{player_name}的怀疑记录"
            
            result = f"{player_name}的相关记录:\n"
            for i, mem in enumerate(memories, 1):
                # 清理可能泄露身份的内容
                content = sanitize_output(mem['content'])
                result += f"{i}. {content}\n"
            return result
        
        else:
            return "未知的操作类型，可选: add, query"
    
    return [
        memory_retrieval,
        player_analysis,
        vote_analysis,
        game_state_query,
        suspicion_tracking,
    ]
