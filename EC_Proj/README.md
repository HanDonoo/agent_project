# EC Employee Skills Finder

AI-powered employee skills matching system with OpenWebUI integration.

## 🎯 Features

- **AI-Driven Skill Inference**: Uses Ollama LLM to understand complex queries
- **4-Level Proficiency System**: awareness → skilled → advanced → expert
- **Complexity Analysis**: Automatically determines required proficiency levels
- **Weighted Scoring**: Considers skill importance, verification status, and coverage
- **OpenWebUI Compatible**: Works seamlessly with OpenWebUI chat interface

## 🏗️ Architecture

```
User Query → Skill Inference → Complexity Analysis → Employee Matching → Results
              (Ollama LLM)      (Ollama LLM)         (Weighted Scoring)
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.9+**
2. **Ollama** running locally
   ```bash
   # Install Ollama: https://ollama.ai
   ollama pull llama3.1:8b
   ```

### Installation

```bash
# 1. Navigate to EC_Proj directory
cd EC_Proj

# 2. Install dependencies
pip install -r requirements.txt

# 3. Verify database exists
ls -lh data/employee_directory_200_mock.db

# 4. Start the server
python start_server.py
```

The API will be available at:
- **API Server**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

### Test the API

```bash
# Health check
curl http://localhost:8001/health

# List models (OpenWebUI compatible)
curl http://localhost:8001/v1/models

# Query employees
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "I need a deep learning expert"}'

# OpenWebUI chat completions
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ec-skills-finder",
    "messages": [
      {"role": "user", "content": "Find me a Python expert"}
    ]
  }'
```

## 🔗 OpenWebUI Integration

### Option 1: Docker Compose (Recommended)

```bash
# Start Ollama + OpenWebUI
docker-compose up -d

# Access OpenWebUI at http://localhost:3000
```

### Option 2: Manual Configuration

1. **Start the EC API server** (port 8001)
   ```bash
   python start_server.py
   ```

2. **Configure OpenWebUI**:
   - Go to Settings → Connections
   - Add OpenAI API:
     - Base URL: `http://host.docker.internal:8001/v1` (if OpenWebUI in Docker)
     - Base URL: `http://localhost:8001/v1` (if OpenWebUI local)
     - API Key: (leave empty or use any value)

3. **Select Model**:
   - In chat, select model: `ec-skills-finder`

4. **Start Chatting**:
   ```
   User: Find me a network engineer with MPLS experience
   
   EC Agent: ✅ Found 3 matching candidates
   
   Required Skills:
   • Network Engineering (target: advanced, importance: 0.85)
   • MPLS (target: skilled, importance: 0.80)
   
   👥 Top Candidates:
   
   1. John Smith
      📧 john.smith@company.co.nz
      💼 Senior Network Engineer
      🎯 Score: 2.456
      📊 Required Coverage: 100%
      ✅ Key Skills:
         • Network Engineering: expert (target: advanced) ✓
         • MPLS: advanced (target: skilled) ✓
   ...
   ```

## 📊 How It Works

### 1. Skill Inference Engine

Analyzes the query and infers:
- **Required skills** (1-10): Must-have skills
- **Preferred skills** (0-10): Nice-to-have skills
- **Importance** (0-1): How critical each skill is
- **Confidence** (0-1): How confident the inference is

Example:
```
Query: "I need someone to build a machine learning pipeline"

Inferred:
  Required:
    - Machine Learning (weight: 0.9, importance: 0.9)
    - Python (weight: 0.85, importance: 0.8)
    - Data Engineering (weight: 0.8, importance: 0.75)
  
  Preferred:
    - MLOps (weight: 0.7, importance: 0.6)
    - Docker (weight: 0.6, importance: 0.5)
```

### 2. Complexity Analysis

Determines:
- **Complexity score** (0-1): How difficult/ambiguous the task is
- **Complexity label**: low / medium / high
- **Target proficiency** per skill: awareness / skilled / advanced / expert

Rules:
- "explain/what is" → lower targets (awareness/skilled)
- "build/implement/production" → higher targets (advanced/expert)

### 3. Employee Matching

Scores each employee based on:
- **Proficiency match**: Does employee meet target level?
- **Skill verification**: Is the skill verified by manager? (+8% bonus)
- **Coverage**: % of required/preferred skills met
- **Importance weighting**: Critical skills weighted higher
- **Missing skill penalty**: Penalized for missing required skills

Final score formula:
```
score = Σ(effective_weight × confidence × match_value × verification_bonus)
        - missing_required_penalty
        × (0.7 + 0.3 × required_coverage)
```

## 📁 Project Structure

```
EC_Proj/
├── EC_api/
│   └── main.py                    # FastAPI server (OpenWebUI compatible)
├── EC_database/
│   ├── EC_db_manager.py           # Database operations
│   ├── EC_models.py               # Data models
│   └── EC_schema.sql              # Database schema
├── EC_skills_agent/
│   ├── EC_skills_interpreter_engine.py   # Skill inference (Ollama)
│   └── EC_recommender_engine.py          # Employee matching
├── data/
│   └── employee_directory_200_mock.db    # SQLite database (200 employees)
├── data_creation/
│   ├── create_new_db_with_mock_data.py   # Generate mock data
│   └── EC_skills_catalogue.py            # Skills catalogue
├── docker-compose.yml             # Ollama + OpenWebUI
├── requirements.txt               # Python dependencies
├── start_server.py               # Server startup script
└── README.md                     # This file
```

## 🔧 Configuration

Edit `EC_api/main.py` to configure:

```python
# Database
DB_PATH = "data/employee_directory_200_mock.db"

# Ollama
OLLAMA_BASE_URL = "http://localhost:11434"
CHAT_MODEL = "llama3.1:8b"

# Server
PORT = 8001
```

## 🧪 Example Queries

```
✅ "Find me a Python expert"
✅ "I need someone who knows deep learning"
✅ "Who can help with network security?"
✅ "Find a data engineer with SQL skills"
✅ "I need a DevOps engineer for Kubernetes"
✅ "Who knows React and TypeScript?"
```

## 📈 Database Statistics

- **200 employees** across multiple teams
- **Extensible skills catalogue** (100+ skills)
- **4-level proficiency system**
- **Skill verification** by managers
- **Full-text search** (SQLite FTS5)

## 🐛 Troubleshooting

### Ollama not running
```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

### Database not found
```bash
# Generate new database
cd data_creation
python create_new_db_with_mock_data.py
```

### Port 8001 already in use
```bash
# Change port in start_server.py
--port 8002
```

## 📝 License

Internal use only.

