# OpenWebUI 集成指南 🔌

完整的OpenWebUI集成教程，让你的One NZ Employee Finder Agent在OpenWebUI中使用。

---

## 📋 前提条件

### 1. 确保Agent服务器正在运行

```bash
# 启动服务器
cd /path/to/agent_project
python scripts/start_server.py

# 或使用uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 2. 验证服务器状态

```bash
# 检查健康状态
curl http://localhost:8000/health

# 应该返回类似：
# {"status":"healthy","database":"connected","ai_routing_enabled":true,...}
```

### 3. 确保有测试数据

```bash
# 如果还没有数据，运行：
python scripts/create_mock_data.py
```

### 4. OpenWebUI已安装

如果还没安装OpenWebUI：

```bash
# 使用Docker安装（推荐）
docker run -d -p 3000:8080 \
  --name openwebui \
  ghcr.io/open-webui/open-webui:main

# 或使用pip安装
pip install open-webui
open-webui serve
```

访问：http://localhost:3000

---

## 🚀 方法一：作为 OpenAI-Compatible API（推荐）

我们的Agent实现了OpenAI兼容的 `/v1/chat/completions` 端点，可以直接作为自定义模型使用。

### 步骤 1: 打开OpenWebUI设置

1. 访问 http://localhost:3000
2. 登录OpenWebUI
3. 点击左上角的 **头像** 或 **设置图标** ⚙️
4. 选择 **Admin Panel（管理面板）** 或 **Settings（设置）**

### 步骤 2: 添加自定义OpenAI API

在Admin Panel中：

1. 找到 **Connections** 或 **External Connections** 部分
2. 找到 **OpenAI API** 配置区域
3. 点击 **Add** 或 **+** 添加新连接

### 步骤 3: 填写配置信息

```
Name: One NZ Employee Finder
Base URL: http://localhost:8000/v1
API Key: sk-dummy-key-not-required
```

**重要说明：**
- **Base URL**: 必须是 `http://localhost:8000/v1`（注意 `/v1` 后缀）
- **API Key**: 我们的API不验证Key，但OpenWebUI要求填写，随便填一个即可
- **如果在不同机器上**:
  - 将 `localhost` 改为Agent服务器的IP地址
  - 例如：`http://192.168.1.100:8000/v1`
  - 如果用Docker，使用 `http://host.docker.internal:8000/v1`

### 步骤 4: 保存并刷新模型列表

1. 点击 **Save** 保存配置
2. 返回聊天界面
3. 点击顶部的 **模型选择器**（通常显示当前模型名）
4. 在下拉列表中找到 `one-nz-employee-finder`
5. 选择这个模型

### 步骤 5: 开始对话！

现在你可以直接在OpenWebUI中使用Agent了！

---

## 🧪 测试查询

在OpenWebUI中尝试以下查询：

### 1. 直接查找（快速，不用AI）
```
Find john.smith@onenz.co.nz
```
**预期：** ~10ms响应，返回John Smith的信息

### 2. 简单搜索（模式匹配）
```
Who is in the billing team?
```
**预期：** ~50ms响应，返回Billing Operations团队成员

### 3. 复杂查询（使用AI理解，如果启用）
```
I need help with BIA provisioning for a new enterprise customer
```
**预期：** 返回Emma Wilson（Primary Owner）和David Brown（Backup）

### 4. 职责查询
```
Who handles network security?
```
**预期：** 返回Sarah Johnson（Network Security Specialist）

### 5. 对话式
```
Thanks! Can you also tell me who their manager is?
```
**预期：** AI理解上下文，返回相关人员的经理信息

---

## ⚙️ 配置选项

### 选项 A: 不使用LLM（默认，最快）

```bash
# .env
USE_AI_ROUTING=True
ENABLE_LLM=False
```

**特点：**
- ✅ 速度最快（10-100ms）
- ✅ 无需配置LLM
- ✅ 适合简单查询
- ❌ 复杂查询理解能力有限

### 选项 B: 使用OpenAI（最智能）

```bash
# .env
USE_AI_ROUTING=True
ENABLE_LLM=True
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_MODEL=gpt-3.5-turbo
```

**特点：**
- ✅ 理解复杂查询
- ✅ 自然对话能力
- ✅ 上下文理解
- ❌ 需要API费用
- ❌ 稍慢（~800ms）

### 选项 C: 使用本地LLM（隐私优先）

