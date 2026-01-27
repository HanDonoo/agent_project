# OpenWebUI Connection Guide

## 🎯 Goal

Connect your EC Skills Finder API (running on port 8001) to OpenWebUI so you can chat with it.

---

## 📋 Prerequisites

✅ EC API Server running on http://localhost:8001  
✅ OpenWebUI installed and running

---

## 🚀 Method 1: Using Docker Compose (Recommended)

### Step 1: Start Everything with Docker

```bash
cd EC_Proj

# Start Ollama + OpenWebUI
docker-compose up -d

# Wait 10 seconds for services to start
sleep 10
```

This will start:
- **Ollama**: http://localhost:11434
- **OpenWebUI**: http://localhost:3000

### Step 2: Start EC API Server

In another terminal:
```bash
cd EC_Proj
source .venv/bin/activate
python start_server.py
```

EC API will run on: http://localhost:8001

### Step 3: Configure OpenWebUI

1. **Open OpenWebUI**: http://localhost:3000
2. **Create an account** (first time only)
3. **Go to Settings** (click your profile icon → Settings)
4. **Navigate to**: Admin Panel → Settings → Connections
5. **Add OpenAI API**:
   - Click "+ Add OpenAI API"
   - **API Base URL**: `http://host.docker.internal:8001/v1`
   - **API Key**: `sk-dummy` (any value works)
   - Click "Save"

### Step 4: Select Model and Chat

1. **Start a new chat**
2. **Select model**: Click the model dropdown → Select `ec-skills-finder`
3. **Start chatting**:
   ```
   Find me a Python expert
   ```

---

## 🖥️ Method 2: Local OpenWebUI (Not Docker)

If you're running OpenWebUI locally (not in Docker):

### Step 1: Start EC API Server

```bash
cd EC_Proj
source .venv/bin/activate
python start_server.py
```

### Step 2: Configure OpenWebUI

1. **Open OpenWebUI**: http://localhost:3000 (or your OpenWebUI URL)
2. **Go to Settings** → Admin Panel → Settings → Connections
3. **Add OpenAI API**:
   - **API Base URL**: `http://localhost:8001/v1`
   - **API Key**: `sk-dummy` (any value works)
   - Click "Save"

### Step 3: Select Model and Chat

1. **Start a new chat**
2. **Select model**: `ec-skills-finder`
3. **Start chatting**

---

## 🧪 Test the Connection

### Test 1: Check if OpenWebUI can see the model

In OpenWebUI, click the model dropdown. You should see:
- `ec-skills-finder`

### Test 2: Send a test query

```
Find me a network engineer
```

Expected response:
```
✅ Found 5 matching candidates

Required Skills:
• Network Engineering (target: advanced, importance: 0.85)

👥 Top Candidates:

1. [Employee Name]
   📧 [email]
   💼 [title]
   🎯 Score: [score]
   ...
```

---

## 🐛 Troubleshooting

### Issue 1: "Model not found" or "No models available"

**Cause**: OpenWebUI can't reach the EC API server.

**Solution**:
```bash
# Check if EC API is running
curl http://localhost:8001/v1/models

# Should return:
# {"object":"list","data":[{"id":"ec-skills-finder",...}]}
```

If not working:
- Make sure EC API server is running (`python start_server.py`)
- Check the API Base URL in OpenWebUI settings

### Issue 2: "Connection refused" in Docker

**Cause**: Wrong URL for Docker.

**Solution**:
- Use `http://host.docker.internal:8001/v1` (NOT `http://localhost:8001/v1`)
- `host.docker.internal` allows Docker containers to access host machine

### Issue 3: "Invalid API Key"

**Cause**: OpenWebUI requires an API key.

**Solution**:
- Use any dummy value: `sk-dummy` or `test123`
- The EC API doesn't validate API keys

### Issue 4: Model shows but doesn't respond

**Cause**: Ollama not running or model not pulled.

**Solution**:
```bash
# Start Ollama
ollama serve

# Pull the model
ollama pull llama3.1:8b

# Verify
curl http://localhost:11434/api/tags
```

---

## 📊 Architecture Diagram

```
┌─────────────────┐
│   OpenWebUI     │  http://localhost:3000
│  (Port 3000)    │
└────────┬────────┘
         │
         │ API calls to /v1/chat/completions
         │
         ▼
┌─────────────────┐
│   EC API        │  http://localhost:8001
│  (Port 8001)    │
└────────┬────────┘
         │
         │ Calls Ollama for AI inference
         │
         ▼
┌─────────────────┐
│     Ollama      │  http://localhost:11434
│  (Port 11434)   │
│ llama3.1:8b     │
└─────────────────┘
```

---

## 🎯 Quick Reference

| Component | URL | Purpose |
|-----------|-----|---------|
| **OpenWebUI** | http://localhost:3000 | Chat interface |
| **EC API** | http://localhost:8001 | Skills finder API |
| **EC API Docs** | http://localhost:8001/docs | API documentation |
| **Ollama** | http://localhost:11434 | LLM inference |

---

## 💡 Tips

1. **Always start services in this order**:
   - Ollama first
   - EC API second
   - OpenWebUI last

2. **Check health before connecting**:
   ```bash
   curl http://localhost:8001/health
   ```

3. **View API docs**:
   - Open http://localhost:8001/docs in browser
   - Test endpoints directly

4. **Docker vs Local**:
   - Docker OpenWebUI: Use `http://host.docker.internal:8001/v1`
   - Local OpenWebUI: Use `http://localhost:8001/v1`

---

## 🆘 Still Having Issues?

Run the diagnostic:
```bash
cd EC_Proj
python tests/check_setup.py
```

Check all services:
```bash
# EC API
curl http://localhost:8001/health

# Ollama
curl http://localhost:11434/api/tags

# OpenWebUI
curl http://localhost:3000
```

