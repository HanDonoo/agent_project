# Implementation Checklist
## One NZ Employee Finder Agent

Use this checklist to verify your implementation and deployment.

---

## ✅ Phase 1: Initial Setup (Day 1)

### Environment Setup
- [ ] Python 3.12+ installed and verified (`python3 --version`)
- [ ] Virtual environment created (`.venv`)
- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created from `.env.example`

### Verification
```bash
# Check Python version
python3 --version  # Should be 3.12+

# Check dependencies
pip list | grep fastapi  # Should show fastapi 0.109.0
pip list | grep pandas   # Should show pandas 2.1.4
```

---

## ✅ Phase 2: Data Preparation (Day 1-2)

### Excel File Preparation
- [ ] Employee data exported from HR system
- [ ] Excel file has required columns:
  - [ ] Formal Name
  - [ ] Email Address
  - [ ] Position Title
- [ ] Excel file has optional columns:
  - [ ] People Leader Formal Name
  - [ ] Function (Label)
  - [ ] Business Unit (Label)
  - [ ] Team (Label)
  - [ ] Location (Name)
- [ ] Data quality checked (no missing emails, valid format)
- [ ] Test with small sample first (10-20 employees)

### Data Import
- [ ] Import script runs successfully
- [ ] No errors in import process
- [ ] Statistics look correct (employees, skills, ownerships)
- [ ] Database file created (`data/employee_directory.db`)

### Verification
```bash
# Import test data
python scripts/import_employees.py test_employees.xlsx

# Check database was created
ls -lh data/employee_directory.db

# Run tests
python tests/test_agent.py
```

---

## ✅ Phase 3: API Testing (Day 2)

### Server Startup
- [ ] Server starts without errors
- [ ] API documentation accessible at `/docs`
- [ ] Health check returns 200 OK
- [ ] Database statistics shown in health check

### API Endpoint Testing
- [ ] `GET /health` - Returns statistics
- [ ] `POST /query` - Returns recommendations
- [ ] `GET /search/employee` - Finds employees
- [ ] `POST /feedback` - Accepts feedback
- [ ] `GET /analytics/summary` - Shows analytics

### Verification
```bash
# Start server
python scripts/start_server.py

# In another terminal, test endpoints:

# Health check
curl http://localhost:8000/health

# Query test
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "I need help with provisioning"}'

# Search test
curl "http://localhost:8000/search/employee?email=test@onenz.co.nz"
```

---

## ✅ Phase 4: OpenWebUI Integration (Day 3)

### OpenWebUI Setup
- [ ] OpenWebUI installed and running
- [ ] Connection added in OpenWebUI settings
- [ ] Base URL configured: `http://localhost:8000/v1`
- [ ] Model name set: `one-nz-employee-finder`
- [ ] Connection test successful

### Chat Testing
- [ ] Can send messages to agent
- [ ] Receives formatted responses
- [ ] Recommendations display correctly
- [ ] Match scores and reasons shown
- [ ] People leaders shown for escalation

### Test Queries
- [ ] "I need help with BIA provisioning"
- [ ] "Who handles network security?"
- [ ] "Find me someone from the billing team"
- [ ] "I need a provisioning specialist in Auckland"
- [ ] Ambiguous query (should ask for clarification)

---

## ✅ Phase 5: Quality Assurance (Day 3-4)

### Functionality Testing
- [ ] Query parsing works correctly
- [ ] Ownership matching prioritized
- [ ] Skill matching works
- [ ] Full-text search works
- [ ] People leader enrichment works
- [ ] Confidence scoring accurate
- [ ] Clarification detection works

### Data Quality
- [ ] All employees searchable
- [ ] Skills derived correctly
- [ ] Ownership assignments make sense
- [ ] People leader relationships correct
- [ ] No duplicate employees

### Performance Testing
- [ ] Query response time <500ms
- [ ] Can handle 10+ concurrent requests
- [ ] Database queries optimized
- [ ] No memory leaks

### Verification
```bash
# Run all tests
python tests/test_agent.py

# Load test (optional)
# Install: pip install locust
# Create locustfile.py and run load tests
```

---

## ✅ Phase 6: User Acceptance Testing (Week 2)

