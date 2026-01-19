# AI Agent Architecture
## Company Employee Finder - Intelligent Routing System

---

## 🎯 Overview

The system now includes **intelligent routing** that decides when to use AI (LLM) vs direct database queries, optimizing for both **speed** and **accuracy**.

---

## 🏗️ Architecture Layers

```
User Query
    ↓
┌─────────────────────────────────────┐
│  1. ROUTER (Query Classification)   │
│  - Analyzes query complexity        │
│  - Decides: Direct/Pattern/AI       │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  2. STRATEGY EXECUTION              │
│  ┌─────────┬─────────┬───────────┐  │
│  │ Direct  │ Pattern │    AI     │  │
│  │ (Fast)  │ (Fast)  │ (Smart)   │  │
│  └─────────┴─────────┴───────────┘  │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  3. TOOLS (Database Operations)     │
│  - find_by_email()                  │
│  - find_by_team()                   │
│  - find_by_skill()                  │
│  - find_by_responsibility()         │
│  - search_fulltext()                │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  4. RESPONSE GENERATION             │
│  - Format results                   │
│  - Add context & next steps         │
│  - Include confidence level         │
└─────────────────────────────────────┘
    ↓
Response to User
```

---

## 🔀 Router Decision Logic

### Query Type Classification

| Query Type | Example | Strategy | AI Needed? |
|------------|---------|----------|------------|
| **Direct Lookup** | "Find john.doe@sample.com" | Direct DB query | ❌ No |
| **Simple Search** | "Find someone in billing team" | Pattern matching | ❌ No |
| **Complex Intent** | "I need help with BIA provisioning" | AI understanding | ✅ Yes |
| **Conversational** | "Thanks!" or "Can you explain?" | AI response | ✅ Yes |
| **Ambiguous** | "Help" (too vague) | AI clarification | ✅ Yes |

### Decision Flow

```python
def route_query(query):
    # 1. Check for email pattern
    if contains_email(query):
        return DIRECT_LOOKUP  # No AI needed
    
    # 2. Check for conversational patterns
    if is_conversational(query):
        return CONVERSATIONAL  # AI needed
    
    # 3. Check for simple search patterns
    if matches_simple_pattern(query):
        return SIMPLE_SEARCH  # No AI needed
    
    # 4. Check if too short/ambiguous
    if word_count < 3:
        return AMBIGUOUS  # AI needed
    
    # 5. Default to complex intent
    return COMPLEX_INTENT  # AI needed
```

---

## 🛠️ Tools System

Each tool is a discrete function that can be called independently:

### Tool 1: Direct Email Lookup
```python
find_by_email("john.doe@sample.com")
# Returns: Single employee or None
# Speed: ~10ms
```

### Tool 2: Team Search
```python
find_by_team("Network Infrastructure")
# Returns: List of employees in team
# Speed: ~50ms
```

### Tool 3: Role Search
```python
find_by_role("Network Engineer")
# Returns: List of employees with matching role
# Speed: ~50ms
```

### Tool 4: Skill Search
```python
find_by_skill("provisioning", min_confidence=0.6)
# Returns: List of employees with skill
# Speed: ~100ms
```

### Tool 5: Responsibility/Ownership Search
```python
find_by_responsibility("BIA provisioning")
# Returns: Primary owners, then backups
# Speed: ~100ms
```

### Tool 6: Full-Text Search
```python
search_fulltext("network provisioning Auckland")
# Returns: Ranked results using FTS5
# Speed: ~150ms
```

---

## 🤖 LLM Integration

### When LLM is Used

1. **Complex Intent Understanding**
   - Query: "I need help setting up BIA provisioning for a new customer"
   - LLM extracts: domains=["provisioning", "BIA"], requirements={}, strategy="responsibility"

2. **Conversational Responses**
   - Query: "Thanks for the help!"
   - LLM generates: Friendly acknowledgment

3. **Clarification**
   - Query: "Help"
   - LLM asks: "What do you need help with? (e.g., finding someone, understanding a process)"

### LLM Providers Supported

#### Option 1: OpenAI (Cloud)
```bash
# .env configuration
ENABLE_LLM=True
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo
```

**Pros:**
- ✅ High quality understanding
- ✅ Fast response
- ✅ No local setup

**Cons:**
- ❌ Requires API key (costs money)
- ❌ Data sent to external service
- ❌ Requires internet

