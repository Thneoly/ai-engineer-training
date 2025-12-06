# WASM 技术栈分析与方案选择

## 🎯 目标需求

为狼人杀多智能体游戏添加图形界面，要求：
- ✅ 用户本地简单配置
- ✅ 一键启动运行
- ✅ 展示游戏过程
- ✅ 支持回放对局

---

## ❌ 为什么不推荐纯 WASM？

### 1. **架构不兼容**

```
┌─────────────────────────────────┐
│  浏览器 (WASM 环境)              │
│  ┌──────────────────────────┐   │
│  │ Python (Pyodide)         │   │
│  │   ↓                      │   │
│  │ CrewAI Framework         │   │ ❌ 依赖后端 API
│  │   ↓                      │   │
│  │ 需要调用 DashScope API   │   │ ❌ CORS 限制
│  │   ↓                      │   │
│  │ ❌ 无法访问外部 API       │   │ ❌ API Key 安全
│  └──────────────────────────┘   │
└─────────────────────────────────┘
```

**核心问题：**
- 🚫 浏览器安全策略禁止直接调用第三方 API
- 🚫 API Key 会暴露在客户端代码中
- 🚫 CORS 限制无法绕过

### 2. **依赖包不兼容**

| 包名 | 是否支持 WASM | 问题 |
|------|-------------|------|
| crewai | ❌ | 依赖复杂的 asyncio 和网络库 |
| chromadb | ❌ | 依赖 C 扩展（sqlite、hnswlib） |
| dashscope | ❌ | 依赖 requests、urllib3 |
| openai | ⚠️ | 部分功能可用，但受 CORS 限制 |

### 3. **性能问题**

```python
# WASM 环境性能对比
操作             原生 Python    Pyodide (WASM)    性能比
─────────────────────────────────────────────────────────
启动时间          < 1s          10-30s           30x 慢
向量计算          快             慢               10x 慢
文件 I/O          快             很慢             20x 慢
网络请求          正常           受限             不可用
```

### 4. **包大小问题**

```
Pyodide 基础包:     ~30 MB
+ NumPy:            ~15 MB
+ Pandas:           ~10 MB
+ scikit-learn:     ~25 MB
+ 其他依赖:         ~20 MB
─────────────────────────────
总计:               ~100 MB
```

用户首次访问需要下载 100MB+，体验很差。

---

## ✅ 推荐方案对比

### 方案 1: **Docker + Streamlit**（推荐）⭐⭐⭐⭐⭐

#### 优点
- ✅ **一键启动**: `docker-compose up`
- ✅ **环境隔离**: 无依赖冲突
- ✅ **跨平台**: Windows/Mac/Linux
- ✅ **安全**: API Key 在服务端
- ✅ **性能**: 原生 Python 性能
- ✅ **易部署**: 可部署到任何云平台

#### 用户操作流程
```bash
# 1. 安装 Docker Desktop（一次性）
# 2. 配置 API Key
echo "DASHSCOPE_API_KEY=xxx" > .env

# 3. 启动
docker-compose up -d

# 4. 访问
http://localhost:8501
```

#### 架构图
```
┌────────────────────────────────────────┐
│  用户浏览器                             │
│  http://localhost:8501                │
└────────────────┬───────────────────────┘
                 │ HTTP
┌────────────────▼───────────────────────┐
│  Docker 容器                            │
│  ┌──────────────────────────────────┐  │
│  │ Streamlit Web Server             │  │
│  │   ↓                              │  │
│  │ Python + CrewAI                  │  │
│  │   ↓                              │  │
│  │ ChromaDB (本地)                  │  │
│  └───────────────┬──────────────────┘  │
└──────────────────┼─────────────────────┘
                   │ HTTPS
        ┌──────────▼──────────┐
        │ DashScope API (云端) │
        └─────────────────────┘
```

---

### 方案 2: **WebAssembly 混合架构**（部分可行）⭐⭐⭐

#### 适用场景
- 前端展示和交互
- 后端处理 AI 逻辑

#### 架构设计

