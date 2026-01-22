# Employee Finder Agent Project

## 📁 Project Structure

```
agent_project/
├── EC_Proj/          # Main Project - EC Employee Skills Finder (Current Version)
│   ├── EC_api/       # FastAPI Server (OpenWebUI Integration)
│   ├── EC_database/  # Database Management
│   ├── EC_skills_agent/  # AI Skills Inference Engine
│   ├── data/         # Database Files (200 employees)
│   ├── data_creation/  # Data Generation Scripts
│   ├── tests/        # Test Files
│   │   ├── EC_skills_interpreter_test.py
│   │   ├── EC_recommender_test.py
│   │   ├── check_setup.py
│   │   └── test_api.sh
│   ├── README.md     # Full Documentation
│   ├── QUICKSTART.md # Quick Start Guide
│   ├── requirements.txt
│   ├── start_server.py
│   └── docker-compose.yml
│
└── V1/               # Legacy Version - Simple Keyword Matching System
    ├── agent/        # Legacy Agent Logic
    ├── api/          # Legacy API
    ├── database/     # Legacy Database
    ├── scripts/      # Legacy Scripts
    ├── tests/        # Legacy Tests
    └── README.md     # Legacy Documentation
```

## 🚀 Quick Start

### First Time Setup (New Team Members)

If you just cloned this repository:

```bash
cd EC_Proj
chmod +x setup.sh
./setup.sh
```

This will install dependencies, generate the database, and verify setup.

**For detailed setup instructions, see [EC_Proj/SETUP.md](EC_Proj/SETUP.md)**

### Using EC_Proj (After Setup)

```bash
# 1. Navigate to EC_Proj directory
cd EC_Proj

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Start server
python start_server.py
```

Server will run at **http://localhost:8001**

### API Endpoints

- **Health Check**: `GET http://localhost:8001/health`
- **OpenWebUI Model List**: `GET http://localhost:8001/v1/models`
- **OpenWebUI Chat**: `POST http://localhost:8001/v1/chat/completions`
- **Direct Query**: `POST http://localhost:8001/query`
- **API Documentation**: `http://localhost:8001/docs`

## 📚 Documentation

- **EC_Proj Documentation**: [EC_Proj/README.md](EC_Proj/README.md)
- **V1 Legacy Documentation**: [V1/README.md](V1/README.md)

## 🆚 Version Comparison

| Feature | V1 (Legacy) | EC_Proj (Current) |
|---------|-------------|-------------------|
| **Search Method** | Keyword Matching | AI-Driven Skills Inference |
| **Skills System** | Simple Tags | 4-Level Proficiency System |
| **Employee Count** | 16 | 200 |
| **AI Engine** | None | Ollama (llama3.1:8b) |
| **OpenWebUI** | Basic Integration | Full Integration |
| **Complexity Analysis** | None | Intelligent Complexity Analysis |
| **Scoring System** | Simple Matching | Weighted Scoring Algorithm |

## 🧪 Testing

```bash
# Run environment check
cd EC_Proj
python tests/check_setup.py

# Run API tests
cd EC_Proj
bash tests/test_api.sh

# Run skills inference tests
cd EC_Proj
python tests/EC_skills_interpreter_test.py

# Run recommender engine tests
cd EC_Proj
python tests/EC_recommender_test.py
```

## 🔧 Dependencies

### EC_Proj Dependencies

- Python 3.9+
- FastAPI
- Uvicorn
- Pydantic
- Requests
- Ollama (llama3.1:8b)

### Installation

```bash
cd EC_Proj
pip install -r requirements.txt
```

## 🐳 Docker Deployment

```bash
cd EC_Proj
docker-compose up -d
```

This will start:
- Ollama (port 11434)
- OpenWebUI (port 3000)

Then manually start EC API:
```bash
python start_server.py
```

## 📝 License

Internal Use Only

## 🤝 Contributing

This is an internal project.

---

**Current Active Project**: EC_Proj
**Legacy Version Archive**: V1/

