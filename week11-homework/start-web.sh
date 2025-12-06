#!/bin/bash

# 狼人杀游戏 Web 界面启动脚本（使用 uv）

set -e

echo "🐺 启动狼人杀游戏 Web 界面..."
echo "================================"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  警告: .env 文件不存在"
    echo "   正在从模板创建..."
    cp .env.example .env
    echo ""
    echo "⚠️  请编辑 .env 文件，填入你的 DASHSCOPE_API_KEY"
    echo "   然后重新运行此脚本"
    exit 1
fi

# 读取 API Key
source .env
if [ -z "$DASHSCOPE_API_KEY" ] || [ "$DASHSCOPE_API_KEY" = "your-api-key-here" ]; then
    echo "❌ DASHSCOPE_API_KEY 未正确配置"
    echo "   请编辑 .env 文件，填入你的 API Key"
    exit 1
fi

echo "✅ API Key 已配置"
echo ""

# 确保依赖已安装
echo "📦 检查依赖..."
if ! uv pip show streamlit > /dev/null 2>&1; then
    echo "   安装 streamlit..."
    uv pip install streamlit
fi

echo "✅ 依赖已就绪"
echo ""

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "⚠️  虚拟环境不存在，正在创建..."
    uv sync
    echo "✅ 虚拟环境创建完成"
fi

echo "🚀 启动 Streamlit 服务..."
echo ""
echo "访问地址: http://localhost:8501"
echo ""
echo "按 Ctrl+C 停止服务"
echo "================================"
echo ""

# 激活虚拟环境并启动 Streamlit
source .venv/bin/activate
streamlit run werewolf/web_ui.py
