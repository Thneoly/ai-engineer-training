"""
记忆管理系统 - 实现情景记忆和语义记忆
使用 ChromaDB 作为向量数据库进行 RAG 检索
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
import chromadb
from chromadb.config import Settings
import json
import hashlib


class Memory:
    """单条记忆"""
    def __init__(
        self, 
        content: str, 
        memory_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        self.content = content
        self.memory_type = memory_type  # 'episodic' or 'semantic'
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "memory_type": self.memory_type,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


def _sanitize_collection_name(name: str) -> str:
    """
    将玩家名称转换为 ChromaDB 兼容的集合名称
    ChromaDB 只接受 [a-zA-Z0-9._-] 字符，3-512 个字符
    """
    # 使用 MD5 哈希处理中文名称
    hash_suffix = hashlib.md5(name.encode('utf-8')).hexdigest()[:8]
    
    # 只保留 ASCII 字母、数字、点、下划线、横线
    safe_chars = []
    for c in name:
        if c.isascii() and (c.isalnum() or c in '._-'):
            safe_chars.append(c)
        elif c.isspace():
            safe_chars.append('_')
    
    safe_name = ''.join(safe_chars)
    
    # 如果名称为空或全是非法字符（如全中文名），使用哈希值
    if not safe_name or not any(c.isalnum() for c in safe_name):
        safe_name = f"player_{hash_suffix}"
    else:
        # 添加哈希后缀确保唯一性
        safe_name = f"{safe_name}_{hash_suffix}"
    
    # 移除开头和结尾的非字母数字字符
    safe_name = safe_name.strip('._-')
    
    # 确保长度在有效范围内（3-512字符）
    if len(safe_name) < 3:
        safe_name = safe_name + "_mem"
    elif len(safe_name) > 512:
        safe_name = safe_name[:504] + hash_suffix
    
    return safe_name


class MemoryManager:
    """
    记忆管理器
    - 情景记忆：具体的游戏事件（谁说了什么，谁被投票等）
    - 语义记忆：总结性的知识（某人的行为模式，推理结论等）
    """
    
    def __init__(self, player_name: str, collection_name: str = "werewolf_memory"):
        self.player_name = player_name
        # 使用安全的集合名称（处理中文字符）
        safe_name = _sanitize_collection_name(player_name)
        self.collection_name = f"{collection_name}_{safe_name}"
        
        # 初始化 ChromaDB
        self.client = chromadb.Client(Settings(
            anonymized_telemetry=False,
            allow_reset=True
        ))
        
        # 创建或获取集合
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        
        # 短期记忆（当前轮次）
        self.short_term_memory: List[Memory] = []
        
        # 统计信息
        self.memory_count = 0
    
    def add_episodic_memory(
        self, 
        content: str, 
        round_num: int,
        phase: str,
        speaker: Optional[str] = None,
        action: Optional[str] = None
    ):
        """添加情景记忆"""
        metadata = {
            "round": round_num,
            "phase": phase,
            "speaker": speaker or "unknown",
            "action": action or "none",
            "player": self.player_name
        }
        
        memory = Memory(content, "episodic", metadata)
        self.short_term_memory.append(memory)
        
        # 存入向量数据库
        self._store_to_vector_db(memory)
    
    def add_semantic_memory(
        self, 
        content: str,
        category: str,
        related_player: Optional[str] = None
    ):
        """添加语义记忆（总结性知识）"""
        metadata = {
            "category": category,  # 如: "suspicion", "analysis", "pattern"
            "related_player": related_player or "general",
            "player": self.player_name
        }
        
        memory = Memory(content, "semantic", metadata)
        self.short_term_memory.append(memory)
        
        # 存入向量数据库
        self._store_to_vector_db(memory)
    
    def _store_to_vector_db(self, memory: Memory):
        """将记忆存入向量数据库"""
        self.memory_count += 1
        
        self.collection.add(
            documents=[memory.content],
            metadatas=[memory.metadata],
            ids=[f"{self.player_name}_memory_{self.memory_count}"]
        )
    
    def retrieve_relevant_memories(
        self, 
        query: str, 
        top_k: int = 5,
        memory_type: Optional[str] = None,
        phase: Optional[str] = None
    ) -> List[Dict]:
        """
        RAG 检索：根据查询检索相关记忆
        
        Args:
            query: 查询内容
            top_k: 返回的记忆数量
            memory_type: 过滤记忆类型 ('episodic' or 'semantic')
            phase: 过滤游戏阶段
        """
        if self.collection.count() == 0:
            return []
        
        # 构建过滤条件
        where_filter = {}
        if memory_type:
            where_filter["memory_type"] = memory_type
        if phase:
            where_filter["phase"] = phase
        
        try:
            # 使用 ChromaDB 进行相似度搜索
            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k, self.collection.count()),
                where=where_filter if where_filter else None
            )
            
            # 格式化结果
            memories = []
            if results['documents'] and len(results['documents']) > 0:
                for i, doc in enumerate(results['documents'][0]):
                    memory_dict = {
                        "content": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results.get('distances') else 0
                    }
                    memories.append(memory_dict)
            
            return memories
        except Exception as e:
            print(f"检索记忆时出错: {e}")
            return []
    
    def get_recent_memories(self, count: int = 10) -> List[Memory]:
        """获取最近的记忆（短期记忆）"""
        return self.short_term_memory[-count:]
    
    def get_memories_about_player(self, player_name: str, top_k: int = 5) -> List[Dict]:
        """获取关于特定玩家的记忆"""
        query = f"关于{player_name}的信息和行为"
        return self.retrieve_relevant_memories(query, top_k=top_k)
    
    def summarize_round(self, round_num: int) -> str:
        """总结某一轮的记忆"""
        round_memories = [
            m for m in self.short_term_memory 
            if m.metadata.get("round") == round_num
        ]
        
        if not round_memories:
            return f"第{round_num}轮没有记录"
        
        summary = f"第{round_num}轮总结:\n"
        for mem in round_memories:
            summary += f"- {mem.content}\n"
        
        return summary
    
    def clear_short_term_memory(self):
        """清空短期记忆（用于新一轮游戏）"""
        self.short_term_memory = []
    
    def reset(self):
        """重置所有记忆"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            self.short_term_memory = []
            self.memory_count = 0
        except Exception as e:
            print(f"重置记忆时出错: {e}")
    
    def export_memories(self) -> List[Dict]:
        """导出所有记忆（用于分析和日志）"""
        return [m.to_dict() for m in self.short_term_memory]
    
    def get_memory_stats(self) -> Dict:
        """获取记忆统计信息"""
        episodic_count = len([m for m in self.short_term_memory if m.memory_type == "episodic"])
        semantic_count = len([m for m in self.short_term_memory if m.memory_type == "semantic"])
        
        return {
            "player": self.player_name,
            "total_memories": len(self.short_term_memory),
            "episodic_memories": episodic_count,
            "semantic_memories": semantic_count,
            "vector_db_count": self.collection.count()
        }


