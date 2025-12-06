"""
游戏 Agent 定义 - 使用 CrewAI
"""
from crewai import Agent
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
from .config import Role, Personality, PlayerConfig, game_config
from .tools import create_player_tools
from .memory import MemoryManager

# 加载环境变量
load_dotenv()


class WerewolfAgent:
    """狼人杀游戏 Agent 包装类"""
    
    def __init__(
        self,
        player_config: PlayerConfig,
        memory_manager: MemoryManager,
        game_state: Dict,
        llm_model: str = None
    ):
        self.config = player_config
        self.name = player_config.name
        self.role = player_config.role
        self.personality = player_config.personality
        self.alive = player_config.alive
        self.memory_manager = memory_manager
        self.game_state = game_state
        
        # 设置千问模型的环境变量
        # DashScope 提供了 OpenAI 兼容的接口
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY 环境变量未设置")
        
        # 为 CrewAI 设置 OpenAI 环境变量（指向千问）
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        
        # 设置模型名称
        self.llm_model = llm_model or game_config.LLM_MODEL
        
        # 创建工具
        self.tools = create_player_tools(memory_manager, game_state)
        
        # 创建 CrewAI Agent
        self.agent = self._create_agent()

    
    def _create_agent(self) -> Agent:
        """创建 CrewAI Agent"""
        # 获取角色和性格的 prompt
        role_prompts = game_config.get_role_prompts()
        personality_prompts = game_config.get_personality_prompts()
        
        # 组合 backstory
        backstory = f"""
{role_prompts[self.role]}

{personality_prompts[self.personality]}

你的名字是 {self.name}。
你需要利用记忆和观察来做出最佳决策。
在发言时要符合你的角色身份和性格特点。
记住使用你的工具来检索记忆、分析玩家和查询游戏状态。
"""
        
        # 根据角色类型设置目标
        if self.role == Role.WEREWOLF:
            goal = "隐藏狼人身份，消灭所有村民，引导村民投票给无辜的玩家"
        elif self.role == Role.VILLAGER:
            goal = "找出并投票处决所有狼人，保护村民阵营获胜"
        else:  # MODERATOR
            goal = "公正地主持游戏，管理游戏流程，宣布结果"
        
        return Agent(
            role=f"{self.role.value}",
            goal=goal,
            backstory=backstory,
            tools=self.tools if self.role != Role.MODERATOR else [],
            llm=self.llm_model,  # 使用模型名称字符串
            verbose=True,
            allow_delegation=False,
            max_iter=5,  # 增加到 5 次迭代，确保Agent有足够时间调用工具并生成完整发言
            memory=False  # 我们使用自定义的记忆系统
        )
    
    def is_alive(self) -> bool:
        """检查是否存活"""
        return self.alive
    
    def kill(self):
        """杀死玩家"""
        self.alive = False
        self.config.alive = False
    
    def get_identity(self) -> Dict:
        """获取身份信息（调试用）"""
        return {
            "name": self.name,
            "role": self.role.value,
            "personality": self.personality.value,
            "alive": self.alive
        }


class ModeratorAgent:
    """主持人 Agent"""
    
    def __init__(self, game_state: Dict, llm_model: str = None):
        self.name = "主持人"
        self.game_state = game_state
        
        # 设置千问模型的环境变量
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY 环境变量未设置")
        
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        
        self.llm_model = llm_model or game_config.LLM_MODEL
        
        # 创建 CrewAI Agent
        self.agent = self._create_agent()
    
    def _create_agent(self) -> Agent:
        """创建主持人 Agent"""
        role_prompts = game_config.get_role_prompts()
        
        return Agent(
            role="游戏主持人",
            goal="公正地主持狼人杀游戏，确保游戏流程正确执行",
            backstory=role_prompts[Role.MODERATOR],
            tools=[],
            llm=self.llm_model,  # 使用模型名称字符串
            verbose=True,
            allow_delegation=False,
            max_iter=2,
            memory=False
        )
    
    def announce(self, message: str) -> str:
        """主持人宣布信息"""
        return f"【主持人】{message}"


def create_game_agents(
    player_configs: List[PlayerConfig],
    memory_managers: Dict[str, MemoryManager],
    game_state: Dict
) -> Dict[str, WerewolfAgent]:
    """
    创建所有游戏 Agent
    
    Args:
        player_configs: 玩家配置列表
        memory_managers: 玩家记忆管理器字典
        game_state: 游戏状态
    
    Returns:
        玩家名到 Agent 的映射
    """
    agents = {}
    
    for config in player_configs:
        memory_manager = memory_managers.get(config.name)
        if memory_manager:
            agent = WerewolfAgent(
                player_config=config,
                memory_manager=memory_manager,
                game_state=game_state
            )
            agents[config.name] = agent
    
    return agents


def get_werewolf_agents(agents: Dict[str, WerewolfAgent]) -> List[WerewolfAgent]:
    """获取所有狼人 Agent"""
    return [
        agent for agent in agents.values()
        if agent.role == Role.WEREWOLF and agent.is_alive()
    ]


def get_villager_agents(agents: Dict[str, WerewolfAgent]) -> List[WerewolfAgent]:
    """获取所有村民 Agent"""
    return [
        agent for agent in agents.values()
        if agent.role == Role.VILLAGER and agent.is_alive()
    ]


def get_alive_agents(agents: Dict[str, WerewolfAgent]) -> List[WerewolfAgent]:
    """获取所有存活的 Agent"""
    return [agent for agent in agents.values() if agent.is_alive()]