```
┌─────────────────────────────────────────┐
│  浏览器（WASM 前端）                     │
│  ┌───────────────────────────────────┐  │
│  │ React/Vue + Rust (WASM)          │  │
│  │  - 游戏界面渲染                  │  │
│  │  - 动画效果                      │  │
│  │  - 用户交互                      │  │
│  └───────────────┬───────────────────┘  │
└──────────────────┼──────────────────────┘
                   │ WebSocket/HTTP
┌──────────────────▼──────────────────────┐
│  后端服务（Python）                      │
│  ┌───────────────────────────────────┐  │
│  │ FastAPI Server                   │  │
│  │   ↓                              │  │
│  │ CrewAI + ChromaDB               │  │
│  │   ↓                              │  │
│  │ DashScope API                   │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

#### 实现示例

**前端（Rust + WASM）**
```rust
// src/game_ui.rs
use yew::prelude::*;
use gloo_net::http::Request;

#[function_component(GameBoard)]
pub fn game_board() -> Html {
    let game_state = use_state(|| None);
    
    let start_game = {
        let game_state = game_state.clone();
        Callback::from(move |_| {
            wasm_bindgen_futures::spawn_local(async move {
                // 调用后端 API
                let response = Request::post("http://localhost:8000/api/game/start")
                    .send()
                    .await
                    .unwrap();
                
                let data = response.json().await.unwrap();
                game_state.set(Some(data));
            });
        })
    };
    
    html! {
        <div class="game-container">
            <button onclick={start_game}>{"Start Game"}</button>
            // 游戏界面
        </div>
    }
}
```

**后端（FastAPI）**
```python
# backend/api.py
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from werewolf.game import WerewolfGame

app = FastAPI()

# 允许 WASM 前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

games = {}

@app.post("/api/game/start")
async def start_game():
    game_id = str(uuid.uuid4())
    games[game_id] = WerewolfGame()
    
    # 在后台运行游戏
    asyncio.create_task(run_game(game_id))
    
    return {"game_id": game_id}

@app.websocket("/ws/game/{game_id}")
async def game_websocket(websocket: WebSocket, game_id: str):
    await websocket.accept()
    
    game = games.get(game_id)
    
    # 实时推送游戏状态
    while True:
        state = game.get_current_state()
        await websocket.send_json(state)
        await asyncio.sleep(1)
```

#### 优点
- ✅ 前端响应快速（WASM 渲染）
- ✅ 后端功能完整（Python AI）
- ✅ 实时通信（WebSocket）

#### 缺点
- ❌ 开发复杂度高
- ❌ 需要学习 Rust/WASM
- ❌ 仍需要运行后端服务

---

### 方案 3: **Electron + Python**（桌面应用）⭐⭐⭐⭐

#### 适用场景
- 需要桌面应用
- 不依赖浏览器

#### 架构
```
┌─────────────────────────────────┐
│  Electron 窗口                  │
│  ┌───────────────────────────┐  │
│  │ HTML/CSS/JavaScript       │  │
│  │  (渲染进程)               │  │
│  └───────────┬───────────────┘  │
│              │ IPC              │
│  ┌───────────▼───────────────┐  │
│  │ Node.js (主进程)          │  │
│  │   ↓                       │  │
│  │ 启动 Python 子进程        │  │
│  │   ↓                       │  │
│  │ Python + CrewAI          │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

#### 打包分发
```bash
# 使用 PyInstaller + Electron-builder
npm run build    # 打包 Electron
pyinstaller      # 打包 Python

# 最终产物
werewolf-game-win.exe    # Windows
werewolf-game-mac.dmg    # macOS
werewolf-game-linux.AppImage  # Linux
```

#### 优点
- ✅ 原生应用体验
- ✅ 离线可用
- ✅ 性能好

#### 缺点
- ❌ 包体积大（~200MB）
- ❌ 打包复杂
- ❌ 更新不便

---

### 方案 4: **纯静态页面 + API 代理**（可考虑）⭐⭐⭐

#### 适用场景
- 只需要展示历史对局
- 不需要运行新游戏