```bash
# .env
USE_AI_ROUTING=True
ENABLE_LLM=True
LLM_PROVIDER=local
LOCAL_LLM_ENDPOINT=http://localhost:11434/v1
LOCAL_LLM_MODEL=llama2
```

**前提：** 需要先安装Ollama
```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 下载模型
ollama pull llama2

# 启动 Ollama（默认在11434端口）
ollama serve
```

**特点：**
- ✅ 数据不出本地
- ✅ 免费
- ✅ 离线可用
- ❌ 需要本地GPU/CPU资源
- ❌ 较慢（1-3秒）

---

## 🔍 验证集成

### 1. 检查服务器状态

```bash
curl http://localhost:8000/health
```

**预期响应：**
```json
{
  "status": "healthy",
  "database": "connected",
  "total_employees": 13,
  "total_teams": 10,
  "ai_routing_enabled": true,
  "llm_enabled": false,
  "llm_provider": "openai",
  "agent_type": "Enhanced AI Agent"
}
```

### 2. 测试OpenAI兼容端点

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "one-nz-employee-finder",
    "messages": [
      {"role": "user", "content": "I need help with BIA provisioning"}
    ]
  }'
```

**预期响应：**
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "one-nz-employee-finder",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "👥 Recommended Contacts:\n\n1. Emma Wilson (Primary Owner)..."
      },
      "finish_reason": "stop"
    }
  ]
}
```

---

## 🎨 在 OpenWebUI 中的使用体验

### 对话示例

**用户：** "I need help with BIA provisioning"

**Agent：** 
```
👥 Recommended Contacts:

1. Emma Wilson (Primary Owner)
   📧 emma.wilson@onenz.co.nz
   💼 BIA Provisioning Lead
   👥 Team: Provisioning Services
   🎯 Match: 90% - Primary owner of: BIA provisioning
   ⬆️ Escalation: Emma Wilson (emma.wilson@onenz.co.nz)

2. David Brown (Backup)
   📧 david.brown@onenz.co.nz
   💼 Provisioning Specialist
   👥 Team: Provisioning Services
   🎯 Match: 60% - Backup for: BIA provisioning
```

**用户：** "What about network security?"

**Agent：**
```
👥 Recommended Contacts:

1. Sarah Johnson (Primary Owner)
   📧 sarah.johnson@onenz.co.nz
   💼 Network Security Specialist
   👥 Team: Network Infrastructure
   🎯 Match: 90% - Primary owner of: network security
   ⬆️ Escalation: John Smith (john.smith@onenz.co.nz)
```

---

## 🐛 故障排除

### 问题 1: OpenWebUI 无法连接

**检查：**
```bash
# 确认服务器正在运行
curl http://localhost:8000/health

# 检查端口是否被占用
lsof -i :8000
```

**解决：**
- 确保服务器已启动：`python scripts/start_server.py`
- 检查防火墙设置
- 如果在不同机器上，确保网络可达

### 问题 2: 返回空结果

**检查：**
```bash
# 确认数据库有数据
python scripts/create_mock_data.py
```

### 问题 3: LLM 不工作

**检查：**
```bash
# 查看 .env 配置
cat .env | grep LLM

# 如果使用 OpenAI，测试 API Key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 如果使用本地 LLM，测试 Ollama
curl http://localhost:11434/api/tags
```

---

## 📊 性能优化建议

### 1. 对于大多数查询（推荐）
```bash
USE_AI_ROUTING=True
ENABLE_LLM=False
```
- 38.5%的查询直接查数据库（10-50ms）
- 其余使用模式匹配（50-150ms）

### 2. 对于复杂业务场景
```bash
USE_AI_ROUTING=True
ENABLE_LLM=True
LLM_PROVIDER=openai
```
- 简单查询仍然快速（10-50ms）
- 复杂查询使用AI理解（~800ms）

---

## 🎯 下一步

1. ✅ 在OpenWebUI中测试基本查询
2. ✅ 根据需要调整AI配置
3. ✅ 导入真实员工数据（替换Mock数据）
4. ✅ 收集用户反馈
5. ✅ 监控使用情况和性能

---

**需要帮助？** 查看其他文档：
- [AI_ROUTER_SUMMARY.md](AI_ROUTER_SUMMARY.md) - Router工作原理
- [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) - 更多查询示例
- [README.md](README.md) - 完整项目文档

