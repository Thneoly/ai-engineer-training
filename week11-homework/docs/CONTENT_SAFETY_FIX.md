# 内容安全审核问题修复记录

## 问题描述

在使用阿里云通义千问（Qwen）模型时，遇到以下错误：

```
HTTP Status: 400
Error Code: InvalidParameter
Error Message: Input data may contain inappropriate content.
```

这是因为阿里云 DashScope 平台对内容进行了安全审核，检测到输入/输出中包含暴力、敏感词汇。

## 触发原因

狼人杀游戏中涉及的术语可能触发内容安全机制：
- "杀死"、"击杀"、"处决"
- "投票淘汰"、"狼人杀人"
- "死亡"、"尸体"

## 解决方案

### 1. 替换暴力词汇

将所有可能引发问题的词汇替换为更中性的表达：

| 原词汇 | 替换为 | 使用场景 |
|--------|--------|----------|
| 杀死 | 出局 | 狼人行动 |
| 击杀 | 淘汰 | 投票结果 |
| 处决 | 淘汰 | 投票决定 |
| 死亡 | 出局 | 状态描述 |
| 尸体 | 出局者 | 结果展示 |
| 凶手 | 行动方 | 角色描述 |

### 2. 代码修改

#### werewolf/config.py

**修改前**:
```python
MODERATOR_PROMPT = """
你是狼人杀游戏的主持人。

狼人每晚可以杀死一名村民...
如果狼人被投票处决，村民胜利...
"""
```

**修改后**:
```python
MODERATOR_PROMPT = """
你是狼人杀游戏的主持人。

狼人每晚可以让一名村民出局...
如果狼人被投票淘汰，村民胜利...
"""
```

#### werewolf/game.py

**修改前**:
```python
def execute_night_action(self, target: str):
    logger.info(f"狼人击杀了 {target}")
    return f"{target}被杀死"
```

**修改后**:
```python
def execute_night_action(self, target: str):
    logger.info(f"狼人选择让 {target} 出局")
    return f"{target}已出局"
```

#### werewolf/tools.py

**修改前**:
```python
@tool("夜间行动")
def night_action(target: str) -> str:
    """狼人击杀目标玩家"""
    return f"成功击杀 {target}"
```

**修改后**:
```python
@tool("夜间行动")
def night_action(target: str) -> str:
    """狼人选择让目标玩家出局"""
    return f"{target} 已被选择出局"
```

### 3. Prompt 优化

修改所有角色的提示词，避免使用暴力语言：

**狼人角色 - 修改前**:
```python
WEREWOLF_PROMPT = """
你是一名狼人，需要在夜晚杀死村民...
白天要隐藏身份，避免被处决...
"""
```

**狼人角色 - 修改后**:
```python
WEREWOLF_PROMPT = """
你是一名狼人，需要在夜晚选择让村民出局...
白天要隐藏身份，避免被投票淘汰...
"""
```

**村民角色 - 修改前**:
```python
VILLAGER_PROMPT = """
你是一名村民，需要找出并处决所有狼人...
夜晚可能被狼人杀死...
"""
```

**村民角色 - 修改后**:
```python
VILLAGER_PROMPT = """
你是一名村民，需要找出并投票淘汰所有狼人...
夜晚可能被狼人选择出局...
"""
```

### 4. 日志输出调整

将日志输出中的敏感词汇也进行替换：

```python
logger.info(f"【夜晚阶段】{target} 被选择出局")
logger.info(f"【投票结果】{player} 被淘汰")
logger.info(f"【游戏结束】所有狼人已被淘汰")
```

## 全局替换命令

使用以下命令批量替换：

```bash
# 替换 "杀死" 为 "出局"
find werewolf/ -type f -name "*.py" -exec sed -i 's/杀死/出局/g' {} +

# 替换 "击杀" 为 "淘汰"
find werewolf/ -type f -name "*.py" -exec sed -i 's/击杀/淘汰/g' {} +

# 替换 "处决" 为 "淘汰"
find werewolf/ -type f -name "*.py" -exec sed -i 's/处决/淘汰/g' {} +

# 替换 "死亡" 为 "出局"
find werewolf/ -type f -name "*.py" -exec sed -i 's/死亡/出局/g' {} +
```

