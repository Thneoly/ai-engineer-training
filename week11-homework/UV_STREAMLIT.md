# 使用 uv 运行 Streamlit Web 界面

## ✅ 成功启动方法

### 方法 1: 使用虚拟环境（推荐）

```bash
# 激活 uv 创建的虚拟环境
source .venv/bin/activate

# 运行 Streamlit
streamlit run werewolf/web_ui.py
```

### 方法 2: 使用启动脚本

```bash
# 直接运行启动脚本
./start-web.sh
```

### 方法 3: 一行命令

```bash
source .venv/bin/activate && streamlit run werewolf/web_ui.py
```

## 📍 访问地址

启动成功后，在浏览器中访问：
- **本地**: http://localhost:8501
- **网络**: http://198.18.0.1:8501

## 🔧 常见问题

### Q1: ModuleNotFoundError: No module named 'crewai'

**原因**: 依赖未安装或未激活虚拟环境

**解决方案**:
```bash
# 同步所有依赖
uv sync

# 激活虚拟环境
source .venv/bin/activate
```

### Q2: ModuleNotFoundError: No module named 'werewolf'

**原因**: Python 路径问题

**解决方案**: 已在 `web_ui.py` 中自动修复，无需手动处理

### Q3: streamlit: command not found

**原因**: streamlit 未安装

**解决方案**:
```bash
uv pip install streamlit
```

## 🛠️ uv 命令速查

```bash
# 同步依赖
uv sync

# 安装单个包
uv pip install <package>

# 列出已安装的包
uv pip list

# 激活虚拟环境
source .venv/bin/activate

# 退出虚拟环境
deactivate
```

## 🎯 完整启动流程

```bash
# 1. 进入项目目录
cd /home/cc/Desktop/code/AIPro/ai-engineer-training/week11-homework

# 2. 确保依赖已安装
uv sync

# 3. 激活虚拟环境
source .venv/bin/activate

# 4. 启动 Web 界面
streamlit run werewolf/web_ui.py

# 5. 在浏览器中访问
# http://localhost:8501
```

## 📊 验证环境

```bash
# 检查 Python 版本
python --version

# 检查关键包
python -c "import crewai; import streamlit; print('✅ 环境正常')"

# 列出所有依赖
uv pip list | grep -E "(crewai|streamlit|chromadb)"
```

## ⏹️ 停止服务

在终端中按 `Ctrl + C` 停止 Streamlit 服务

---

**当前状态**: ✅ Streamlit 正在运行在 http://localhost:8501
