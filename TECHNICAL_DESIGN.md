# Technical Design Document
## Company Employee Finder Agent

---

## 1. Executive Summary

This document outlines the technical architecture and design decisions for the Company Employee Finder Agent, an AI-powered system designed to help employees quickly find the right people across the organization.

### Key Design Principles (Based on Survey Insights)

1. **Ownership-First**: Prioritize finding people who are responsible for tasks
2. **Role-Before-Person**: Show roles/teams before individual names
3. **Time-Saving Focus**: Reduce search time from 39.3 min/week to <1 minute
4. **Privacy-Compliant**: No PII storage beyond session
5. **Transparent**: Always explain recommendations

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────┐
│   OpenWebUI     │  (Frontend - User Interface)
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│   FastAPI       │  (API Layer)
│   /v1/chat      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Employee Finder │  (Agent Logic)
│     Agent       │  - Query Parsing
│                 │  - Matching Algorithm
│                 │  - Recommendation Engine
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SQLite + FTS5  │  (Database)
│  - Employees    │
│  - Skills       │
│  - Ownership    │
└─────────────────┘
```

### 2.2 Component Breakdown

#### A. Database Layer (`database/`)

**Technology**: SQLite with FTS5 (Full-Text Search)

**Why SQLite?**
- File-based (no server needed)
- Built-in Python support
- FTS5 for fast full-text search
- Suitable for 1K-100K employees
- Easy backup and migration

**Tables**:

1. **employees** - Core employee data
   - Stores: name, email, position, team, function, location
   - Indexed on: email, team, function, business_unit

2. **employee_skills** - Derived skills
   - Auto-extracted from position titles and teams
   - Confidence scoring (0.0-1.0)
   - Source tracking (position_title, team, function)

3. **role_ownership** - Ownership mapping
   - Maps employees to responsibility areas
   - Types: primary, backup, escalation
   - **Critical for survey insight**: "find who's responsible"

4. **query_log** - Analytics
   - Session-based logging
   - No PII retention
   - Used for improvement and metrics

5. **employees_fts** - Full-text search index
   - FTS5 virtual table
   - Auto-synced with employees table via triggers

#### B. Agent Layer (`agent/`)

**Core Algorithm**:

```python
def process_query(query):
    # 1. Parse query → extract domains, responsibilities, keywords
    parsed = parse_query(query)
    
    # 2. Identify roles FIRST (survey insight)
    roles = identify_roles(parsed)
    
    # 3. Find matching employees
    #    Priority: Ownership > Skills > Team/Function > Keywords
    candidates = find_matching_employees(parsed)
    
    # 4. Enrich with people leaders (for escalation)
    candidates = enrich_with_leaders(candidates)
    
    # 5. Calculate confidence and generate response
    return create_response(roles, candidates)
```

**Matching Strategy** (Priority Order):

1. **Ownership Match** (Score: 0.9 for primary, 0.7 for backup)
   - Searches `role_ownership` table
   - Example: "BIA provisioning" → finds primary owner

2. **Skill Match** (Score: 0.6)
   - Searches `employee_skills` table
   - Uses derived skills from position/team

3. **Full-Text Search** (Score: 0.4)
   - Uses FTS5 for keyword matching
   - Searches across all employee fields

4. **Team/Function Match** (Score: 0.5)
   - Direct team or function matching

#### C. API Layer (`api/`)

**Technology**: FastAPI

**Key Endpoints**:

1. `POST /query` - Main query endpoint
2. `POST /v1/chat/completions` - OpenWebUI compatible
3. `GET /health` - Health check
4. `POST /feedback` - User feedback
5. `GET /analytics/summary` - Usage metrics

**OpenWebUI Integration**:
- Implements OpenAI-compatible chat completions API
- Returns formatted markdown responses
- Supports streaming (future enhancement)

#### D. Data Import Layer (`data_import/`)

**Excel Import Process**:

```
Excel File
    ↓
1. Read & Validate Columns
    ↓
2. Import Employees (Pass 1)
    ↓
3. Resolve People Leader FKs (Pass 2)
    ↓
4. Derive Skills (Pass 3)
    ↓
5. Derive Ownership (Pass 4)
    ↓
