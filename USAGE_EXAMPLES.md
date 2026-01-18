# Usage Examples
## One NZ Employee Finder Agent - Query Examples

This document shows how different types of queries are handled by the system.

---

## 🎯 Query Type Examples

### 1. Direct Email Lookup (No AI Needed)

**Query:**
```
"Find john.doe@onenz.co.nz"
```

**Routing Decision:**
- Type: `DIRECT_LOOKUP`
- Strategy: `direct`
- Confidence: `1.0`
- AI Used: ❌ No

**Response Time:** ~10ms

**Response:**
```json
{
  "understanding": "Found employee with email: john.doe@onenz.co.nz",
  "recommended_roles": ["Senior Network Engineer"],
  "recommendations": [
    {
      "employee": {
        "name": "John Doe",
        "email": "john.doe@onenz.co.nz",
        "position": "Senior Network Engineer",
        "team": "Network Infrastructure"
      },
      "match_score": 1.0,
      "match_reasons": ["Exact email match"],
      "people_leader": {
        "name": "Jane Smith",
        "email": "jane.smith@onenz.co.nz"
      }
    }
  ],
  "confidence_level": "high"
}
```

---

### 2. Simple Team Search (No AI Needed)

**Query:**
```
"Find someone in billing team"
```

**Routing Decision:**
- Type: `SIMPLE_SEARCH`
- Strategy: `pattern`
- Confidence: `0.8`
- AI Used: ❌ No

**Response Time:** ~50ms

**Response:**
```json
{
  "understanding": "Found 8 people matching your search",
  "recommended_roles": [
    "Billing Manager",
    "Billing Specialist",
    "Revenue Analyst"
  ],
  "recommendations": [
    {
      "employee": {
        "name": "Alice Johnson",
        "position": "Billing Manager",
        "team": "Billing Operations"
      },
      "match_score": 0.8,
      "match_reasons": ["Team: Billing Operations"]
    }
    // ... more results
  ],
  "confidence_level": "medium"
}
```

---

### 3. Complex Intent (AI Recommended)

**Query:**
```
"I need help with BIA provisioning for a new enterprise customer"
```

**Routing Decision:**
- Type: `COMPLEX_INTENT`
- Strategy: `ai`
- Confidence: `0.7`
- AI Used: ✅ Yes (if enabled)

**LLM Understanding:**
```json
{
  "intent": "User needs assistance with Business Impact Analysis provisioning for enterprise customer",
  "domains": ["provisioning", "BIA", "enterprise"],
  "requirements": {
    "skills": ["provisioning", "BIA", "enterprise support"]
  },
  "search_strategy": "responsibility"
}
```

**Response Time:** ~800ms (with LLM) or ~100ms (without LLM)

**Response:**
```json
{
  "understanding": "You need help with Business Impact Analysis provisioning for enterprise customers",
  "recommended_roles": [
    "BIA Provisioning Specialist",
    "Enterprise Solutions Architect"
  ],
  "recommendations": [
    {
      "employee": {
        "name": "Bob Wilson",
        "position": "BIA Provisioning Lead",
        "team": "Enterprise Provisioning"
      },
      "match_score": 0.9,
      "match_reasons": [
        "primary owner",
        "Role: BIA Provisioning Lead"
      ],
      "ownership_type": "primary",
      "people_leader": {
        "name": "Carol Davis"
      }
    }
    // ... more results
  ],
  "confidence_level": "high",
  "next_steps": [
    "Contact the primary owner first",
    "If unavailable, try the backup contact",
    "Escalate to people leader if needed"
  ]
}
```

---

### 4. Location-Based Search

**Query:**
```
"Who is in Auckland office?"
```

**Routing Decision:**
- Type: `SIMPLE_SEARCH`
- Strategy: `pattern`
- AI Used: ❌ No

**Response:**
```json
{
  "understanding": "Found 45 people in Auckland office",
  "recommendations": [
    // List of employees in Auckland
  ]
}
```

---

### 5. Role-Based Search

**Query:**
```
"Show me network engineers"
```

**Routing Decision:**
- Type: `SIMPLE_SEARCH`
- Strategy: `pattern`
- AI Used: ❌ No

