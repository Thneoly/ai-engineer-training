"""
Streamlit 可视化界面（可选）
运行方式: streamlit run werewolf/visualizer.py
"""
import streamlit as st
import json
from pathlib import Path
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="狼人杀游戏观战", layout="wide")

st.title("🐺 狼人杀游戏日志查看器")

# 选择日志文件
log_dir = Path("./logs")
if not log_dir.exists():
    st.error("logs 目录不存在，请先运行游戏")
    st.stop()

log_files = list(log_dir.glob("werewolf_game_*.json"))
if not log_files:
    st.warning("没有找到游戏日志文件")
    st.stop()

# 文件选择器
selected_file = st.selectbox(
    "选择游戏日志",
    log_files,
    format_func=lambda x: x.name
)

# 加载日志
with open(selected_file, 'r', encoding='utf-8') as f:
    game_data = json.load(f)

# 显示游戏概况
st.header("📊 游戏概况")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("总回合数", game_data.get('total_rounds', 0))
with col2:
    winner = game_data.get('winner', 'unknown')
    st.metric("获胜方", winner.upper() if winner else "未知")
with col3:
    duration = game_data.get('duration_seconds', 0)
    st.metric("游戏时长", f"{duration:.1f}秒")
with col4:
    alive_count = len(game_data.get('alive_players', []))
    st.metric("存活玩家", alive_count)

# 玩家状态
st.header("👥 玩家状态")
col1, col2 = st.columns(2)

with col1:
    st.subheader("✅ 存活玩家")
    for player in game_data.get('alive_players', []):
        st.success(player)

with col2:
    st.subheader("💀 死亡玩家")
    for player in game_data.get('dead_players', []):
        st.error(player)

# 游戏过程
st.header("📜 游戏过程")

game_log = game_data.get('game_log', [])

# 按回合过滤
rounds = sorted(set(entry.get('round', 0) for entry in game_log))
selected_round = st.selectbox("选择回合", ["全部"] + [f"第{r}轮" for r in rounds if r > 0])

# 过滤日志
if selected_round != "全部":
    round_num = int(selected_round.replace("第", "").replace("轮", ""))
    filtered_log = [entry for entry in game_log if entry.get('round') == round_num]
else:
    filtered_log = game_log

# 显示日志
for entry in filtered_log:
    category = entry.get('category', 'INFO')
    message = entry.get('message', '')
    phase = entry.get('phase', '')
    round_num = entry.get('round', 0)
    
    # 根据类别选择颜色
    if category == "PHASE":
        st.markdown(f"### {message}")
    elif category == "SPEECH":
        st.info(f"💬 {message}")
    elif category == "DECISION":
        st.warning(f"⚡ {message}")
    elif category == "ANNOUNCEMENT":
        st.success(f"📢 {message}")
    elif category == "ERROR":
        st.error(f"❌ {message}")
    else:
        st.text(f"[{category}] {message}")

# 记忆统计
st.header("🧠 记忆统计")

memory_stats = game_data.get('memory_stats', {})
if memory_stats:
    stats_data = []
    for player, stats in memory_stats.items():
        stats_data.append({
            "玩家": player,
            "总记忆数": stats.get('total_memories', 0),
            "情景记忆": stats.get('episodic_memories', 0),
            "语义记忆": stats.get('semantic_memories', 0),
            "向量DB记录": stats.get('vector_db_count', 0)
        })
    
    df = pd.DataFrame(stats_data)
    st.dataframe(df, use_container_width=True)
    
    # 图表
    st.bar_chart(df.set_index('玩家')[['情景记忆', '语义记忆']])
else:
    st.info("没有记忆统计数据")

# 下载原始数据
st.header("💾 下载数据")
st.download_button(
    label="下载 JSON 日志",
    data=json.dumps(game_data, ensure_ascii=False, indent=2),
    file_name=f"game_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    mime="application/json"
)

st.markdown("---")
st.caption("狼人杀游戏系统 - 基于 CrewAI 框架")