#### Option 2: Local LLM (Ollama, LocalAI)
```bash
# .env configuration
ENABLE_LLM=True
LLM_PROVIDER=local
LOCAL_LLM_ENDPOINT=http://localhost:11434/v1
LOCAL_LLM_MODEL=llama2
```

**Pros:**
- ✅ Free
- ✅ Privacy (data stays local)
- ✅ Works offline

**Cons:**
- ❌ Requires local setup
- ❌ Slower (depends on hardware)
- ❌ May need GPU for good performance

#### Option 3: No LLM (Pattern Matching Only)
```bash
# .env configuration
ENABLE_LLM=False
USE_AI_ROUTING=True  # Still uses router, but no LLM
```

**Pros:**
- ✅ Fast
- ✅ No external dependencies
- ✅ Predictable

**Cons:**
- ❌ Less flexible
- ❌ Can't handle complex queries as well

---

## 📊 Performance Comparison

| Strategy | Speed | Accuracy | Use Case |
|----------|-------|----------|----------|
| **Direct** | 🚀 10ms | ⭐⭐⭐⭐⭐ 100% | Email lookup |
| **Pattern** | 🚀 50-100ms | ⭐⭐⭐⭐ 80% | Team/role search |
| **AI (Cloud)** | 🐢 500-1000ms | ⭐⭐⭐⭐⭐ 95% | Complex queries |
| **AI (Local)** | 🐌 1000-3000ms | ⭐⭐⭐⭐ 85% | Complex queries |

---

## 🔄 Example Query Flows

### Example 1: Direct Lookup (No AI)
```
User: "Find john.doe@sample.com"
  ↓
Router: DIRECT_LOOKUP (confidence: 1.0)
  ↓
Tool: find_by_email("john.doe@sample.com")
  ↓
Response: [John Doe's info] (10ms)
```

### Example 2: Simple Search (No AI)
```
User: "Find someone in billing team"
  ↓
Router: SIMPLE_SEARCH (confidence: 0.8)
  ↓
Tool: find_by_team("billing")
  ↓
Response: [List of billing team members] (50ms)
```

### Example 3: Complex Intent (With AI)
```
User: "I need help with BIA provisioning"
  ↓
Router: COMPLEX_INTENT (confidence: 0.7)
  ↓
LLM: Extract intent → {domains: ["provisioning", "BIA"], strategy: "responsibility"}
  ↓
Tool: find_by_responsibility("BIA provisioning")
  ↓
Response: [Primary owners, backups, escalation] (800ms)
```

---

## ⚙️ Configuration Options

### Recommended Configurations

#### 1. Production (High Quality)
```bash
USE_AI_ROUTING=True
ENABLE_LLM=True
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-3.5-turbo
```
**Best for:** Production use with budget for API calls

#### 2. Production (Privacy-First)
```bash
USE_AI_ROUTING=True
ENABLE_LLM=True
LLM_PROVIDER=local
LOCAL_LLM_MODEL=llama2
```
**Best for:** Organizations with privacy requirements

#### 3. Development/Testing
```bash
USE_AI_ROUTING=True
ENABLE_LLM=False
```
**Best for:** Development, testing, or when LLM not needed

---

## 🎓 Key Design Decisions

### Why Router?
- **Efficiency**: Don't use expensive AI for simple queries
- **Speed**: Direct queries are 50-100x faster
- **Cost**: Save API costs by routing simple queries to DB
- **Reliability**: Pattern matching is more predictable for simple cases

### Why Support Multiple LLM Providers?
- **Flexibility**: Organizations have different requirements
- **Privacy**: Some need local-only processing
- **Cost**: Some want to avoid API costs
- **Availability**: Some don't have internet access

### Why Make LLM Optional?
- **Gradual Adoption**: Start simple, add AI later
- **Fallback**: System works even if LLM fails
- **Testing**: Easier to test without LLM dependency

---

## 📈 Future Enhancements

- [ ] **Function Calling**: Let LLM decide which tools to call
- [ ] **Multi-turn Conversations**: Remember context across queries
- [ ] **Learning**: Improve routing based on user feedback
- [ ] **Caching**: Cache LLM responses for common queries
- [ ] **Streaming**: Stream LLM responses for better UX

---

**Version**: 2.0.0  
**Last Updated**: 2026-01-18

