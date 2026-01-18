# OpenWebUI 完整配置指南 🚀

**环境：** macOS + Docker OpenWebUI

---

## ✅ 前提检查

### 1. 确认Agent服务器正在运行

```bash
# 检查服务器状态
curl http://localhost:8000/health

# 应该返回：
# {"status":"healthy","database":"connected",...}
```

### 2. 测试两个关键端点

```bash
# 测试模型列表
curl http://localhost:8000/v1/models

# 应该返回：
# {"object":"list","data":[{"id":"one-nz-employee-finder",...}]}

# 测试聊天
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"one-nz-employee-finder","messages":[{"role":"user","content":"test"}]}'

# 应该返回OpenAI格式的响应
```

✅ 如果两个都成功，继续下一步！

---

## 🐳 OpenWebUI配置步骤

### 步骤1: 访问OpenWebUI

打开浏览器访问：
```
http://localhost:3000
```

### 步骤2: 进入Admin设置

1. 登录OpenWebUI
2. 点击左下角的 **头像/用户名**
3. 选择 **Admin Panel（管理面板）**
4. 或者点击 **Settings** → **Admin Settings**

### 步骤3: 配置OpenAI API连接

在 **General** 或 **Connections** 部分找到 **OpenAI API**：

```
API Base URL: http://host.docker.internal:8000/v1
API Key: sk-dummy-key
```

**重要说明：**
- ✅ 必须使用 `host.docker.internal`（Docker Desktop for Mac自动支持）
- ✅ 必须包含 `/v1` 后缀
- ✅ API Key随便填（我们的Agent不验证）

### 步骤4: 保存配置

点击页面底部或右上角的 **Save** 按钮

### 步骤5: 验证连接（可选）

如果有 **Test Connection** 按钮，点击测试。

或者手动从Docker容器内测试：

```bash
# 进入OpenWebUI容器
docker exec -it openwebui sh

# 测试连接
wget -O- http://host.docker.internal:8000/v1/models

# 应该看到模型列表
# 退出
exit
```

### 步骤6: 返回聊天界面

1. 点击左侧的 **Chat** 图标
2. 或直接访问 http://localhost:3000

### 步骤7: 选择模型

在聊天界面顶部：

1. 点击 **模型选择器**（显示当前模型名的下拉框）
2. 在列表中找到 **`one-nz-employee-finder`**
3. 点击选择

**如果看不到模型：**
- 刷新页面（F5 或 Cmd+R）
- 重新保存一次API配置
- 检查浏览器控制台是否有错误

### 步骤8: 开始测试！

发送测试消息：

```
I need help with BIA provisioning
```

**预期响应：**
```
✅ Found 3 people matching your search

📋 Recommended Roles/Teams:
  • BIA Provisioning Lead
  • Provisioning Specialist
  ...

👥 Recommended Contacts:

1. Emma Wilson (primary)
   📧 emma.wilson@onenz.co.nz
   💼 BIA Provisioning Lead
   ...
```

---

## 🧪 更多测试查询

```
1. "Who is in the billing team?"
   → 应返回 Robert Davis, Jennifer Lee

2. "emma.wilson@onenz.co.nz"
   → 应返回 Emma Wilson的详细信息

3. "Who handles network security?"
   → 应返回 Sarah Johnson

4. "I need help with compliance"
   → 应返回 Alice Martinez
```

---

## 🐛 故障排查

### 问题1: 看不到模型 `one-nz-employee-finder`

**检查：**
```bash
# 1. 确认Agent在运行
curl http://localhost:8000/v1/models

# 2. 从Docker容器内测试
docker exec openwebui wget -O- http://host.docker.internal:8000/v1/models
```

**解决方案：**
- 确保API Base URL正确：`http://host.docker.internal:8000/v1`
- 刷新OpenWebUI页面
- 清除浏览器缓存
- 重启OpenWebUI容器：
  ```bash
  docker restart openwebui
  ```

### 问题2: 连接失败 "Connection refused"

**检查：**
```bash
# 确认Agent服务器在运行
ps aux | grep uvicorn

# 确认端口8000开放
lsof -i :8000

# 测试本地连接
curl http://localhost:8000/health
```

**解决方案：**
- 启动Agent服务器：
  ```bash
  cd /Users/handongdong/pythonProjects/agent_project
  uvicorn api.main:app --host 0.0.0.0 --port 8000
  ```

### 问题3: 返回 "Streaming not supported"

**解决方案：**

在OpenWebUI中禁用streaming：

1. 进入 **Settings** → **Interface**
2. 找到 **Streaming** 或 **Enable Streaming** 选项
3. 关闭它
4. 或者在聊天时，点击设置图标，取消勾选 "Stream"

---

## 📊 完整验收清单

配置成功后，确认：

- [ ] Agent服务器在运行（`curl http://localhost:8000/health` 成功）
- [ ] `/v1/models` 端点返回模型列表
- [ ] `/v1/chat/completions` 端点返回正确响应
- [ ] OpenWebUI中能看到 `one-nz-employee-finder` 模型
- [ ] 选择模型后可以正常对话
- [ ] 查询返回格式化的员工信息

---

## 🎯 快速启动命令（完整版）

```bash
# 终端1: 启动Agent
cd /Users/handongdong/pythonProjects/agent_project
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 终端2: 启动OpenWebUI（如果还没启动）
docker run -d \
  -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --name openwebui \
  ghcr.io/open-webui/open-webui:main

# 浏览器: 访问OpenWebUI
open http://localhost:3000

# 配置:
# Settings → Admin Panel → OpenAI API
# Base URL: http://host.docker.internal:8000/v1
# API Key: sk-dummy-key
# Save

# 使用:
# Chat → 选择 one-nz-employee-finder → 开始对话
```

---

## 🎉 成功！

现在你可以在OpenWebUI中使用One NZ Employee Finder Agent了！

**享受你的AI助手！** 🚀

---

**需要帮助？** 查看其他文档：
- [README.md](README.md) - 项目总览
- [AI_ROUTER_SUMMARY.md](AI_ROUTER_SUMMARY.md) - AI路由说明
- [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) - 更多查询示例

