"""
狼人杀游戏主入口
使用 CrewAI 框架实现的智能体协作游戏系统
"""
import os
from dotenv import load_dotenv
from .game import WerewolfGame
from .logger import GameLogger, export_game_replay
from .config import game_config


def main():
    """
    游戏主入口
    在根目录可以通过 python -m werewolf.main 运行
    """
    # 加载环境变量
    load_dotenv()
    
    # 检查千问 API Key
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("错误: 请设置 DASHSCOPE_API_KEY 环境变量")
        print("可以在项目根目录创建 .env 文件，添加:")
        print("DASHSCOPE_API_KEY=your_api_key_here")
        return
    
    print("\n" + "="*80)
    print("欢迎来到狼人杀游戏！")
    print("使用 CrewAI 框架实现的 AI 智能体协作系统")
    print("="*80 + "\n")
    
    # 显示游戏配置
    print("游戏配置:")
    print(f"  玩家总数: {game_config.TOTAL_PLAYERS}")
    print(f"  狼人数量: {game_config.NUM_WEREWOLVES}")
    print(f"  村民数量: {game_config.NUM_VILLAGERS}")
    print(f"  LLM 模型: {game_config.LLM_MODEL}")
    print(f"  最大回合数: {game_config.MAX_ROUNDS}")
    print()
    
    # 创建游戏
    game = WerewolfGame()
    
    # 创建日志记录器
    logger = GameLogger()
    
    try:
        # 开始游戏
        print("游戏即将开始...\n")
        game_summary = game.play()
        
        print("\n" + "="*80)
        print("游戏结束！")
        print("="*80 + "\n")
        
        # 保存游戏日志
        logger.save_game_log(game_summary)
        logger.generate_readable_log(game_summary)
        
        # 导出游戏回放
        export_game_replay(game_summary)
        
        # 分析游戏
        analysis = logger.analyze_game(game_summary)
        logger.print_analysis(analysis)
        
        print("\n游戏日志已保存到 ./logs 目录")
        print("你可以查看:")
        print("  - JSON 格式的详细日志")
        print("  - TXT 格式的可读日志")
        print("  - 游戏回放数据")
        
    except KeyboardInterrupt:
        print("\n\n游戏被用户中断")
    except Exception as e:
        print(f"\n游戏运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()