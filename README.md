# One NZ Employee Finder Agent 🤖

An AI-powered agent designed to break down silos within One NZ by enabling internal employees to quickly identify and connect with the most relevant people across teams for any query or project.

**Version 2.0** - Now with intelligent AI routing!

## 🎯 Purpose

This agent promotes collaboration, accelerates problem-solving, and fosters innovation by ensuring employees can easily form cross-functional teams aligned to their objectives.

## ✨ Key Features

Based on comprehensive user research and survey insights:

- **🤖 Intelligent AI Router**: Automatically decides when to use AI vs direct queries for optimal speed and accuracy
- **🎯 Ownership-First Matching**: Finds people who are actually responsible for tasks, not just experts
- **👥 Role-Before-Person**: Shows recommended roles/teams first, then specific contacts
- **⚡ Time-Saving Focus**: Reduces average search time from 39.3 minutes/week to under 1 minute
- **🔄 Backup & Escalation**: Shows people leaders for easy escalation
- **🔒 Privacy-Compliant**: No PII storage, session-only data processing
- **🤝 Teams Integration Ready**: Designed to integrate with Microsoft Teams
- **🔌 Flexible LLM Support**: Works with OpenAI, local LLMs (Ollama), or no LLM at all

## 📊 Architecture

### System Overview

```
User Query → Router → Strategy Selection → Tools → Database → Response
                ↓
        Direct / Pattern / AI
```

**Key Components:**

1. **Router** (`agent/router.py`) - Classifies queries and decides strategy
2. **Tools** (`agent/tools.py`) - 7 database search functions
3. **LLM Integration** (`agent/llm_integration.py`) - Optional AI understanding
4. **Enhanced Agent** (`agent/ai_agent.py`) - Orchestrates the workflow

### File Structure

```
agent_project/
├── database/           # SQLite database with FTS5 full-text search
│   ├── schema.sql     # Database schema
│   ├── models.py      # Data models
│   └── db_manager.py  # Database operations
├── agent/             # Core AI agent logic
│   ├── router.py      # 🆕 Intelligent query routing
│   ├── tools.py       # 🆕 Database search tools
│   ├── llm_integration.py  # 🆕 LLM provider support
│   ├── ai_agent.py    # 🆕 Enhanced AI agent
│   └── employee_finder_agent.py  # Basic pattern-matching agent
├── api/               # FastAPI REST API
│   └── main.py        # API endpoints (OpenWebUI compatible)
├── data_import/       # Excel data import utilities
│   └── excel_importer.py
├── scripts/           # Utility scripts
│   ├── import_employees.py
│   └── start_server.py
└── config.py          # Configuration
```

### Query Routing Logic

| Query Type | Example | Strategy | AI Needed? | Speed |
|------------|---------|----------|------------|-------|
| Direct Lookup | "john.doe@onenz.co.nz" | Direct DB | ❌ No | ~10ms |
| Simple Search | "billing team" | Pattern Match | ❌ No | ~50ms |
| Complex Intent | "help with BIA provisioning" | AI Understanding | ✅ Yes | ~800ms |
| Conversational | "Thanks!" | AI Response | ✅ Yes | ~600ms |

📖 **See [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) for detailed architecture documentation**

## 🗄️ Database Design

**SQLite** with the following tables:

1. **employees** - Core employee data
2. **employee_skills** - Derived skills (auto-extracted from roles/teams)
3. **role_ownership** - Ownership mapping (primary/backup/escalation)
4. **query_log** - Analytics (session-only, privacy-compliant)
5. **employees_fts** - Full-text search index (FTS5)

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
cd agent_project

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env
# Edit .env to configure AI settings (see Configuration section below)
```

### 2. Import Employee Data

Prepare your Excel file with these columns:
- Formal Name
- Email Address
- People Leader Formal Name
- Position Title
- Function (Label)
- Business Unit (Label)
- Team (Label)
- Location (Name)

```bash
python scripts/import_employees.py path/to/your/employees.xlsx
```

### 3. Start the Server

```bash
python scripts/start_server.py
```

The API will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 4. Configuration (Optional)

The system works out-of-the-box with pattern matching. To enable AI features:

#### Option A: No AI (Default - Fastest)
```bash
# .env
USE_AI_ROUTING=True
ENABLE_LLM=False
```
✅ Best for: Development, testing, or when LLM not needed

#### Option B: OpenAI (Best Quality)
```bash
# .env
USE_AI_ROUTING=True
ENABLE_LLM=True
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-3.5-turbo
```
✅ Best for: Production with budget for API calls

#### Option C: Local LLM (Privacy-First)
```bash
# .env
USE_AI_ROUTING=True
ENABLE_LLM=True
LLM_PROVIDER=local
LOCAL_LLM_ENDPOINT=http://localhost:11434/v1
LOCAL_LLM_MODEL=llama2
```
✅ Best for: Organizations with privacy requirements

📖 **See [AI_ROUTER_SUMMARY.md](AI_ROUTER_SUMMARY.md) for detailed configuration guide**

## 📡 API Endpoints

### Main Query Endpoint

```bash
POST /query
Content-Type: application/json

