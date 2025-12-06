"""
游戏日志和分析工具
"""
import json
from typing import Dict, List
from datetime import datetime
from pathlib import Path


class GameLogger:
    """游戏日志记录器"""
    
    def __init__(self, output_dir: str = "./logs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.current_game_log = []
    
    def save_game_log(self, game_summary: Dict, filename: str = None):
        """保存游戏日志到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"werewolf_game_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(game_summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n游戏日志已保存到: {filepath}")
        return filepath
    
    def generate_readable_log(self, game_summary: Dict, filename: str = None):
        """生成可读的游戏日志文本"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"werewolf_game_{timestamp}.txt"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("狼人杀游戏日志\n")
            f.write("=" * 80 + "\n\n")
            
            # 游戏概况
            f.write(f"总回合数: {game_summary.get('total_rounds', 0)}\n")
            f.write(f"获胜方: {game_summary.get('winner', 'unknown').upper()}\n")
            f.write(f"游戏时长: {game_summary.get('duration_seconds', 0):.2f} 秒\n")
            f.write(f"存活玩家: {', '.join(game_summary.get('alive_players', []))}\n")
            f.write(f"死亡玩家: {', '.join(game_summary.get('dead_players', []))}\n\n")
            
            # 游戏过程
            f.write("=" * 80 + "\n")
            f.write("游戏过程记录\n")
            f.write("=" * 80 + "\n\n")
            
            game_log = game_summary.get('game_log', [])
            current_round = 0
            
            for entry in game_log:
                round_num = entry.get('round', 0)
                
                # 新回合标记
                if round_num != current_round:
                    current_round = round_num
                    f.write(f"\n{'='*60}\n")
                    f.write(f"第 {round_num} 轮\n")
                    f.write(f"{'='*60}\n\n")
                
                category = entry.get('category', 'INFO')
                message = entry.get('message', '')
                phase = entry.get('phase', '')
                
                f.write(f"[{category}] [{phase}] {message}\n")
            
            # 记忆统计
            f.write("\n" + "=" * 80 + "\n")
            f.write("记忆统计\n")
            f.write("=" * 80 + "\n\n")
            
            memory_stats = game_summary.get('memory_stats', {})
            for player, stats in memory_stats.items():
                f.write(f"{player}:\n")
                f.write(f"  总记忆数: {stats.get('total_memories', 0)}\n")
                f.write(f"  情景记忆: {stats.get('episodic_memories', 0)}\n")
                f.write(f"  语义记忆: {stats.get('semantic_memories', 0)}\n")
                f.write(f"  向量数据库记录数: {stats.get('vector_db_count', 0)}\n\n")
        
        print(f"可读日志已保存到: {filepath}")
        return filepath
    
    def analyze_game(self, game_summary: Dict) -> Dict:
        """分析游戏数据"""
        analysis = {
            "game_duration": game_summary.get('duration_seconds', 0),
            "total_rounds": game_summary.get('total_rounds', 0),
            "winner": game_summary.get('winner', 'unknown'),
            "survival_rate": {
                "total": len(game_summary.get('alive_players', [])) / 
                        (len(game_summary.get('alive_players', [])) + 
                         len(game_summary.get('dead_players', []))),
            },
            "memory_usage": {},
            "phase_distribution": {},
        }
        
        # 分析记忆使用情况
        memory_stats = game_summary.get('memory_stats', {})
        total_memories = sum(stats.get('total_memories', 0) for stats in memory_stats.values())
        analysis["memory_usage"] = {
            "total_memories": total_memories,
            "avg_per_player": total_memories / len(memory_stats) if memory_stats else 0,
            "by_player": memory_stats
        }
        
        # 分析阶段分布
        game_log = game_summary.get('game_log', [])
        phase_counts = {}
        for entry in game_log:
            phase = entry.get('phase', 'unknown')
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
        
        analysis["phase_distribution"] = phase_counts
        
        return analysis
    
    def print_analysis(self, analysis: Dict):
        """打印分析结果"""
        print("\n" + "=" * 80)
        print("游戏分析报告")
        print("=" * 80 + "\n")
        
        print(f"游戏时长: {analysis['game_duration']:.2f} 秒")
        print(f"总回合数: {analysis['total_rounds']}")
        print(f"获胜方: {analysis['winner'].upper()}")
        print(f"存活率: {analysis['survival_rate']['total']:.2%}\n")
        
        print("记忆使用情况:")
        print(f"  总记忆数: {analysis['memory_usage']['total_memories']}")
        print(f"  平均每人: {analysis['memory_usage']['avg_per_player']:.1f}\n")
        
        print("阶段分布:")
        for phase, count in analysis['phase_distribution'].items():
            print(f"  {phase}: {count} 条记录")


def export_game_replay(game_summary: Dict, output_file: str = None):
    """
    导出游戏回放数据（用于可视化）
    
    Args:
        game_summary: 游戏总结数据
        output_file: 输出文件路径
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"./logs/replay_{timestamp}.json"
    
    # 提取关键事件
    replay_data = {
        "game_info": {
            "total_rounds": game_summary.get('total_rounds', 0),
            "winner": game_summary.get('winner', 'unknown'),
            "duration": game_summary.get('duration_seconds', 0),
        },
        "events": [],
        "players": {
            "alive": game_summary.get('alive_players', []),
            "dead": game_summary.get('dead_players', [])
        }
    }
    
    # 提取事件
    game_log = game_summary.get('game_log', [])
    for entry in game_log:
        if entry.get('category') in ['DECISION', 'ANNOUNCEMENT', 'SPEECH', 'VOTE']:
            replay_data["events"].append({
                "round": entry.get('round', 0),
                "phase": entry.get('phase', ''),
                "type": entry.get('category', ''),
                "message": entry.get('message', ''),
                "timestamp": entry.get('timestamp', 0)
            })
    
    # 保存
    Path(output_file).parent.mkdir(exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(replay_data, f, ensure_ascii=False, indent=2)
    
    print(f"游戏回放数据已导出到: {output_file}")
    return output_file
