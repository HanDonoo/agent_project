# 🌟 Gemini API 设置指南

本指南将帮助你从 Ollama 本地模型切换到 Google Gemini API。

---

## 📋 前提条件

1. **Google Gemini API Key**
   - 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
   - 登录你的 Google 账号
   - 点击 "Create API Key"
   - 复制生成的 API key

---

## 🔧 设置步骤

### 步骤 1：安装依赖

```bash
cd EC_Proj

# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate  # Windows

# 安装新依赖
pip install -r requirements.txt
```

### 步骤 2：创建 .env 文件

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件
nano .env  # 或使用你喜欢的编辑器
```

### 步骤 3：配置 API Key

在 `.env` 文件中设置：

```bash
# AI Provider: "ollama" or "gemini"
AI_PROVIDER=gemini

# Gemini API Configuration
GEMINI_API_KEY=你的_API_KEY_这里
GEMINI_MODEL=gemini-1.5-flash

# Server Configuration
API_PORT=8001
API_HOST=0.0.0.0

# Logging
LOG_LEVEL=INFO
```

**重要：** 将 `你的_API_KEY_这里` 替换为你从 Google AI Studio 获取的实际 API key。

### 步骤 4：启动服务器

```bash
python start_server.py
```

你应该看到：

```
🚀 Initializing EC Skills Finder API Server
================================================================================
✅ Configuration validated
📁 Database path: data/employee_directory_200_mock.db
🤖 AI Provider: gemini
🌟 Gemini Model: gemini-2.0-flash-exp
🤖 Initializing AI client (gemini)...
✅ AI client initialized
🧠 Initializing skill inference engine...
✅ Skill inference engine initialized
================================================================================
✅ All components initialized successfully
================================================================================
```

---

## 🔄 切换回 Ollama

如果你想切换回 Ollama 本地模型：

1. 编辑 `.env` 文件：
   ```bash
   AI_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.2:3b
   ```

2. 确保 Ollama 正在运行：
   ```bash
   ollama serve
   ```

3. 重启服务器：
   ```bash
   python start_server.py
   ```

---

## 📊 Gemini vs Ollama 对比

| 特性 | Gemini | Ollama |
|------|--------|--------|
| **速度** | ⚡ 非常快（云端） | 🐌 取决于硬件 |
| **成本** | 💰 按使用付费 | 🆓 免费 |
| **隐私** | ☁️ 数据发送到 Google | 🔒 完全本地 |
| **质量** | ⭐⭐⭐⭐⭐ 优秀 | ⭐⭐⭐⭐ 很好 |
| **依赖** | 🌐 需要网络 | 💻 需要本地资源 |
| **设置** | 🔑 需要 API key | 🐳 需要 Docker/本地安装 |

---

## 🧪 测试 Gemini 集成

### 测试 1：健康检查

```bash
curl http://localhost:8001/health
```

应该返回：
```json
{
  "status": "healthy",
  "database": "connected",
  "employees": 200
}
```

### 测试 2：技能查询

```bash
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "One-Connector",
    "messages": [
      {"role": "user", "content": "Find me a Python expert"}
    ]
  }'
```

### 测试 3：在 OpenWebUI 中测试

1. 打开 OpenWebUI (http://localhost:3000)
2. 选择模型：`One-Connector`
3. 输入查询：`Find a machine learning engineer`
4. 查看结果

---

## ❓ 常见问题

### Q: API key 无效怎么办？

**A:** 检查以下几点：
1. API key 是否正确复制（没有多余空格）
2. API key 是否已激活
3. Google Cloud 项目是否启用了 Generative Language API

### Q: 请求超时怎么办？

**A:** Gemini API 通常很快，如果超时：
1. 检查网络连接
2. 检查 Google AI Studio 服务状态
3. 尝试使用更小的模型（如 `gemini-1.5-flash`）

### Q: 成本如何计算？

**A:** Gemini API 按 token 计费：
- 输入：$0.00025 / 1K tokens
- 输出：$0.00050 / 1K tokens
- 每月有免费额度

详见：https://ai.google.dev/pricing

### Q: 数据隐私如何保障？

**A:** 
- 使用 Gemini API 时，查询会发送到 Google 服务器
- 如果需要完全本地化，请使用 Ollama
- Google 的数据使用政策：https://ai.google.dev/terms

---

## 📝 环境变量说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AI_PROVIDER` | AI 提供商（`ollama` 或 `gemini`） | `gemini` |
| `GEMINI_API_KEY` | Gemini API 密钥 | 无（必填） |
| `GEMINI_MODEL` | Gemini 模型名称 | `gemini-2.0-flash-exp` |
| `OLLAMA_BASE_URL` | Ollama 服务器地址 | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama 模型名称 | `llama3.2:3b` |
| `API_PORT` | API 服务器端口 | `8001` |
| `API_HOST` | API 服务器主机 | `0.0.0.0` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

---

## 🎉 完成！

现在你的 EC Skills Finder 已经使用 Gemini API 了！

**优势：**
- ✅ 更快的响应速度
- ✅ 更好的推理质量
- ✅ 不需要本地 GPU/CPU 资源
- ✅ 不需要下载大型模型

**下一步：**
- 在 OpenWebUI 中测试查询
- 监控 API 使用情况
- 根据需要调整模型参数

