# Employee Finder Agent Project

## 📁 项目结构

```
agent_project/
├── EC_Proj/          # 主项目 - EC Employee Skills Finder (当前版本)
│   ├── EC_api/       # FastAPI 服务器 (OpenWebUI 集成)
│   ├── EC_database/  # 数据库管理
│   ├── EC_skills_agent/  # AI 技能推理引擎
│   ├── data/         # 数据库文件 (200 员工)
│   ├── data_creation/  # 数据生成脚本
│   ├── test/         # 测试文件
│   │   ├── EC_skills_interpreter_test.py
│   │   ├── EC_recommender_test.py
│   │   ├── check_setup.py
│   │   └── test_api.sh
│   ├── README.md     # 完整文档
│   ├── QUICKSTART.md # 快速开始指南
│   ├── requirements.txt
│   ├── start_server.py
│   └── docker-compose.yml
│
└── V1/               # 旧版本 - 简单关键词匹配系统
    ├── agent/        # 旧版 Agent 逻辑
    ├── api/          # 旧版 API
    ├── database/     # 旧版数据库
    ├── scripts/      # 旧版脚本
    ├── tests/        # 旧版测试
    └── README.md     # 旧版文档
```

## 🚀 快速开始

### 使用 EC_Proj (推荐)

```bash
# 1. 进入 EC_Proj 目录
cd EC_Proj

# 2. 查看快速开始指南
cat QUICKSTART.md

# 3. 检查环境
python test/check_setup.py

# 4. 启动服务器
python start_server.py
```

服务器将在 **http://localhost:8001** 运行

### API 端点

- **健康检查**: `GET http://localhost:8001/health`
- **OpenWebUI 模型列表**: `GET http://localhost:8001/v1/models`
- **OpenWebUI 聊天**: `POST http://localhost:8001/v1/chat/completions`
- **直接查询**: `POST http://localhost:8001/query`
- **API 文档**: `http://localhost:8001/docs`

## 📚 文档

- **EC_Proj 完整文档**: [EC_Proj/README.md](EC_Proj/README.md)
- **快速开始指南**: [EC_Proj/QUICKSTART.md](EC_Proj/QUICKSTART.md)
- **V1 旧版文档**: [V1/README.md](V1/README.md)

## 🆚 版本对比

| 特性 | V1 (旧版) | EC_Proj (当前) |
|------|-----------|----------------|
| **搜索方式** | 关键词匹配 | AI 驱动的技能推理 |
| **技能系统** | 简单标签 | 4 级熟练度系统 |
| **员工数量** | 16 | 200 |
| **AI 引擎** | 无 | Ollama (llama3.1:8b) |
| **OpenWebUI** | 基础集成 | 完整集成 |
| **复杂度分析** | 无 | 智能复杂度分析 |
| **评分系统** | 简单匹配 | 加权评分算法 |

## 🧪 测试

```bash
# 运行环境检查
cd EC_Proj
python test/check_setup.py

# 运行 API 测试
cd EC_Proj
bash test/test_api.sh

# 运行技能推理测试
cd EC_Proj
python test/EC_skills_interpreter_test.py

# 运行推荐引擎测试
cd EC_Proj
python test/EC_recommender_test.py
```

## 🔧 依赖

### EC_Proj 依赖

- Python 3.9+
- FastAPI
- Uvicorn
- Pydantic
- Requests
- Ollama (llama3.1:8b)

### 安装

```bash
cd EC_Proj
pip install -r requirements.txt
```

## 🐳 Docker 部署

```bash
cd EC_Proj
docker-compose up -d
```

这将启动：
- Ollama (端口 11434)
- OpenWebUI (端口 3000)

然后手动启动 EC API：
```bash
python start_server.py
```

## 📝 许可

内部使用

## 🤝 贡献

这是一个内部项目。

---

**当前活跃项目**: EC_Proj  
**旧版本存档**: V1/

