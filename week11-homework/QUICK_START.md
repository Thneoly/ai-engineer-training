# 🐺 狼人杀游戏 - 一键启动指南

## 方式 1: Docker（推荐，最简单）

### 前置要求
- 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- 获取阿里云 DashScope API Key

### 启动步骤

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd week11-homework

# 2. 配置 API Key
echo "DASHSCOPE_API_KEY=你的API密钥" > .env

# 3. 一键启动！
docker-compose up -d

# 4. 打开浏览器
# 访问 http://localhost:8501
```

就这么简单！🎉

### 管理命令

```bash
# 查看日志
docker-compose logs -f

# 停止服务
docker-compose stop

# 重启服务
docker-compose restart

# 完全清理
docker-compose down
```

---

## 方式 2: 本地运行（开发者）

### 前置要求
- Python 3.11+
- uv 包管理器

### 启动步骤

```bash
# 1. 安装依赖
uv pip install -e .
uv pip install streamlit

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY

# 3. 启动 Web 界面
streamlit run werewolf/web_ui.py

# 或者运行命令行版本
python -m werewolf.main
```

---

## 方式 3: 在线体验（云部署）

项目已部署到以下平台：

- **Streamlit Cloud**: https://your-app.streamlit.app
- **Hugging Face Spaces**: https://huggingface.co/spaces/...

无需安装，直接使用！

---

## 🎮 使用指南

### Web 界面功能

1. **开始新游戏**
   - 点击左侧"开始新游戏"
   - 配置游戏参数
   - 观看 AI 对战

2. **查看历史对局**
   - 选择"查看历史对局"
   - 浏览往期记录
   - 分析玩家策略

3. **实时追踪**
   - 查看玩家状态
   - 观察讨论过程
   - 统计投票结果

### 命令行版本

```bash
# 基础运行
python -m werewolf.main

# 自定义配置
python -m werewolf.main --rounds 15 --verbose
```

---

## 📊 系统要求

| 项目 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核+ |
| 内存 | 2GB | 4GB+ |
| 磁盘 | 500MB | 2GB+ |
| 网络 | 稳定互联网 | 宽带 |

---

## ❓ 常见问题

### Q1: Docker 容器启动失败？

```bash
# 检查日志
docker-compose logs

# 常见原因：
# 1. 端口 8501 被占用 -> 修改 docker-compose.yml 端口映射
# 2. API Key 未设置 -> 检查 .env 文件
# 3. 内存不足 -> 增加 Docker 内存限制
```

### Q2: 页面加载很慢？

- 第一次启动需要初始化 ChromaDB
- LLM API 调用需要时间
- 建议等待 2-3 分钟

### Q3: 如何更新到最新版本？

```bash
# Docker 方式
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 本地方式
git pull
uv pip install -e . --force-reinstall
```

---

## 🚀 进阶配置

### 自定义端口

编辑 `docker-compose.yml`:
```yaml
ports:
  - "8080:8501"  # 改为你想要的端口
```

### 多实例部署

```bash
# 实例 1
docker-compose -p werewolf-1 up -d

# 实例 2（修改端口）
docker-compose -p werewolf-2 -f docker-compose.yml up -d
```

### 性能优化

在 `.env` 中添加：
```bash
# 使用更快的模型
LLM_MODEL=qwen-turbo

# 减少迭代次数
MAX_ITER=3

# 限制回合数
MAX_ROUNDS=5
```

---

## 🌐 云部署

### Streamlit Cloud（免费）

1. Fork 本项目到 GitHub
2. 访问 https://streamlit.io/cloud
3. 连接 GitHub 仓库
4. 配置 API Key
5. 点击 Deploy

### Hugging Face Spaces

1. 创建新 Space
2. 上传项目文件
3. 添加 `app.py`:
   ```python
   import subprocess
   subprocess.run(["streamlit", "run", "werewolf/web_ui.py"])
   ```
4. 配置 Secrets

### Railway / Render

参考 `docs/DEPLOYMENT.md` 详细教程。

---

## 📞 获取帮助

- **文档**: 查看 `docs/` 目录
- **示例**: 查看 `logs/` 目录的历史对局
- **问题**: 提交 GitHub Issue

---

**享受游戏！🐺🌙**