### Pilot Group
- [ ] 5-10 pilot users identified
- [ ] Training session conducted
- [ ] Access provided to pilot users
- [ ] Feedback collection mechanism in place

### Feedback Collection
- [ ] User satisfaction survey created
- [ ] Usage analytics monitored
- [ ] Common queries documented
- [ ] Pain points identified
- [ ] Improvement suggestions collected

### Metrics to Track
- [ ] Number of queries per day
- [ ] Average response time
- [ ] User satisfaction scores (1-5)
- [ ] Time saved per query
- [ ] Clarification rate (% queries needing clarification)

---

## ✅ Phase 7: Production Deployment (Week 3)

### Infrastructure
- [ ] Production server provisioned
- [ ] Database backup strategy in place
- [ ] Monitoring setup (logs, metrics)
- [ ] SSL/TLS configured (if needed)
- [ ] Firewall rules configured

### Security
- [ ] Environment variables secured
- [ ] Database file permissions set
- [ ] API rate limiting configured (optional)
- [ ] CORS origins restricted
- [ ] Logs anonymized (if required)

### Documentation
- [ ] User guide distributed
- [ ] Admin guide created
- [ ] Troubleshooting guide created
- [ ] Contact information for support

### Deployment Checklist
- [ ] Code deployed to production server
- [ ] Dependencies installed
- [ ] Database migrated
- [ ] Environment variables configured
- [ ] Server started and verified
- [ ] Health check passing
- [ ] OpenWebUI connected
- [ ] Pilot users can access

---

## ✅ Phase 8: Rollout & Monitoring (Week 4+)

### Gradual Rollout
- [ ] Week 1: Pilot group (5-10 users)
- [ ] Week 2: Department (50 users)
- [ ] Week 3: Division (200 users)
- [ ] Week 4+: Full organization

### Ongoing Monitoring
- [ ] Daily health checks
- [ ] Weekly usage reports
- [ ] Monthly feedback review
- [ ] Quarterly data refresh

### Maintenance Tasks
- [ ] Weekly: Review query logs
- [ ] Monthly: Update employee data
- [ ] Quarterly: Analyze usage patterns
- [ ] Annually: Review skill patterns and ownership

---

## 🚨 Troubleshooting Checklist

### Server Won't Start
- [ ] Check Python version
- [ ] Check dependencies installed
- [ ] Check port 8000 not in use
- [ ] Check `.env` file exists
- [ ] Check database file accessible

### No Results Returned
- [ ] Check database has data (`/health` endpoint)
- [ ] Check query is clear enough
- [ ] Check employee data imported correctly
- [ ] Check logs for errors

### Poor Match Quality
- [ ] Review skill derivation patterns
- [ ] Review ownership assignments
- [ ] Check employee data quality
- [ ] Adjust confidence thresholds

### Performance Issues
- [ ] Check database size
- [ ] Check query complexity
- [ ] Check server resources
- [ ] Consider adding indexes
- [ ] Consider caching

---

## 📊 Success Metrics

Track these metrics to measure success:

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Adoption Rate | >80% of team | User count from analytics |
| Time Saved | >30 min/week/user | Survey + analytics |
| User Satisfaction | >4.0/5.0 | Feedback scores |
| Query Success Rate | >90% | Queries with results |
| Response Time | <500ms | API metrics |
| Missed Opportunities | <5% | User survey |

---

## 📝 Sign-off

### Phase Completion

- [ ] Phase 1: Setup - Completed by: __________ Date: __________
- [ ] Phase 2: Data Import - Completed by: __________ Date: __________
- [ ] Phase 3: API Testing - Completed by: __________ Date: __________
- [ ] Phase 4: OpenWebUI - Completed by: __________ Date: __________
- [ ] Phase 5: QA - Completed by: __________ Date: __________
- [ ] Phase 6: UAT - Completed by: __________ Date: __________
- [ ] Phase 7: Deployment - Completed by: __________ Date: __________
- [ ] Phase 8: Rollout - Completed by: __________ Date: __________

### Final Sign-off

- [ ] Technical Lead: __________ Date: __________
- [ ] Product Owner: __________ Date: __________
- [ ] Stakeholder: __________ Date: __________

---

**Good luck with your implementation! 🚀**

Team Rua | Kevin, Zuki, Zoea, Jack, Eden

