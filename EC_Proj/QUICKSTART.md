# EC Skills Finder - Quick Start Guide

## 🚀 5-Minute Setup

### Step 1: Start Ollama

**Option A: Using Docker Compose (Recommended)**
```bash
cd EC_Proj
docker-compose up -d ollama
```

**Option B: Local Ollama**
```bash
# If Ollama is already installed
ollama serve

# In another terminal, pull the model
ollama pull llama3.1:8b
```

**Verify Ollama is running:**
```bash
curl http://localhost:11434/api/tags
```

### Step 2: Install Python Dependencies

```bash
cd EC_Proj
pip install -r requirements.txt
```

### Step 3: Start the API Server

```bash
python start_server.py
```

You should see:
```
🚀 Starting EC Skills Finder API Server...
============================================================
📍 API will be available at: http://localhost:8001
📚 API docs at: http://localhost:8001/docs
🔗 OpenWebUI endpoint: http://localhost:8001/v1/chat/completions
============================================================

INFO:     Uvicorn running on http://0.0.0.0:8001
```

### Step 4: Test the API

**In another terminal:**
```bash
# Health check
curl http://localhost:8001/health

# Test query
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Find me a Python expert"}'
```

### Step 5: Connect to OpenWebUI

**Option A: Start OpenWebUI with Docker Compose**
```bash
docker-compose up -d open-webui
```
Then open: http://localhost:3000

**Option B: Use existing OpenWebUI**

1. Go to OpenWebUI Settings → Connections
2. Add OpenAI API:
   - **Base URL**: `http://host.docker.internal:8001/v1` (Docker)
   - **Base URL**: `http://localhost:8001/v1` (Local)
   - **API Key**: (any value or leave empty)
3. Select model: `ec-skills-finder`
4. Start chatting!

## 🧪 Example Queries

Try these in OpenWebUI:

```
✅ "Find me a Python expert"
✅ "I need someone who knows deep learning"
✅ "Who can help with network security?"
✅ "Find a data engineer with SQL skills"
✅ "I need a DevOps engineer for Kubernetes"
```

## 🐛 Troubleshooting

### Ollama not running
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
docker-compose up -d ollama
# OR
ollama serve
```

### Model not found
```bash
# Pull the model
ollama pull llama3.1:8b

# Verify
ollama list
```

### Port 8001 already in use
```bash
# Find what's using the port
lsof -ti:8001

# Kill it
lsof -ti:8001 | xargs kill -9

# Or change port in start_server.py
```

### Database not found
```bash
# Check if database exists
ls -lh EC_Proj/data/employee_directory_200_mock.db

# If not, generate it
cd EC_Proj/data_creation
python create_new_db_with_mock_data.py
```

## 📊 What You Get

- **200 mock employees** with realistic skills
- **4-level proficiency system**: awareness → skilled → advanced → expert
- **AI-powered skill inference**: Understands complex queries
- **Weighted scoring**: Considers importance, verification, coverage
- **OpenWebUI integration**: Chat interface ready

## 🎯 Next Steps

1. ✅ Test basic queries
2. ✅ Try complex queries
3. ✅ Explore the API docs: http://localhost:8001/docs
4. ✅ Check the scoring logic in matched_skills
5. ✅ Customize the skills catalogue

## 📚 Documentation

- **README.md**: Full documentation
- **API Docs**: http://localhost:8001/docs (when server is running)
- **Database Schema**: `EC_database/EC_schema.sql`
- **Skills Catalogue**: `data_creation/EC_skills_catalogue.py`

## 🔗 Useful URLs

- **API Server**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health
- **OpenWebUI**: http://localhost:3000 (if using Docker Compose)
- **Ollama**: http://localhost:11434

---

**Need help?** Check the main README.md or the troubleshooting section above.

