#!/bin/bash
# 狼人杀游戏快速启动脚本

echo "======================================"
echo "  狼人杀游戏系统 - 快速启动"
echo "======================================"
echo ""

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件"
    echo "正在从 .env.example 创建..."
    cp .env.example .env
    echo "✓ 已创建 .env 文件"
    echo ""
    echo "请编辑 .env 文件，添加你的 OPENAI_API_KEY"
    echo "然后重新运行此脚本"
    exit 1
fi

# 检查 API Key
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo "⚠️  请在 .env 文件中配置有效的 OPENAI_API_KEY"
    echo ""
    echo "编辑 .env 文件："
    echo "  OPENAI_API_KEY=sk-your_key_here"
    exit 1
fi

echo "✓ 环境配置检查通过"
echo ""

# 安装依赖
echo "正在检查依赖..."
uv sync --quiet
echo "✓ 依赖已就绪"
echo ""

# 启动游戏
echo "======================================"
echo "  开始游戏！"
echo "======================================"
echo ""
uv sync
uv run python -m werewolf.main
