# Quick Start Guide
## One NZ Employee Finder Agent

Get up and running in 5 minutes! ⚡

---

## Prerequisites

- Python 3.12+ installed
- Your employee data in Excel format
- Terminal/Command Prompt access

---

## Step 1: Setup Environment (2 minutes)

```bash
# Navigate to project directory
cd agent_project

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Prepare Your Data (1 minute)

Your Excel file should have these columns (exact names):

| Column Name | Required | Example |
|-------------|----------|---------|
| Formal Name | ✅ Yes | John Smith |
| Email Address | ✅ Yes | john.smith@onenz.co.nz |
| Position Title | ✅ Yes | Senior Network Engineer |
| People Leader Formal Name | ⚪ Optional | Jane Doe |
| Function (Label) | ⚪ Optional | Technology |
| Business Unit (Label) | ⚪ Optional | IT |
| Team (Label) | ⚪ Optional | Network Infrastructure |
| Location (Name) | ⚪ Optional | Auckland |

**Sample Data** (create `sample_employees.xlsx`):

```
Formal Name              | Email Address              | Position Title                | Team
-------------------------|----------------------------|-------------------------------|------------------
Alice Johnson            | alice.j@onenz.co.nz       | BIA Provisioning Lead         | Provisioning
Bob Wilson               | bob.w@onenz.co.nz         | Network Engineer              | Network Ops
Carol Davis              | carol.d@onenz.co.nz       | Security Compliance Officer   | Security
David Chen               | david.c@onenz.co.nz       | Customer Support Lead         | Support
Emma Thompson            | emma.t@onenz.co.nz        | Sales Engineer                | Sales
```

---

## Step 3: Import Employee Data (1 minute)

```bash
# Import your Excel file
python scripts/import_employees.py path/to/your/employees.xlsx

# You should see output like:
# ============================================================
# One NZ Employee Directory - Data Import
# ============================================================
# Importing from: employees.xlsx
# First pass: Importing employees...
# Imported 100/100 employees
# Second pass: Updating people leader relationships...
# Third pass: Deriving skills...
# Deriving role ownerships...
# ============================================================
# Import Summary:
#   Total rows processed: 100
#   Employees imported: 100
#   Skills derived: 250
#   Ownerships derived: 75
#   Errors: 0
# ============================================================
# ✅ Import completed successfully!
```

---

## Step 4: Start the Server (30 seconds)

```bash
# Start the API server
python scripts/start_server.py

# You should see:
# ============================================================
# One NZ Employee Finder Agent
# ============================================================
# Starting server on http://0.0.0.0:8000
# API Documentation: http://0.0.0.0:8000/docs
# Health Check: http://0.0.0.0:8000/health
# ============================================================
```

---

## Step 5: Test It! (30 seconds)

### Option A: Using the API Documentation (Easiest)

1. Open browser: http://localhost:8000/docs
2. Click on `POST /query`
3. Click "Try it out"
4. Enter test query:
   ```json
   {
     "query": "I need help with network provisioning"
   }
   ```
5. Click "Execute"
6. See the results! 🎉

### Option B: Using curl

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I need help with BIA provisioning"
  }'
```

### Option C: Using Python

```python
import requests

response = requests.post(
    "http://localhost:8000/query",
    json={"query": "Who can help with network security?"}
)

print(response.json())
```

---

## Step 6: Integrate with OpenWebUI (Optional)

If you're using OpenWebUI:

1. Open OpenWebUI settings
2. Go to **Connections** → **Add Connection**
3. Configure:
   - **Name**: One NZ Employee Finder
   - **Base URL**: `http://localhost:8000/v1`
   - **Model**: `one-nz-employee-finder`
4. Save and start chatting!

**Example queries in OpenWebUI**:
- "I need help setting up BIA provisioning"
- "Who handles network security compliance?"
- "Find me someone from the billing team"
- "I need a provisioning specialist in Auckland"

---

## Common Issues & Solutions

### Issue: "Module not found" error

**Solution**: Make sure virtual environment is activated
```bash
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

### Issue: "File not found" when importing Excel

**Solution**: Use absolute path or check file location
```bash
python scripts/import_employees.py /full/path/to/employees.xlsx
```

### Issue: Port 8000 already in use

**Solution**: Change port in `.env` file
```env
API_PORT=8001
```

### Issue: No results returned

**Solution**: Check if data was imported successfully
```bash
# Check database statistics
curl http://localhost:8000/health
```

---

## Next Steps

✅ **You're all set!** Here's what to do next:

1. **Import your real employee data**
   ```bash
   python scripts/import_employees.py your_real_data.xlsx
   ```

2. **Test with real queries**
   - Try queries your team would actually ask
   - Collect feedback

3. **Monitor usage**
   ```bash
   curl http://localhost:8000/analytics/summary
   ```

4. **Customize**
   - Edit `.env` for configuration
   - Adjust skill patterns in `data_import/excel_importer.py`
   - Modify response format in `api/main.py`

---

## Useful Commands

```bash
# Check health
curl http://localhost:8000/health

# Search for specific employee
curl "http://localhost:8000/search/employee?email=john@onenz.co.nz"

# Get analytics
curl http://localhost:8000/analytics/summary

# Run tests
python tests/test_agent.py

# Stop server
# Press CTRL+C in the terminal running the server
```

---

## Getting Help

- 📖 Read the full [README.md](README.md)
- 🔧 Check [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) for architecture details
- 🐛 Found a bug? Check the logs in the terminal
- 💡 Need features? Document your requirements

---

**Happy Finding! 🚀**

Team Rua | Kevin, Zuki, Zoea, Jack, Eden

