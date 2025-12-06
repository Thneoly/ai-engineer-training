"""
狼人杀游戏 Streamlit Web 界面
运行方式: streamlit run werewolf/web_ui.py
"""

import streamlit as st
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 页面配置（必须在最前面）
st.set_page_config(
    page_title="🐺 狼人杀多智能体游戏",
    page_icon="🐺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 延迟导入，避免启动时加载失败
def get_game_class():
    """延迟导入 WerewolfGame"""
    try:
        from werewolf.game import WerewolfGame
        return WerewolfGame
    except ImportError as e:
        st.error(f"导入失败: {e}")
        st.info("游戏功能暂时不可用，但您可以查看历史对局。")
        return None

# 自定义CSS
st.markdown("""
<style>
    .stAlert {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .player-card {
        padding: 1rem;
        border-radius: 0.5rem;
        background: #f0f2f6;
        margin: 0.5rem 0;
    }
    .round-section {
        padding: 1.5rem;
        border-left: 3px solid #FF4B4B;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 初始化 session state
if 'game' not in st.session_state:
    st.session_state.game = None
if 'game_running' not in st.session_state:
    st.session_state.game_running = False
if 'game_logs' not in st.session_state:
    st.session_state.game_logs = []

def load_game_log(log_file: Path):
    """加载游戏日志"""
    if log_file.suffix == '.json':
        with open(log_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        with open(log_file, 'r', encoding='utf-8') as f:
            return {"text_log": f.read()}

def get_available_logs():
    """获取所有可用的游戏日志"""
    logs_dir = Path(__file__).parent.parent / "logs"
    if not logs_dir.exists():
        return []
    
    log_files = sorted(
        list(logs_dir.glob("werewolf_game_*.json")),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    return log_files

# ==================== 侧边栏 ====================
with st.sidebar:
    st.title("🐺 狼人杀游戏控制台")
    st.markdown("---")
    
    # 游戏模式选择
    mode = st.radio(
        "选择模式",
        ["🎮 开始新游戏", "📁 查看历史对局"],
        index=1 if st.session_state.game is None else 0
    )
    
    if mode == "🎮 开始新游戏":
        st.markdown("### 游戏配置")
        
        st.info("""
        ### ⚠️ 注意
        
        Web 界面暂时不支持直接启动游戏。
        请在终端运行游戏：
        
        ```bash
        python -m werewolf.main
        ```
        
        游戏配置：
        - 玩家数量: 6 (2狼人 + 4村民)
        - 最大回合数: 8 (在 config.py 中配置)
        """)
        
        if st.button("📖 查看运行命令", type="primary", use_container_width=True):
            st.code("""
# 在终端执行以下命令:
cd /home/cc/Desktop/code/AIPro/ai-engineer-training/week11-homework
source .venv/bin/activate
python -m werewolf.main
            """, language="bash")
        
        if st.session_state.game_running:
            st.warning("⚠️ 游戏正在运行中...")
            if st.button("⏸️ 停止游戏", use_container_width=True):
                st.session_state.game_running = False
                st.session_state.game = None
                st.rerun()
    
    else:  # 查看历史对局
        st.markdown("### 历史对局")
        log_files = get_available_logs()
        
        if log_files:
            selected_log = st.selectbox(
                "选择对局",
                log_files,
                format_func=lambda x: x.stem.replace("werewolf_game_", ""),
                key="log_selector"
            )
            
            if st.button("📂 加载对局", type="primary", use_container_width=True):
                with st.spinner("加载中..."):
                    try:
                        log_data = load_game_log(selected_log)
                        st.session_state.current_log = log_data
                        st.success("对局已加载！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"加载失败: {e}")
        else:
            st.info("暂无历史对局记录")
    
    st.markdown("---")
    st.markdown("### 📊 统计信息")
    total_games = len(get_available_logs())
    st.metric("历史对局数", total_games)

# ==================== 主界面 ====================
st.title("🐺 狼人杀多智能体游戏")

# 如果有加载的日志，显示历史对局
if 'current_log' in st.session_state:
    log_data = st.session_state.current_log
    
    # 三列布局
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.subheader("👥 玩家列表")
        
        if 'players' in log_data:
            for player in log_data['players']:
                status = "💀" if player.get('eliminated', False) else "✅"
                role = "🐺" if player.get('role') == 'werewolf' else "👤"
                
                st.markdown(f"""
                <div class="player-card">
                    <b>{status} {player['name']}</b> {role}
                </div>
                """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("💬 游戏进程")
        
        # 使用选项卡展示不同阶段
        tabs = st.tabs(["📖 完整记录", "🌙 夜晚", "☀️ 白天", "🗳️ 投票"])
        
        with tabs[0]:  # 完整记录
            if 'text_log' in log_data:
                st.text_area(
                    "游戏日志",
                    log_data['text_log'],
                    height=600,
                    key="full_log"
                )
            elif 'rounds' in log_data:
                for round_info in log_data['rounds']:
                    with st.expander(f"第 {round_info['number']} 回合", expanded=False):
                        st.markdown(round_info.get('content', ''))
        
        with tabs[1]:  # 夜晚阶段
            st.markdown("### 🌙 狼人行动记录")
            if 'night_actions' in log_data:
                for action in log_data['night_actions']:
                    st.info(f"**回合 {action['round']}**: {action['content']}")
            else:
                st.warning("暂无夜晚记录")
        
        with tabs[2]:  # 白天讨论
            st.markdown("### ☀️ 讨论发言")
            if 'discussions' in log_data:
                for disc in log_data['discussions']:
                    st.chat_message(disc['player']).write(disc['content'])
            else:
                st.warning("暂无讨论记录")
        
        with tabs[3]:  # 投票
            st.markdown("### 🗳️ 投票统计")
            if 'votes' in log_data:
                for vote_round in log_data['votes']:
                    st.markdown(f"**第 {vote_round['round']} 回合**")
                    st.bar_chart(vote_round['data'])
            else:
                st.warning("暂无投票记录")
    
    with col3:
        st.subheader("📊 游戏统计")
        
        # 游戏结果
        if 'result' in log_data:
            result = log_data['result']
            if result.get('winner') == 'werewolf':
                st.success("🐺 狼人获胜！")
            elif result.get('winner') == 'villager':
                st.success("👥 村民获胜！")
            
            st.metric("游戏回合数", result.get('total_rounds', 'N/A'))
        
        # 记忆统计
        if 'memories' in log_data:
            st.markdown("### 🧠 记忆统计")
            for player, memories in log_data['memories'].items():
                with st.expander(f"📝 {player}"):
                    episodic = memories.get('episodic', [])
                    semantic = memories.get('semantic', [])
                    
                    st.metric("情节记忆", len(episodic))
                    st.metric("语义记忆", len(semantic))
                    
                    if episodic:
                        st.markdown("**最新记忆:**")
                        st.text(episodic[-1][:100] + "...")

# 如果正在运行新游戏
elif st.session_state.game_running:
    st.info("🎮 游戏正在运行中，请查看终端输出...")
    
    # 显示实时进度
    progress_placeholder = st.empty()
    log_placeholder = st.empty()
    
    # 这里可以通过 WebSocket 或轮询获取实时游戏状态
    # 简化版本：显示提示信息
    st.markdown("""
    ### 游戏运行中...
    
    - 请在终端查看实时游戏输出
    - 游戏结束后可在"查看历史对局"中回放
    - 日志文件保存在 `logs/` 目录
    """)

# 默认欢迎页面
else:
    st.markdown("""
    ## 欢迎来到狼人杀多智能体游戏！
    
    ### 🎯 功能特性
    
    - 🤖 **多智能体协作**: 6 个 AI 玩家（2 狼人 + 4 村民）
    - 🧠 **双层记忆系统**: 情节记忆 + 语义记忆
    - 🛠️ **5 个智能工具**: 历史查询、嫌疑跟踪、策略规划等
    - 🎮 **完整游戏流程**: 确认、夜晚、讨论、投票、判定
    - 📊 **详细日志记录**: 文本 + JSON 双格式
    
    ### 📖 使用指南
    
    1. **开始新游戏**: 在左侧选择"开始新游戏"
    2. **查看历史**: 选择"查看历史对局"浏览往期记录
    3. **分析对局**: 查看玩家发言、投票统计、记忆数据
    
    ### 🚀 快速开始
    
    点击左侧的"开始新游戏"按钮开始你的第一局游戏！
    """)
    
    # 显示一些统计数据
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("历史对局", len(get_available_logs()))
    
    with col2:
        st.metric("AI 玩家", 6)
    
    with col3:
        st.metric("智能工具", 5)

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>🐺 狼人杀多智能体游戏 | Powered by CrewAI + Qwen | Week 11 作业</p>
</div>
""", unsafe_allow_html=True)
