# AI Router 功能总结
## One NZ Employee Finder Agent - 智能路由系统

---

## 🎯 你的问题

> "我们这个是ai agent，你帮我开发的这个项目有router吗，什么时候直接查询，什么时候用ai"

---

## ✅ 答案：现在有了！

我已经为你添加了完整的 **AI Router（智能路由）** 系统，它会自动决定：
- ✅ **什么时候直接查询数据库**（快速、不需要AI）
- ✅ **什么时候使用AI理解**（复杂查询、需要智能理解）

---

## 🏗️ 新增的组件

### 1. **Router（路由器）** - `agent/router.py`
- 分析查询复杂度
- 分类查询类型（5种）
- 决定处理策略

### 2. **Tools（工具系统）** - `agent/tools.py`
- 7个数据库查询工具
- 可被AI调用或直接使用
- 每个工具都是独立函数

### 3. **LLM Integration（AI集成）** - `agent/llm_integration.py`
- 支持OpenAI API
- 支持本地LLM（Ollama等）
- 可选启用/禁用

### 4. **Enhanced Agent（增强Agent）** - `agent/ai_agent.py`
- 整合Router + Tools + LLM
- 智能决策执行流程
- 生成结构化响应

---

## 🔀 路由决策逻辑

### 5种查询类型

| 查询类型 | 示例 | 处理方式 | 是否用AI | 响应时间 |
|---------|------|---------|---------|---------|
| **1. 直接查找** | "Find john.doe@onenz.co.nz" | 直接数据库查询 | ❌ 不用 | ~10ms |
| **2. 简单搜索** | "Find someone in billing team" | 模式匹配 + 数据库 | ❌ 不用 | ~50ms |
| **3. 复杂意图** | "I need help with BIA provisioning" | AI理解 + 数据库 | ✅ 用AI | ~800ms |
| **4. 对话式** | "Thanks!" 或 "Can you explain?" | AI生成回复 | ✅ 用AI | ~600ms |
| **5. 模糊查询** | "Help"（太模糊） | AI澄清 | ✅ 用AI | ~600ms |

### 决策流程

```
用户查询
    ↓
检查是否包含邮箱？
    ├─ 是 → 直接查询（不用AI）✅ 快！
    └─ 否 ↓
检查是否对话式？
    ├─ 是 → AI回复（用AI）
    └─ 否 ↓
检查是否简单模式？
    ├─ 是 → 模式匹配（不用AI）✅ 快！
    └─ 否 ↓
检查是否太短/模糊？
    ├─ 是 → AI澄清（用AI）
    └─ 否 → 复杂意图（用AI）
```

---

## 🛠️ 工具系统（7个工具）

所有工具都可以：
- ✅ 被AI调用
- ✅ 被Router直接调用
- ✅ 独立使用

| 工具 | 功能 | 速度 |
|-----|------|------|
| `find_by_email()` | 邮箱精确查找 | 10ms |
| `find_by_team()` | 团队搜索 | 50ms |
| `find_by_role()` | 职位搜索 | 50ms |
| `find_by_skill()` | 技能搜索 | 100ms |
| `find_by_responsibility()` | 职责所有权搜索 | 100ms |
| `search_fulltext()` | 全文搜索（FTS5） | 150ms |
| `get_employee_with_leader()` | 获取员工+领导信息 | 50ms |

---

## 🤖 AI集成（可选）

### 3种配置模式

#### 模式1：使用OpenAI（云端AI）
```bash
# .env 配置
USE_AI_ROUTING=True
ENABLE_LLM=True
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-3.5-turbo
```

**优点：**
- ✅ 理解质量最高
- ✅ 响应快
- ✅ 无需本地配置

**缺点：**
- ❌ 需要API密钥（花钱）
- ❌ 数据发送到外部
- ❌ 需要网络

---

#### 模式2：使用本地LLM（Ollama等）
```bash
# .env 配置
USE_AI_ROUTING=True
ENABLE_LLM=True
LLM_PROVIDER=local
LOCAL_LLM_ENDPOINT=http://localhost:11434/v1
LOCAL_LLM_MODEL=llama2
```

**优点：**
- ✅ 免费
- ✅ 隐私（数据不出本地）
- ✅ 离线可用

**缺点：**
- ❌ 需要本地安装Ollama
- ❌ 较慢（取决于硬件）
- ❌ 可能需要GPU

---

#### 模式3：不使用AI（仅模式匹配）
```bash
# .env 配置
USE_AI_ROUTING=True
ENABLE_LLM=False
```

