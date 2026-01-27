# Ollama Timeout Error - 解决方案

## 🐛 问题

错误信息：
```
ReadTimeout: HTTPConnectionPool(host='localhost', port=11434): Read timed out. (read timeout=120)
```

**原因：** Ollama 处理请求超过 120 秒没有返回结果。

---

## ✅ 已修复

我已经将超时时间从 **120秒** 增加到 **300秒（5分钟）**。

修改文件：`EC_Proj/EC_skills_agent/EC_skills_interpreter_engine.py`

---

## 🔧 你的同事需要做的事情

### 步骤 1：运行诊断脚本

```bash
cd EC_Proj
python tests/test_ollama.py
```

这个脚本会：
- ✅ 检查 Ollama 是否运行
- ✅ 检查模型是否已安装
- ✅ 测试 Ollama 响应速度
- ✅ 给出性能建议

### 步骤 2：根据诊断结果采取行动

#### 情况 A：Ollama 没有运行

```bash
# 启动 Ollama
ollama serve
```

#### 情况 B：模型没有安装

```bash
# 安装模型
ollama pull llama3.1:8b
```

#### 情况 C：电脑太慢，使用更小的模型

```bash
# 1. 安装更小的模型（3B 参数，比 8B 快很多）
ollama pull llama3.2:3b

# 2. 修改配置
# 编辑 EC_Proj/EC_api/main.py
# 找到这一行：
CHAT_MODEL = "llama3.1:8b"
# 改为：
CHAT_MODEL = "llama3.2:3b"

# 3. 重启服务器
python start_server.py
```

#### 情况 D：第一次运行慢（正常）

第一次调用 Ollama 时，需要：
1. 加载模型到内存（可能需要 30-60 秒）
2. 处理请求

**解决方法：预热模型**

```bash
# 发送一个简单的测试请求，让模型加载到内存
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.1:8b",
  "prompt": "Hello",
  "stream": false
}'

# 等待这个命令完成（可能需要 1-2 分钟）
# 之后的请求就会快很多
```

---

## 📊 性能参考

| 模型 | 参数量 | 内存需求 | 速度 | 质量 |
|------|--------|----------|------|------|
| llama3.2:1b | 1B | ~1GB | 🚀 很快 | ⭐⭐ 一般 |
| llama3.2:3b | 3B | ~2GB | 🚀 快 | ⭐⭐⭐ 好 |
| llama3.1:8b | 8B | ~5GB | ⏱️ 中等 | ⭐⭐⭐⭐ 很好 |

**推荐：**
- 💻 普通电脑：使用 `llama3.2:3b`
- 🖥️ 高性能电脑：使用 `llama3.1:8b`

---

## 🧪 测试修复

### 1. 重启服务器

```bash
# 停止当前服务器（Ctrl+C）
# 重新启动
cd EC_Proj
python start_server.py
```

### 2. 在 OpenWebUI 中测试

发送一个简单的查询：
```
Find a Python developer
```

### 3. 查看日志

现在日志会显示详细信息：
```
📨 Received chat completion request from OpenWebUI
🔍 Step 1: Inferring skills using Ollama...
✅ Skill inference complete: 2 required, 1 preferred
🔍 Step 2: Analyzing query complexity...
✅ Complexity analysis complete: medium (score: 0.65)
🔍 Step 3: Finding matching employees...
✅ Found 5 matching candidates
```

如果出错，会看到：
```
❌ Ollama error: ReadTimeout: ...
📋 Full traceback: ...
```

---

## 🆘 如果还是超时

### 选项 1：使用更小的模型（推荐）

```bash
ollama pull llama3.2:3b
# 修改 EC_api/main.py 中的 CHAT_MODEL
```

### 选项 2：增加超时时间

编辑 `EC_Proj/EC_skills_agent/EC_skills_interpreter_engine.py`：

```python
# 找到这一行（第 118 行）
def chat(self, model: str, messages: List[dict], temperature: float = 0.2, timeout: int = 300) -> str:

# 将 300 改为更大的值，比如 600（10分钟）
def chat(self, model: str, messages: List[dict], temperature: float = 0.2, timeout: int = 600) -> str:
```

### 选项 3：使用降级模式（不需要 Ollama）

如果电脑实在跑不动 Ollama，代码会自动降级到关键词搜索模式：

```
⚠️ Ollama not available, using fallback mode
⚠️ Found 5 employees using keyword search (Ollama unavailable)
```

这个模式不需要 AI，但搜索质量会降低。

---

## 📝 总结

1. ✅ **已修复**：超时时间从 120秒 增加到 300秒
2. ✅ **已添加**：详细的错误日志
3. ✅ **已添加**：自动降级模式（Ollama 不可用时）
4. ✅ **已添加**：诊断工具 `tests/test_ollama.py`

**让你的同事运行：**
```bash
cd EC_Proj
python tests/test_ollama.py
```

根据诊断结果采取相应措施即可！