**Response:**
```json
{
  "understanding": "Found 12 network engineers",
  "recommended_roles": [
    "Senior Network Engineer",
    "Network Engineer",
    "Junior Network Engineer"
  ],
  "recommendations": [
    // List of network engineers
  ]
}
```

---

### 6. Conversational Query (AI Needed)

**Query:**
```
"Thanks for the help!"
```

**Routing Decision:**
- Type: `CONVERSATIONAL`
- Strategy: `ai`
- AI Used: ✅ Yes

**Response:**
```json
{
  "understanding": "You're welcome! Happy to help you find the right people.",
  "recommendations": [],
  "next_steps": [
    "Feel free to ask if you need to find anyone else!"
  ]
}
```

---

### 7. Ambiguous Query (AI Clarification)

**Query:**
```
"Help"
```

**Routing Decision:**
- Type: `AMBIGUOUS`
- Strategy: `ai`
- AI Used: ✅ Yes

**Response:**
```json
{
  "understanding": "I'd be happy to help! What are you looking for?",
  "recommendations": [],
  "next_steps": [
    "Try: 'I need help with [specific task]'",
    "Or: 'Find someone in [team name]'",
    "Or: 'Who handles [responsibility]?'"
  ]
}
```

---

## 🔧 Configuration Impact

### With LLM Enabled (ENABLE_LLM=True)

**Complex Query:**
```
"I need someone who can help with network security compliance"
```

**Result:**
- ✅ LLM understands: domains=["network", "security", "compliance"]
- ✅ Searches by responsibility first
- ✅ Returns primary owners
- ⏱️ Response time: ~800ms
- 🎯 Accuracy: ~95%

---

### Without LLM (ENABLE_LLM=False)

**Same Query:**
```
"I need someone who can help with network security compliance"
```

**Result:**
- ✅ Falls back to full-text search
- ✅ Searches keywords: "network", "security", "compliance"
- ✅ Returns matching employees
- ⏱️ Response time: ~150ms
- 🎯 Accuracy: ~75%

**Trade-off:** Faster but less accurate understanding

---

## 📊 Performance Summary

| Query Type | AI Needed | With LLM | Without LLM |
|------------|-----------|----------|-------------|
| Email lookup | ❌ | 10ms | 10ms |
| Team search | ❌ | 50ms | 50ms |
| Role search | ❌ | 50ms | 50ms |
| Complex intent | ✅ | 800ms | 150ms |
| Conversational | ✅ | 600ms | N/A |
| Ambiguous | ✅ | 600ms | N/A |

---

## 💡 Best Practices

### For Users

1. **Be Specific**
   - ❌ "Help"
   - ✅ "I need help with BIA provisioning"

2. **Use Keywords**
   - ❌ "Find that person"
   - ✅ "Find someone in billing team"

3. **Include Context**
   - ❌ "Network person"
   - ✅ "Network engineer in Auckland who handles security"

### For Administrators

1. **Start Without LLM**
   - Test with `ENABLE_LLM=False` first
   - Verify pattern matching works
   - Add LLM only if needed

2. **Monitor Performance**
   - Check `/analytics/summary` endpoint
   - Track query types and response times
   - Adjust routing thresholds if needed

3. **Choose Right LLM Provider**
   - **OpenAI**: Best quality, costs money
   - **Local**: Free, requires setup
   - **None**: Fastest, less flexible

---

## 🎓 Understanding the Router

The router makes decisions based on patterns:

```python
# Email pattern → Direct lookup
"john.doe@onenz.co.nz" → DIRECT

# Simple patterns → Pattern matching
"find someone in [team]" → SIMPLE_SEARCH
"who is in [location]" → SIMPLE_SEARCH
"show me [role]" → SIMPLE_SEARCH

# Complex patterns → AI (if enabled)
"I need help with [complex task]" → COMPLEX_INTENT
"Who can assist with [multi-word description]" → COMPLEX_INTENT

# Conversational → AI (if enabled)
"thanks", "hello", "bye" → CONVERSATIONAL

# Too short → AI clarification (if enabled)
"help", "find" → AMBIGUOUS
```

---

**Tip:** Use the `/health` endpoint to see system configuration and whether LLM is enabled!

```bash
curl http://localhost:8000/health
```

Response includes:
```json
{
  "status": "healthy",
  "ai_routing_enabled": true,
  "llm_enabled": false,
  "total_employees": 1234
}
```

