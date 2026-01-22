# OpenWebUI Integration Guide 🔌

Complete OpenWebUI integration tutorial for the Employee Finder Agent.

---

## 📋 Prerequisites

### 1. Ensure Agent Server is Running

```bash
# Start server
cd /path/to/agent_project
python scripts/start_server.py

# Or use uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 2. Verify Server Status

```bash
# Check health status
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","database":"connected","ai_routing_enabled":true,...}
```

### 3. Ensure Test Data Exists

```bash
# If no data exists, run:
python scripts/create_mock_data.py
```

### 4. OpenWebUI Installed

If OpenWebUI is not installed yet:

```bash
# Install using Docker (recommended)
docker run -d -p 3000:8080 \
  --name openwebui \
  ghcr.io/open-webui/open-webui:main

# Or install using pip
pip install open-webui
open-webui serve
```

Visit: http://localhost:3000

---

## 🚀 Method 1: As OpenAI-Compatible API (Recommended)

Our Agent implements an OpenAI-compatible `/v1/chat/completions` endpoint and can be used directly as a custom model.

### Step 1: Open OpenWebUI Settings

1. Visit http://localhost:3000
2. Log in to OpenWebUI
3. Click the **avatar** or **settings icon** ⚙️ in the top left
4. Select **Admin Panel** or **Settings**

### Step 2: Add Custom OpenAI API

In the Admin Panel:

1. Find the **Connections** or **External Connections** section
2. Find the **OpenAI API** configuration area
3. Click **Add** or **+** to add a new connection

### Step 3: Fill in Configuration Information

```
Name: Company Employee Finder
Base URL: http://localhost:8000/v1
API Key: sk-dummy-key-not-required
```

**Important Notes:**
- **Base URL**: Must be `http://localhost:8000/v1` (note the `/v1` suffix)
- **API Key**: Our API doesn't verify keys, but OpenWebUI requires one - fill in any value
- **If on different machines**:
  - Change `localhost` to the Agent server's IP address
  - Example: `http://192.168.1.100:8000/v1`
  - If using Docker, use `http://host.docker.internal:8000/v1`

### Step 4: Save and Refresh Model List

1. Click **Save** to save the configuration
2. Return to the chat interface
3. Click the **model selector** at the top (usually shows current model name)
4. Find `employee-finder` in the dropdown list
5. Select this model

### Step 5: Start Chatting!

You can now use the Agent!

---

## 🧪 Test Queries

Try the following queries in OpenWebUI:

### 1. Direct Lookup (Fast, No AI)
```
Find john.smith@sample.com
```
**Expected:** ~10ms response, returns John Smith's information

### 2. Simple Search (Pattern Matching)
```
Who is in the billing team?
```
**Expected:** ~50ms response, returns Billing Operations team members

### 3. Complex Query (Uses AI Understanding, if enabled)
```
I need help with BIA provisioning for a new enterprise customer
```
**Expected:** Returns Emma Wilson (Primary Owner) and David Brown (Backup)

### 4. Responsibility Query
```
Who handles network security?
```
**Expected:** Returns Sarah Johnson (Network Security Specialist)

### 5. Conversational
```
Thanks! Can you also tell me who their manager is?
```
**Expected:** AI understands context and returns manager information

---

## ⚙️ Configuration Options

### Option A: No LLM (Default, Fastest)

```bash
# .env
USE_AI_ROUTING=True
ENABLE_LLM=False
```

**Features:**
- ✅ Fastest speed (10-100ms)
- ✅ No LLM configuration needed
- ✅ Suitable for simple queries
- ❌ Limited complex query understanding

### Option B: Use OpenAI (Most Intelligent)

```bash
# .env
USE_AI_ROUTING=True
ENABLE_LLM=True
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_MODEL=gpt-3.5-turbo
```

**Features:**
- ✅ Understands complex queries
- ✅ Natural conversation ability
- ✅ Context understanding
- ❌ Requires API fees
- ❌ Slightly slower (~800ms)

### Option C: Use Local LLM (Privacy First)

```bash
# .env
USE_AI_ROUTING=True
ENABLE_LLM=True
LLM_PROVIDER=local
LOCAL_LLM_ENDPOINT=http://localhost:11434/v1
LOCAL_LLM_MODEL=llama2
```

**Prerequisites:** Install Ollama first
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Download model
ollama pull llama2

# Start Ollama (default port 11434)
ollama serve
```

**Features:**
- ✅ Data stays local
- ✅ Free
- ✅ Works offline
- ❌ Requires local GPU/CPU resources
- ❌ Slower (1-3 seconds)

---

## 🔍 Verify Integration

### 1. Check Server Status

```bash
curl http://localhost:8000/health
```

**Expected Response:**
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

### 2. Test OpenAI Compatible Endpoint

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "employee-finder",
    "messages": [
      {"role": "user", "content": "I need help with BIA provisioning"}
    ]
  }'
```

**Expected Response:**
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "employee-finder",
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

## 🎨 User Experience in OpenWebUI

### Conversation Examples

**User:** "I need help with BIA provisioning"

**Agent:**
```
👥 Recommended Contacts:

1. Emma Wilson (Primary Owner)
   📧 emma.wilson@sample.com
   💼 BIA Provisioning Lead
   👥 Team: Provisioning Services
   🎯 Match: 90% - Primary owner of: BIA provisioning
   ⬆️ Escalation: Emma Wilson (emma.wilson@sample.com)

2. David Brown (Backup)
   📧 david.brown@sample.com
   💼 Provisioning Specialist
   👥 Team: Provisioning Services
   🎯 Match: 60% - Backup for: BIA provisioning
```

**User:** "What about network security?"

**Agent:**
```
👥 Recommended Contacts:

1. Sarah Johnson (Primary Owner)
   📧 sarah.johnson@sample.com
   💼 Network Security Specialist
   👥 Team: Network Infrastructure
   🎯 Match: 90% - Primary owner of: network security
   ⬆️ Escalation: John Smith (john.smith@sample.com)
```

---

## 🐛 Troubleshooting

### Issue 1: OpenWebUI Cannot Connect

**Check:**
```bash
# Confirm server is running
curl http://localhost:8000/health

# Check if port is in use
lsof -i :8000
```

**Solution:**
- Ensure server is started: `python scripts/start_server.py`
- Check firewall settings
- If on different machines, ensure network is reachable

### Issue 2: Returns Empty Results

**Check:**
```bash
# Confirm database has data
python scripts/create_mock_data.py
```

### Issue 3: LLM Not Working

**Check:**
```bash
# View .env configuration
cat .env | grep LLM

# If using OpenAI, test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# If using local LLM, test Ollama
curl http://localhost:11434/api/tags
```

---

## 📊 Performance Optimization Recommendations

### 1. For Most Queries (Recommended)
```bash
USE_AI_ROUTING=True
ENABLE_LLM=False
```
- 38.5% of queries go directly to database (10-50ms)
- Rest use pattern matching (50-150ms)

### 2. For Complex Business Scenarios
```bash
USE_AI_ROUTING=True
ENABLE_LLM=True
LLM_PROVIDER=openai
```
- Simple queries remain fast (10-50ms)
- Complex queries use AI understanding (~800ms)

---

## 🎯 Next Steps

1. ✅ Test basic queries in OpenWebUI
2. ✅ Adjust AI configuration as needed
3. ✅ Import real employee data (replace mock data)
4. ✅ Collect user feedback
5. ✅ Monitor usage and performance

---

**Need Help?** See other documentation:
- [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) - How the router works
- [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) - Technical architecture
- [README.md](README.md) - Complete project documentation