Database Ready
```

**Skill Derivation**:
- Pattern matching on position titles
- Example: "Provisioning Engineer" → skills: [provisioning, engineering]
- Confidence based on source (function > team > position)

**Ownership Derivation**:
- Pattern matching for responsibility areas
- Example: "Senior BIA Provisioning Lead" → primary owner of "bia provisioning"

---

## 3. Key Design Decisions

### 3.1 Why Not Use a Vector Database?

**Decision**: Use SQLite with FTS5 instead of vector embeddings

**Reasoning**:
- Employee data is structured (not unstructured text)
- Exact matching is more important than semantic similarity
- FTS5 is faster for exact keyword matching
- Simpler deployment (no external dependencies)
- Can add vector search later if needed

### 3.2 Why Derive Skills Instead of Self-Reporting?

**Decision**: Auto-derive skills from position/team/function

**Reasoning** (from survey):
- Self-reported skills are often outdated
- People rely on "asking colleagues" (97%)
- Position titles are more reliable
- Reduces maintenance burden

### 3.3 Why Show Roles Before People?

**Decision**: Two-stage output (roles → people)

**Reasoning** (from survey):
- IT/Technology is hardest to navigate (44.4%)
- High personnel turnover
- Users want to know "what role" before "which person"
- Reduces "finding wrong person" anxiety

### 3.4 Why Include People Leaders?

**Decision**: Always show people leader for escalation

**Reasoning** (from survey):
- 66.7% experience delays
- Need backup/escalation path
- Ownership clarity is critical

---

## 4. Privacy & Responsible AI

### 4.1 Data Privacy

**Principles**:
1. ✅ No PII leaves the system
2. ✅ Session-only query processing
3. ✅ No data sent to external APIs
4. ✅ Local database only

**Implementation**:
- SQLite database stored locally
- No cloud services
- Query logs are anonymized (optional)
- Session IDs are temporary

### 4.2 Transparency

**Every recommendation includes**:
- Match score (0-100%)
- Match reasons (why this person?)
- Ownership type (primary/backup/escalation)
- Confidence level (high/medium/low)
- Disclaimer about recommendation quality

### 4.3 Bias Mitigation

**Strategies**:
- Objective matching (no subjective ratings)
- Ownership-based (not popularity-based)
- Transparent scoring
- No historical bias (fresh matching each time)

---

## 5. Performance Considerations

### 5.1 Expected Performance

| Metric | Target | Notes |
|--------|--------|-------|
| Query Response Time | <500ms | For 10K employees |
| Database Size | ~50MB | For 10K employees |
| Concurrent Users | 100+ | FastAPI async support |
| FTS5 Search | <100ms | Full-text search |

### 5.2 Scalability

**Current Capacity**: 1K - 100K employees

**If scaling beyond 100K**:
- Consider PostgreSQL with pg_trgm
- Add caching layer (Redis)
- Implement search result pagination

---

## 6. Future Enhancements

### Phase 2 (Potential)
- [ ] Microsoft Teams bot integration
- [ ] Auto-create Teams groups
- [ ] Meeting scheduling integration
- [ ] Skill endorsements (LinkedIn-style)
- [ ] Project history tracking

### Phase 3 (Advanced)
- [ ] Vector embeddings for semantic search
- [ ] LLM integration for query understanding
- [ ] Multi-language support
- [ ] Mobile app

---

## 7. Deployment Architecture

### Development
```
Local Machine
├── SQLite DB (file)
├── FastAPI (localhost:8000)
└── OpenWebUI (localhost:3000)
```

### Production (Recommended)
```
Internal Server
├── SQLite DB (file) or PostgreSQL
├── FastAPI (Gunicorn/Uvicorn)
├── Nginx (reverse proxy)
└── OpenWebUI (Docker)
```

---

## 8. Monitoring & Analytics

### Key Metrics to Track

1. **Usage Metrics**
   - Total queries per day/week
   - Unique users
   - Peak usage times

2. **Quality Metrics**
   - Average confidence score
   - Feedback ratings (1-5)
   - Clarification rate (% queries needing clarification)

3. **Impact Metrics**
   - Total time saved (hours)
   - Missed opportunities prevented
   - Cross-team connections made

---

## 9. Testing Strategy

### Unit Tests
- Database operations
- Skill derivation logic
- Query parsing
- Matching algorithm

### Integration Tests
- API endpoints
- End-to-end query flow
- Excel import process

### User Acceptance Testing
- Real employee queries
- Feedback collection
- Iterative improvement

---

## 10. Maintenance

### Regular Tasks
- [ ] Weekly: Review query logs for improvement
- [ ] Monthly: Update employee data from HR system
- [ ] Quarterly: Analyze usage patterns
- [ ] Annually: Review and update skill patterns

### Data Updates
- Employee data: Import from HR Excel export
- Skills: Auto-derived on import
- Ownership: Review quarterly with team leads

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-18  
**Authors**: Team Rua

