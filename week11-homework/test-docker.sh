#!/bin/bash

# 狼人杀游戏 - Docker 测试脚本

set -e

echo "🐺 狼人杀游戏 - Docker 环境测试"
echo "=================================="

# 检查 Docker 是否安装
echo ""
echo "1️⃣  检查 Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装"
    echo "请访问 https://www.docker.com/products/docker-desktop/ 下载安装"
    exit 1
fi
echo "✅ Docker 已安装: $(docker --version)"

# 检查 Docker Compose 是否可用
echo ""
echo "2️⃣  检查 Docker Compose..."
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 未安装"
    exit 1
fi
echo "✅ Docker Compose 已安装"

# 检查 .env 文件
echo ""
echo "3️⃣  检查配置文件..."
if [ ! -f .env ]; then
    echo "⚠️  .env 文件不存在，从模板创建..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件，填入你的 DASHSCOPE_API_KEY"
    echo ""
    echo "需要修改的内容："
    echo "  DASHSCOPE_API_KEY=your-api-key-here"
    echo ""
    read -p "是否已经配置好 API Key？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "请先配置 API Key 后再运行此脚本"
        exit 1
    fi
fi

# 读取 API Key
source .env
if [ -z "$DASHSCOPE_API_KEY" ] || [ "$DASHSCOPE_API_KEY" = "your-api-key-here" ]; then
    echo "❌ DASHSCOPE_API_KEY 未正确配置"
    echo "请编辑 .env 文件，填入你的 API Key"
    exit 1
fi
echo "✅ API Key 已配置"

# 构建 Docker 镜像
echo ""
echo "4️⃣  构建 Docker 镜像..."
echo "这可能需要几分钟时间..."
if ! docker-compose build; then
    echo "❌ Docker 镜像构建失败"
    exit 1
fi
echo "✅ Docker 镜像构建成功"

# 启动容器
echo ""
echo "5️⃣  启动容器..."
if ! docker-compose up -d; then
    echo "❌ 容器启动失败"
    exit 1
fi
echo "✅ 容器启动成功"

# 等待服务就绪
echo ""
echo "6️⃣  等待服务就绪..."
sleep 5

# 检查容器状态
echo ""
echo "7️⃣  检查容器状态..."
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ 容器未正常运行"
    echo ""
    echo "查看日志："
    docker-compose logs
    exit 1
fi
echo "✅ 容器正常运行"

# 测试 Web 服务
echo ""
echo "8️⃣  测试 Web 服务..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        echo "✅ Web 服务正常"
        break
    fi
    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ Web 服务无响应"
        echo ""
        echo "查看日志："
        docker-compose logs
        exit 1
    fi
    sleep 2
done

# 显示访问信息
echo ""
echo "=================================="
echo "🎉 环境测试完成！"
echo "=================================="
echo ""
echo "📍 访问地址："
echo "   http://localhost:8501"
echo ""
echo "📊 管理命令："
echo "   查看日志:    docker-compose logs -f"
echo "   停止服务:    docker-compose stop"
echo "   重启服务:    docker-compose restart"
echo "   完全清理:    docker-compose down"
echo ""
echo "🎮 现在可以打开浏览器访问游戏界面了！"
echo ""