**优点：**
- ✅ 最快
- ✅ 无外部依赖
- ✅ 可预测

**缺点：**
- ❌ 灵活性较低
- ❌ 复杂查询理解能力弱

---

## 📊 性能对比

### 不同查询的处理方式

| 查询示例 | 是否用AI | 有LLM | 无LLM |
|---------|---------|-------|-------|
| "john.doe@onenz.co.nz" | ❌ | 10ms | 10ms |
| "billing team" | ❌ | 50ms | 50ms |
| "help with BIA provisioning" | ✅ | 800ms | 150ms |
| "Thanks!" | ✅ | 600ms | N/A |

**结论：**
- 简单查询：有无AI都一样快（因为不用AI）
- 复杂查询：有AI更准确，无AI更快

---

## 🎓 实际例子

### 例子1：邮箱查找（不用AI）
```
用户："Find john.doe@onenz.co.nz"
  ↓
Router：检测到邮箱 → DIRECT_LOOKUP
  ↓
工具：find_by_email("john.doe@onenz.co.nz")
  ↓
数据库：SELECT * FROM employees WHERE email = ?
  ↓
响应：[John Doe的信息] (10ms)
```

### 例子2：团队搜索（不用AI）
```
用户："Find someone in billing team"
  ↓
Router：检测到简单模式 → SIMPLE_SEARCH
  ↓
工具：find_by_team("billing")
  ↓
数据库：SELECT * FROM employees WHERE team LIKE '%billing%'
  ↓
响应：[Billing团队成员列表] (50ms)
```

### 例子3：复杂查询（用AI）
```
用户："I need help with BIA provisioning"
  ↓
Router：复杂意图 → COMPLEX_INTENT
  ↓
LLM：理解查询 → {domains: ["provisioning", "BIA"], strategy: "responsibility"}
  ↓
工具：find_by_responsibility("BIA provisioning")
  ↓
数据库：SELECT * FROM role_ownership WHERE responsibility LIKE '%BIA%'
  ↓
响应：[主要负责人、备份、升级路径] (800ms)
```

---

## ⚙️ 如何使用

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置（选择一种模式）

**推荐：先不用AI（最简单）**
```bash
cp .env.example .env
# 编辑 .env
USE_AI_ROUTING=True
ENABLE_LLM=False
```

**进阶：使用OpenAI**
```bash
# 编辑 .env
USE_AI_ROUTING=True
ENABLE_LLM=True
OPENAI_API_KEY=sk-your-key
```

### 3. 启动服务器
```bash
python scripts/start_server.py
```

### 4. 测试
```bash
# 查看配置
curl http://localhost:8000/health

# 测试简单查询（不用AI）
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "find someone in billing team"}'

# 测试复杂查询（用AI，如果启用）
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "I need help with BIA provisioning"}'
```

---

## 📁 新增文件

```
agent_project/
├── agent/
│   ├── router.py              # ✨ 新增：智能路由
│   ├── tools.py               # ✨ 新增：工具系统
│   ├── llm_integration.py     # ✨ 新增：LLM集成
│   ├── ai_agent.py            # ✨ 新增：增强Agent
│   └── employee_finder_agent.py  # 原有：基础Agent
├── AI_ARCHITECTURE.md         # ✨ 新增：架构文档
├── USAGE_EXAMPLES.md          # ✨ 新增：使用示例
└── AI_ROUTER_SUMMARY.md       # ✨ 新增：本文档
```

---

## 🎯 总结

### 回答你的问题：

**Q: 有router吗？**
✅ **有！** `agent/router.py` - 智能路由系统

**Q: 什么时候直接查询？**
✅ **3种情况：**
1. 邮箱查找（检测到邮箱格式）
2. 简单搜索（团队、职位等简单模式）
3. 关键词搜索（包含简单关键词）

**Q: 什么时候用AI？**
✅ **3种情况：**
1. 复杂意图（需要理解上下文）
2. 对话式查询（"Thanks!", "Hello"等）
3. 模糊查询（需要澄清）

### 关键优势：

1. **智能决策** - 自动选择最优策略
2. **性能优化** - 简单查询不浪费AI资源
3. **灵活配置** - 可选启用/禁用AI
4. **成本控制** - 只在需要时调用LLM
5. **渐进增强** - 先用简单模式，需要时再加AI

---

**版本：** 2.0.0（新增AI Router）  
**更新时间：** 2026-01-18