#### 架构
```
┌─────────────────────────────────┐
│  GitHub Pages / Netlify         │
│  ┌───────────────────────────┐  │
│  │ 静态 HTML/CSS/JS          │  │
│  │   ↓                       │  │
│  │ 加载 logs/*.json          │  │
│  │   ↓                       │  │
│  │ 纯前端渲染游戏记录        │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

#### 实现
```html
<!DOCTYPE html>
<html>
<head>
    <title>狼人杀对局回放</title>
    <script src="https://cdn.jsdelivr.net/npm/vue@3"></script>
</head>
<body>
    <div id="app">
        <h1>🐺 狼人杀对局回放</h1>
        <select v-model="selectedLog" @change="loadLog">
            <option v-for="log in logs" :value="log">{{ log }}</option>
        </select>
        
        <div v-if="gameData">
            <h2>第 {{ currentRound }} 回合</h2>
            <div v-for="message in messages" class="message">
                {{ message }}
            </div>
        </div>
    </div>
    
    <script>
        const { createApp } = Vue;
        
        createApp({
            data() {
                return {
                    logs: [],
                    selectedLog: null,
                    gameData: null,
                    currentRound: 1
                };
            },
            mounted() {
                // 加载日志列表
                fetch('logs/index.json')
                    .then(r => r.json())
                    .then(data => this.logs = data);
            },
            methods: {
                loadLog() {
                    fetch(`logs/${this.selectedLog}`)
                        .then(r => r.json())
                        .then(data => this.gameData = data);
                }
            }
        }).mount('#app');
    </script>
</body>
</html>
```

#### 优点
- ✅ 无需服务器
- ✅ 免费托管
- ✅ 极简部署

#### 缺点
- ❌ 只能回放，不能运行新游戏
- ❌ 功能受限

---

## 📊 方案对比总结

| 方案 | 易用性 | 功能完整性 | 开发成本 | 运行成本 | 推荐度 |
|------|--------|-----------|---------|---------|--------|
| Docker + Streamlit | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 免费 | ⭐⭐⭐⭐⭐ |
| WASM 混合架构 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | 免费 | ⭐⭐⭐ |
| Electron 桌面 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 免费 | ⭐⭐⭐⭐ |
| 纯静态页面 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | 免费 | ⭐⭐⭐ |
| 纯 WASM | ❌ | ❌ | ❌ | 免费 | ❌ |

---

## 🎯 最终建议

### 对于你的项目，强烈推荐：**Docker + Streamlit**

**理由：**

1. **用户体验最佳**
   ```bash
   # 用户只需要：
   docker-compose up -d
   # 然后访问 localhost:8501
   ```

2. **开发最简单**
   - 已经创建了 `werewolf/web_ui.py`
   - 已经创建了 `Dockerfile` 和 `docker-compose.yml`
   - 只需安装 Docker Desktop

3. **功能最完整**
   - ✅ 开始新游戏
   - ✅ 查看历史对局
   - ✅ 实时追踪
   - ✅ 数据分析

4. **部署灵活**
   - 本地运行：Docker
   - 云端部署：Streamlit Cloud / Railway / Render
   - 都是免费的！

### 如果需要更酷炫的界面

可以考虑 **方案 2（WASM 混合架构）**：
- 前端用 Rust + Yew 做炫酷动画
- 后端用 Python 处理 AI 逻辑
- 但开发成本会高 3-5 倍

---

## 🚀 立即开始

运行以下命令启动项目：

```bash
# 安装 Streamlit
uv pip install streamlit

# 启动 Web 界面
streamlit run werewolf/web_ui.py

# 或使用 Docker
docker-compose up -d
```

访问 http://localhost:8501 查看效果！

---

## 📚 参考资源

- [Streamlit 文档](https://docs.streamlit.io/)
- [Docker 文档](https://docs.docker.com/)
- [PyScript (Python in Browser)](https://pyscript.net/)
- [Pyodide (Python + WASM)](https://pyodide.org/)
- [Yew (Rust + WASM)](https://yew.rs/)

---

**结论：不要用纯 WASM，用 Docker + Streamlit！** 🎉