{
  "query": "I need help setting up a new BIA provisioning workflow",
  "session_id": "optional-session-id"
}
```

### OpenWebUI Integration

```bash
POST /v1/chat/completions
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "Who can help with network provisioning?"}
  ]
}
```

### Other Endpoints

- `GET /health` - Health check and statistics
- `GET /search/employee?email=user@onenz.co.nz` - Direct employee search
- `POST /feedback` - Submit feedback on recommendations
- `GET /analytics/summary` - Usage analytics

## 🔌 OpenWebUI Integration

1. In OpenWebUI, go to **Settings** → **Connections**
2. Add a new connection:
   - **Name**: One NZ Employee Finder
   - **Base URL**: `http://localhost:8000/v1`
   - **Model**: `one-nz-employee-finder`

3. Start chatting! Example queries:
   - "I need help with BIA provisioning"
   - "Who handles network security compliance?"
   - "Find me someone from the billing team"

## 💡 Usage Examples

### Example 1: Finding Provisioning Help

**Query**: "I need help setting up a new BIA provisioning workflow"

**Response**:
```
✅ You're looking for help with bia provisioning. Let me find the right people for this.

📋 Recommended Roles/Teams:
  • Provisioning Specialist
  • Network Engineer
  • Compliance Officer

👥 Recommended Contacts:

1. Jane Doe (Primary Owner)
   📧 jane.doe@onenz.co.nz
   💼 Senior Provisioning Engineer
   👥 Team: Network Provisioning
   🎯 Match: 90% - Primary owner of: bia provisioning
   ⬆️ Escalation: John Smith (john.smith@onenz.co.nz)

...
```

## 🔒 Privacy & Responsible AI

- ✅ **No PII Storage**: Employee data stays in local database
- ✅ **Session-Only Processing**: Query data not retained after session
- ✅ **No External Sharing**: Data never leaves your infrastructure
- ✅ **Transparent Recommendations**: Always shows match reasoning
- ✅ **Confidence Levels**: Clear indication of recommendation quality

## 📈 Analytics

Track usage and impact:

```bash
GET /analytics/summary
```

Returns:
- Total queries processed
- Average time saved
- User satisfaction scores
- Common query patterns

## 🛠️ Configuration

Edit `.env` file:

```env
# Database
DATABASE_PATH=data/employee_directory.db

# API
API_PORT=8000

# Agent
MAX_RECOMMENDATIONS=10
AVERAGE_TIME_SAVED_MINUTES=39.3

# AI & LLM (New in v2.0)
USE_AI_ROUTING=True          # Enable intelligent routing
ENABLE_LLM=False             # Enable LLM for query understanding
LLM_PROVIDER=openai          # "openai" or "local"
OPENAI_API_KEY=              # Your OpenAI API key
LOCAL_LLM_ENDPOINT=http://localhost:11434/v1
```

See [AI_ROUTER_SUMMARY.md](AI_ROUTER_SUMMARY.md) for detailed AI configuration.

## 📚 Documentation

- **[README.md](README.md)** - This file (overview and quick start)
- **[AI_ARCHITECTURE.md](AI_ARCHITECTURE.md)** - Detailed AI router architecture
- **[AI_ROUTER_SUMMARY.md](AI_ROUTER_SUMMARY.md)** - AI routing explained (中文)
- **[USAGE_EXAMPLES.md](USAGE_EXAMPLES.md)** - Query examples and performance
- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide
- **[TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md)** - Technical architecture
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Project overview and impact
- **[IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)** - Deployment checklist

## 🧪 Testing

```bash
# Test the router
python tests/test_router.py

# Test the full agent
python tests/test_agent.py
```

## 📝 License

Internal use only - One NZ

## 👥 Team

Team Rua | Kevin, Zuki, Zoea, Jack, Eden

---

**Version**: 2.0.0 (AI Router Edition)
**Last Updated**: 2026-01-18