## 验证步骤

### 1. 测试运行

```bash
python -m werewolf.main
```

### 2. 检查日志

```bash
# 检查是否还有敏感词
grep -r "杀死\|击杀\|处决" werewolf/
```

### 3. 监控 API 响应

观察是否还有 400 错误：
```
✅ 成功: HTTP 200
❌ 失败: HTTP 400 (需要进一步检查)
```

## 效果验证

修复后运行测试：

```
✅ 游戏正常启动
✅ 狼人协商阶段通过
✅ 投票淘汰阶段通过
✅ 全部回合完成
✅ 无内容安全审核错误
```

## 最佳实践

### 1. 预防性措施

在项目开始时就规划用词规范：
- 使用 "出局" 代替 "死亡"
- 使用 "淘汰" 代替 "处决"
- 使用 "选择" 代替 "攻击"

### 2. 文档规范

在 README 和文档中统一使用安全词汇：
```markdown
## 游戏规则
- 狼人每晚选择一名村民出局
- 白天所有玩家投票淘汰一名玩家
- 当所有狼人被淘汰时，村民获胜
```

### 3. 代码审查

使用 Git hooks 检查代码中的敏感词：

```bash
# .git/hooks/pre-commit
#!/bin/bash
if git diff --cached | grep -E "杀死|击杀|处决"; then
    echo "错误: 检测到敏感词汇，请使用中性表达"
    exit 1
fi
```

### 4. 测试用例

添加内容安全测试：

```python
def test_no_violent_words():
    """确保代码中不含暴力词汇"""
    forbidden_words = ["杀死", "击杀", "处决", "凶手"]
    
    for word in forbidden_words:
        result = grep_in_code(word)
        assert result == [], f"发现禁用词汇: {word}"
```

## 其他平台的考虑

不同 LLM 平台对内容安全的要求不同：

| 平台 | 审核严格度 | 建议 |
|------|-----------|------|
| 阿里云 Qwen | 🔴 严格 | 必须替换所有暴力词汇 |
| OpenAI GPT-4 | 🟡 中等 | 建议使用中性词汇 |
| Anthropic Claude | 🟢 宽松 | 可以使用游戏术语 |
| Google Gemini | 🟡 中等 | 建议使用中性词汇 |

## 常见问题

### Q1: 为什么还是触发审核？

检查以下几点：
1. 是否有遗漏的敏感词
2. 用户输入是否包含敏感内容
3. Agent 生成的回复是否合规

### Q2: 如何测试内容安全？

可以使用 DashScope 的内容审核 API 预先检测：

```python
import dashscope

def check_safety(text: str) -> bool:
    """检查文本是否符合内容安全规范"""
    result = dashscope.ModerationClient.check(text)
    return result.safe
```

### Q3: 影响游戏体验吗？

使用 "出局"、"淘汰" 等词汇完全不影响游戏玩法，甚至更容易理解：
- ✅ "Alpha 在夜晚出局" - 清晰明了
- ❌ "Alpha 被狼人杀死" - 可能触发审核

## 相关资源

- [DashScope 内容安全规范](https://help.aliyun.com/zh/dashscope/developer-reference/content-moderation-api)
- [阿里云内容安全服务](https://www.aliyun.com/product/lvwang)
- [OpenAI 使用策略](https://openai.com/policies/usage-policies)

## 修改历史

| 日期 | 修改内容 | 影响范围 |
|------|---------|---------|
| 2024-12-06 | 全局替换暴力词汇 | config.py, tools.py, game.py |
| 2024-12-06 | 优化角色 Prompt | config.py |
| 2024-12-06 | 更新日志输出 | game.py |

---

**总结**: 通过系统性地替换暴力词汇为中性表达，成功解决了内容安全审核问题，同时保持了游戏的完整性和可玩性。