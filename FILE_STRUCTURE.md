# Project File Structure

## Complete File Tree

```
agent_project/
│
├── 📁 database/                    # Database Layer
│   ├── __init__.py                # Package initialization
│   ├── schema.sql                 # SQLite database schema (6 tables)
│   ├── models.py                  # Data models (Employee, Skill, etc.)
│   └── db_manager.py              # Database operations & queries
│
├── 📁 agent/                       # Core Agent Logic
│   ├── __init__.py                # Package initialization
│   └── employee_finder_agent.py   # Main agent implementation
│
├── 📁 api/                         # API Layer
│   ├── __init__.py                # Package initialization
│   └── main.py                    # FastAPI application (8 endpoints)
│
├── 📁 data_import/                 # Data Import Utilities
│   ├── __init__.py                # Package initialization
│   └── excel_importer.py          # Excel import & skill derivation
│
├── 📁 scripts/                     # Utility Scripts
│   ├── __init__.py                # Package initialization
│   ├── import_employees.py        # CLI tool for data import
│   └── start_server.py            # Server startup script
│
├── 📁 tests/                       # Test Suite
│   ├── __init__.py                # Package initialization
│   └── test_agent.py              # Comprehensive tests (6 test cases)
│
├── 📁 data/                        # Data Directory (created at runtime)
│   └── employee_directory.db      # SQLite database (created on first run)
│
├── 📄 config.py                    # Configuration management
├── 📄 requirements.txt             # Python dependencies
├── 📄 .env.example                 # Environment variables template
├── 📄 .gitignore                   # Git ignore rules
│
├── 📖 README.md                    # Main documentation
├── 📖 QUICKSTART.md                # 5-minute setup guide
├── 📖 TECHNICAL_DESIGN.md          # Architecture documentation
├── 📖 PROJECT_SUMMARY.md           # Project overview
└── 📖 FILE_STRUCTURE.md            # This file

```

## File Descriptions

### Core Application Files

| File | Lines | Purpose |
|------|-------|---------|
| `database/schema.sql` | 120 | Database schema with 6 tables + FTS5 |
| `database/models.py` | 120 | Data models (Employee, Skill, Ownership, etc.) |
| `database/db_manager.py` | 270 | Database operations (CRUD, search, analytics) |
| `agent/employee_finder_agent.py` | 380 | Core agent logic (parsing, matching, scoring) |
| `api/main.py` | 370 | FastAPI app with 8 endpoints |
| `data_import/excel_importer.py` | 280 | Excel import + auto-skill derivation |

### Utility Files

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/import_employees.py` | 80 | CLI tool for importing employee data |
| `scripts/start_server.py` | 30 | Server startup script |
| `tests/test_agent.py` | 170 | Test suite (6 comprehensive tests) |
| `config.py` | 35 | Centralized configuration |

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Complete user guide with features, setup, API docs |
| `QUICKSTART.md` | 5-minute quick start guide |
| `TECHNICAL_DESIGN.md` | Detailed architecture and design decisions |
| `PROJECT_SUMMARY.md` | Project overview and impact analysis |
| `FILE_STRUCTURE.md` | This file - project structure reference |

### Configuration Files

| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies (FastAPI, pandas, etc.) |
| `.env.example` | Environment variables template |
| `.gitignore` | Git ignore rules (excludes .venv, *.db, *.xlsx) |

## Key Components by Layer

### 1. Database Layer (3 files)

**Purpose**: Data storage and retrieval

- `schema.sql` - Defines 6 tables:
  - `employees` - Core employee data
  - `employee_skills` - Auto-derived skills
  - `role_ownership` - Ownership mapping
  - `query_log` - Analytics
  - `employees_fts` - Full-text search (FTS5)
  - `query_patterns` - Common query patterns

- `models.py` - Python data classes:
  - `Employee`
  - `EmployeeSkill`
  - `RoleOwnership`
  - `RecommendationResult`
  - `AgentResponse`
  - `QueryLog`

- `db_manager.py` - Database operations:
  - Employee CRUD
  - Skill management
  - Ownership queries
  - Full-text search
  - Analytics

### 2. Agent Layer (1 file)

**Purpose**: Core AI logic

- `employee_finder_agent.py`:
  - Query parsing (extract domains, responsibilities)
  - Role identification (role-before-person)
  - Multi-strategy matching (ownership → skills → keywords)
  - Confidence scoring
  - Response generation
  - Query logging

### 3. API Layer (1 file)

**Purpose**: REST API interface

- `main.py` - 8 endpoints:
  - `POST /query` - Main query endpoint
  - `POST /v1/chat/completions` - OpenWebUI compatible
  - `GET /health` - Health check
  - `POST /feedback` - User feedback
  - `GET /search/employee` - Direct search
  - `GET /analytics/summary` - Usage analytics
  - `GET /` - Root/status
  - Auto-generated `/docs` - Swagger UI

### 4. Data Import Layer (1 file)

**Purpose**: Import employee data from Excel

- `excel_importer.py`:
  - Excel file reading (pandas)
  - Data validation
  - Skill derivation (pattern matching)
  - Ownership derivation
  - People leader resolution

### 5. Scripts (2 files)

**Purpose**: Command-line utilities

- `import_employees.py` - Import data from Excel
- `start_server.py` - Start the API server

### 6. Tests (1 file)

**Purpose**: Quality assurance

- `test_agent.py` - 6 test cases:
  - Database initialization
  - Employee insertion
  - Skill derivation
  - Query parsing
  - Role ownership
  - Full workflow

## Dependencies

From `requirements.txt`:

```
fastapi==0.109.0          # Web framework
uvicorn[standard]==0.27.0 # ASGI server
pydantic==2.5.3           # Data validation
pandas==2.1.4             # Data processing
openpyxl==3.1.2           # Excel reading
python-multipart==0.0.6   # File uploads
python-dotenv==1.0.0      # Environment variables
```

## Runtime Generated Files

These files are created when you run the application:

```
agent_project/
├── 📁 data/
│   └── employee_directory.db    # SQLite database (created on first import)
├── 📁 .venv/                    # Virtual environment (created by user)
└── 📄 .env                      # Environment config (copied from .env.example)
```

## Total Project Stats

- **Total Files**: 25+ files
- **Total Lines of Code**: ~2,000+ lines
- **Languages**: Python, SQL, Markdown
- **External Dependencies**: 7 packages
- **Database Tables**: 6 tables
- **API Endpoints**: 8 endpoints
- **Test Cases**: 6 tests

## File Size Estimates

| Category | Estimated Size |
|----------|---------------|
| Source Code | ~100 KB |
| Documentation | ~50 KB |
| Dependencies (installed) | ~50 MB |
| Database (10K employees) | ~50 MB |
| **Total Project** | ~100 MB |

## Important Paths

### For Development

```bash
# Main application entry point
python scripts/start_server.py

# Data import
python scripts/import_employees.py <excel_file>

# Run tests
python tests/test_agent.py

# API documentation
http://localhost:8000/docs
```

### For Configuration

```bash
# Environment variables
.env

# Application config
config.py

# Database location
data/employee_directory.db
```

## Git Ignored Files

From `.gitignore`:

- `__pycache__/` - Python cache
- `.venv/` - Virtual environment
- `*.db` - Database files
- `*.xlsx` - Excel files (sensitive data)
- `.env` - Environment config
- `.idea/` - IDE files

---

**Note**: This structure is designed for:
- ✅ Easy navigation
- ✅ Clear separation of concerns
- ✅ Scalability
- ✅ Maintainability
- ✅ Testing
- ✅ Documentation

**Last Updated**: 2026-01-18

