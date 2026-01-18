#!/usr/bin/env python
"""Quick test script for the agent"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database.db_manager import DatabaseManager
from agent.ai_agent import EnhancedEmployeeFinderAgent

# Check database
db = DatabaseManager()
with db.get_connection() as conn:
    emp_count = conn.execute("SELECT COUNT(*) as c FROM employees").fetchone()['c']
    skill_count = conn.execute("SELECT COUNT(*) as c FROM employee_skills").fetchone()['c']
    ownership_count = conn.execute("SELECT COUNT(*) as c FROM role_ownership").fetchone()['c']
    
    print(f"📊 Database Stats:")
    print(f"  Employees: {emp_count}")
    print(f"  Skills: {skill_count}")
    print(f"  Ownerships: {ownership_count}")
    
    print(f"\n🎯 Sample Ownerships:")
    rows = conn.execute("SELECT * FROM role_ownership LIMIT 5").fetchall()
    for row in rows:
        print(f"  - {row['responsibility_area']} ({row['ownership_type']})")

# Test agent
print(f"\n🤖 Testing Agent...")
agent = EnhancedEmployeeFinderAgent(db_manager=db, enable_ai=False)

queries = [
    "I need help with BIA provisioning",
    "Who is in the billing team?",
    "emma.wilson@onenz.co.nz",
]

for query in queries:
    print(f"\n📝 Query: {query}")
    response = agent.process_query(query)
    print(f"  Understanding: {response.understanding}")
    print(f"  Recommendations: {len(response.recommendations)}")
    if response.recommendations:
        for i, rec in enumerate(response.recommendations[:2], 1):
            print(f"    {i}. {rec.employee.formal_name} - {rec.employee.position_title} ({rec.match_score}%)")
    else:
        print(f"  Disclaimer: {response.disclaimer}")