class GameMemoryManager:
    """游戏全局记忆管理器"""
    
    def __init__(self):
        self.player_memories: Dict[str, MemoryManager] = {}
        self.game_history: List[Dict] = []  # 游戏事件历史
    
    def create_player_memory(self, player_name: str) -> MemoryManager:
        """为玩家创建记忆管理器"""
        memory_manager = MemoryManager(player_name)
        self.player_memories[player_name] = memory_manager
        return memory_manager
    
    def get_player_memory(self, player_name: str) -> Optional[MemoryManager]:
        """获取玩家的记忆管理器"""
        return self.player_memories.get(player_name)
    
    def add_game_event(
        self, 
        event_type: str, 
        description: str, 
        round_num: int,
        phase: str,
        involved_players: List[str] = None
    ):
        """添加游戏事件到全局历史"""
        event = {
            "type": event_type,
            "description": description,
            "round": round_num,
            "phase": phase,
            "involved_players": involved_players or [],
            "timestamp": datetime.now().isoformat()
        }
        self.game_history.append(event)
    
    def get_game_history(self, round_num: Optional[int] = None) -> List[Dict]:
        """获取游戏历史"""
        if round_num is not None:
            return [e for e in self.game_history if e["round"] == round_num]
        return self.game_history
    
    def reset_all(self):
        """重置所有记忆"""
        for memory_manager in self.player_memories.values():
            memory_manager.reset()
        self.game_history = []
    
    def export_all_memories(self) -> Dict:
        """导出所有玩家的记忆"""
        return {
            player: manager.export_memories()
            for player, manager in self.player_memories.items()
        }
    
    def get_all_stats(self) -> Dict:
        """获取所有记忆统计"""
        return {
            player: manager.get_memory_stats()
            for player, manager in self.player_memories.items()
        }
