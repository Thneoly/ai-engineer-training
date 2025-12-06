"""
狼人杀游戏 Streamlit Web 界面 - 简化版
运行方式: streamlit run werewolf/web_ui_simple.py
"""

import streamlit as st
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 页面配置
st.set_page_config(
    page_title="🐺 狼人杀多智能体游戏",
    page_icon="🐺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 标题
st.title("🐺 狼人杀多智能体游戏")
st.markdown("---")

# 初始化 session state
if 'mode' not in st.session_state:
    st.session_state.mode = "welcome"

def get_available_logs():
    """获取所有可用的游戏日志"""
    logs_dir = Path(__file__).parent.parent / "logs"
    if not logs_dir.exists():
        return []
    
    log_files = sorted(
        list(logs_dir.glob("werewolf_game_*.txt")),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    return log_files

def load_game_log(log_file: Path):
    """加载游戏日志"""
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"加载失败: {str(e)}"

# ==================== 侧边栏 ====================
with st.sidebar:
    st.header("🎮 游戏控制台")
    st.markdown("---")
    
    mode = st.radio(
        "选择模式",
        ["🏠 欢迎页面", "🎮 开始新游戏", "📁 查看历史对局"],
        key="mode_selector"
    )
    
    if mode == "🎮 开始新游戏":
        st.session_state.mode = "new_game"
    elif mode == "📁 查看历史对局":
        st.session_state.mode = "history"
    else:
        st.session_state.mode = "welcome"
    
    st.markdown("---")
    st.markdown("### 📊 统计信息")
    total_games = len(get_available_logs())
    st.metric("历史对局数", total_games)

# ==================== 主界面 ====================

if st.session_state.mode == "welcome":
    # 欢迎页面
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
    
    点击左侧的"开始新游戏"或"查看历史对局"按钮开始！
    """)
    
    # 显示统计数据
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("历史对局", len(get_available_logs()))
    
    with col2:
        st.metric("AI 玩家", 6)
    
    with col3:
        st.metric("智能工具", 5)

elif st.session_state.mode == "new_game":
    # 开始新游戏
    st.markdown("## 🎮 开始新游戏")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.info("""
        ### 游戏配置
        
        **玩家配置**: 6 名玩家（2 狼人 + 4 村民）
        - Alpha (狼人)
        - Beta (狼人)
        - Alice (村民)
        - Bob (村民)
        - Charlie (村民)
        - David (村民)
        
        **游戏设置**:
        - 最大回合数: 8 轮
        - 模型: Qwen-plus
        - 记忆系统: 双层（情节+语义）
        """)
    
    with col2:
        st.markdown("### 📖 运行方式")
        
        if st.button("� 复制命令", type="primary", use_container_width=True):
            st.success("请在终端执行以下命令")
    
    st.markdown("---")
    st.markdown("""
    ### 💡 提示
    
    1. **命令行运行**: 当前版本需要在终端运行游戏
    2. **查看输出**: 游戏过程会输出到终端
    3. **日志保存**: 游戏结束后日志保存到 `logs/` 目录
    4. **回放对局**: 完成后可在"查看历史对局"中回放
    
    ### 📝 运行命令
    
    ```bash
    # 进入项目目录
    cd /path/to/week11-homework
    
    # 激活虚拟环境
    source .venv/bin/activate
    
    # 运行游戏
    python -m werewolf.main
    ```
    """)

elif st.session_state.mode == "history":
    # 查看历史对局
    st.markdown("## 📁 查看历史对局")
    
    log_files = get_available_logs()
    
    if log_files:
        # 选择对局
        selected_log = st.selectbox(
            "选择对局",
            log_files,
            format_func=lambda x: f"{x.stem.replace('werewolf_game_', '')} ({x.stat().st_size // 1024} KB)",
            key="log_selector"
        )
        
        if selected_log:
            col1, col2 = st.columns([3, 1])
            
            with col2:
                st.markdown("### 📊 对局信息")
                st.metric("文件大小", f"{selected_log.stat().st_size // 1024} KB")
                st.metric("修改时间", datetime.fromtimestamp(selected_log.stat().st_mtime).strftime("%Y-%m-%d %H:%M"))
            
            with col1:
                st.markdown("### 📖 游戏记录")
                
                # 加载并显示日志
                log_content = load_game_log(selected_log)
                
                # 添加搜索功能
                search_term = st.text_input("🔍 搜索关键词", key="search")
                
                if search_term:
                    # 高亮显示搜索结果
                    lines = log_content.split('\n')
                    filtered_lines = [line for line in lines if search_term.lower() in line.lower()]
                    if filtered_lines:
                        st.success(f"找到 {len(filtered_lines)} 条匹配记录")
                        st.text_area(
                            "搜索结果",
                            '\n'.join(filtered_lines),
                            height=500,
                            key="search_results"
                        )
                    else:
                        st.warning("未找到匹配记录")
                else:
                    # 显示完整日志
                    st.text_area(
                        "完整日志",
                        log_content,
                        height=600,
                        key="full_log"
                    )
                
                # 下载按钮
                st.download_button(
                    label="📥 下载日志",
                    data=log_content,
                    file_name=selected_log.name,
                    mime="text/plain",
                    key="download_log"
                )
    else:
        st.info("""
        ### 暂无历史对局记录
        
        请先运行一局游戏：
        
        ```bash
        python -m werewolf.main
        ```
        
        游戏结束后，日志会保存到 `logs/` 目录。
        """)

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>🐺 狼人杀多智能体游戏 | Powered by CrewAI + Qwen | Week 11 作业</p>
</div>
""", unsafe_allow_html=True)
