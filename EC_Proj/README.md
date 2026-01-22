# EC Employee Skills Finder

AI-powered employee skills matching system with OpenWebUI integration.

## 🎯 Features

- **AI-Driven Skill Inference**: Uses Ollama LLM to understand complex queries
- **4-Level Proficiency System**: awareness → skilled → advanced → expert
- **Complexity Analysis**: Automatically determines required proficiency levels
- **Weighted Scoring**: Considers skill importance, verification status, and coverage
- **OpenWebUI Compatible**: Works seamlessly with OpenWebUI chat interface
- **200 Mock Employees**: Realistic telecom company structure

## 🚀 Quick Start

### First Time Setup (After Cloning)

```bash
cd EC_Proj
chmod +x setup.sh
./setup.sh
```

This will:
- ✅ Create virtual environment
- ✅ Install dependencies
- ✅ Fix macOS urllib3 issue
- ✅ Generate database (200 employees)
- ✅ Verify setup

### Regular Usage

```bash
cd EC_Proj
source .venv/bin/activate  # Activate virtual environment
python start_server.py      # Start server
```

**API Endpoints:**
- API Server: http://localhost:8001
- API Docs: http://localhost:8001/docs
- Health Check: http://localhost:8001/health

## 🔧 Manual Setup

If automated setup fails:

```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate database (IMPORTANT - not in git)
cd data_creation
python create_new_db_with_mock_data.py
cd ..

# 4. Start server
python start_server.py
```

## 🔗 OpenWebUI Integration

```bash
# Start Ollama + OpenWebUI
docker-compose up -d

# Access OpenWebUI at http://localhost:3000
# Configure: Settings → Connections → Add OpenAI API
# Base URL: http://host.docker.internal:8001/v1
# Select model: ec-skills-finder
```

## 🧪 Testing

```bash
# Health check
curl http://localhost:8001/health

# Query employees
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Find a Python expert"}'

# Run test suite
python tests/check_setup.py
bash tests/test_api.sh
```

## 🐛 Troubleshooting

### "No skills found in DB" Error

Database files are NOT in git. Generate them:
```bash
cd data_creation
python create_new_db_with_mock_data.py
cd ..
```

### urllib3 LibreSSL Warning (macOS)

Already fixed in requirements.txt:
```bash
pip install 'urllib3<2.0'
```

### Port 8001 Already in Use

```bash
lsof -ti:8001 | xargs kill -9
```

### Ollama Not Running

```bash
ollama serve
ollama pull llama3.1:8b
```

## 📁 Project Structure

```
EC_Proj/
├── EC_api/main.py                 # FastAPI server
├── EC_database/                   # Database layer
├── EC_skills_agent/               # AI inference engines
├── data/                          # Database files (not in git)
├── data_creation/                 # Mock data generator
├── tests/                         # Test suite
├── setup.sh                       # Automated setup
└── requirements.txt               # Dependencies
```

## 📝 API Endpoints

- `GET /health` - Health check
- `GET /v1/models` - List available models (OpenWebUI)
- `POST /v1/chat/completions` - Chat endpoint (OpenWebUI)
- `POST /query` - Direct query endpoint
- `GET /docs` - Interactive API documentation

## 📝 License

Internal use only.

