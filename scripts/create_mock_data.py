"""
Create mock employee data for testing
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import DatabaseManager
from database.models import Employee, EmployeeSkill, RoleOwnership
import random


def create_mock_data():
    """Create mock employee data for testing"""

    print("🔧 Creating mock employee data...")

    db = DatabaseManager()

    # Clear existing data
    print("🗑️  Clearing existing data...")
    with db.get_connection() as conn:
        conn.execute("DELETE FROM query_log")
        conn.execute("DELETE FROM role_ownership")
        conn.execute("DELETE FROM employee_skills")
        conn.execute("DELETE FROM employees")
        conn.commit()
    print("  ✅ Database cleared")
    
    # Mock data
    teams = [
        "Network Infrastructure",
        "Billing Operations",
        "Provisioning Services",
        "Customer Support",
        "Security & Compliance",
        "Data Analytics",
        "Product Management",
        "Engineering",
        "Sales",
        "IT Operations"
    ]
    
    functions = [
        "Technology",
        "Finance",
        "Operations",
        "Customer Service",
        "Product",
        "Sales & Marketing"
    ]
    
    locations = [
        "Auckland",
        "Wellington",
        "Christchurch",
        "Hamilton",
        "Remote"
    ]
    
    # Create employees
    employees_data = [
        # Network Team
        {
            "name": "John Smith",
            "email": "john.smith@sample.com",
            "position": "Senior Network Engineer",
            "team": "Network Infrastructure",
            "function": "Technology",
            "business_unit": "Technology Services",
            "location": "Auckland",
            "is_leader": True
        },
        {
            "name": "Sarah Johnson",
            "email": "sarah.johnson@sample.com",
            "position": "Network Security Specialist",
            "team": "Network Infrastructure",
            "function": "Technology",
            "business_unit": "Technology Services",
            "location": "Auckland",
            "leader_email": "john.smith@sample.com"
        },
        {
            "name": "Mike Chen",
            "email": "mike.chen@sample.com",
            "position": "Network Engineer",
            "team": "Network Infrastructure",
            "function": "Technology",
            "business_unit": "Technology Services",
            "location": "Wellington",
            "leader_email": "john.smith@sample.com"
        },
        
        # Provisioning Team
        {
            "name": "Emma Wilson",
            "email": "emma.wilson@sample.com",
            "position": "BIA Provisioning Lead",
            "team": "Provisioning Services",
            "function": "Operations",
            "business_unit": "Service Delivery",
            "location": "Auckland",
            "is_leader": True
        },
        {
            "name": "David Brown",
            "email": "david.brown@sample.com",
            "position": "Provisioning Specialist",
            "team": "Provisioning Services",
            "function": "Operations",
            "business_unit": "Service Delivery",
            "location": "Auckland",
            "leader_email": "emma.wilson@sample.com"
        },
        {
            "name": "Lisa Taylor",
            "email": "lisa.taylor@sample.com",
            "position": "Enterprise Provisioning Engineer",
            "team": "Provisioning Services",
            "function": "Operations",
            "business_unit": "Service Delivery",
            "location": "Wellington",
            "leader_email": "emma.wilson@sample.com"
        },
        
        # Billing Team
        {
            "name": "Robert Davis",
            "email": "robert.davis@sample.com",
            "position": "Billing Manager",
            "team": "Billing Operations",
            "function": "Finance",
            "business_unit": "Finance & Billing",
            "location": "Auckland",
            "is_leader": True
        },
        {
            "name": "Jennifer Lee",
            "email": "jennifer.lee@sample.com",
            "position": "Billing Specialist",
            "team": "Billing Operations",
            "function": "Finance",
            "business_unit": "Finance & Billing",
            "location": "Auckland",
            "leader_email": "robert.davis@sample.com"
        },
        {
            "name": "Tom Anderson",
            "email": "tom.anderson@sample.com",
            "position": "Revenue Analyst",
            "team": "Billing Operations",
            "function": "Finance",
            "business_unit": "Finance & Billing",
            "location": "Christchurch",
            "leader_email": "robert.davis@sample.com"
        },
        
        # Security Team
        {
            "name": "Alice Martinez",
            "email": "alice.martinez@sample.com",
            "position": "Security Compliance Manager",
            "team": "Security & Compliance",
            "function": "Technology",
            "business_unit": "Risk & Compliance",
            "location": "Auckland",
            "is_leader": True
        },
        {
            "name": "Chris Wong",
            "email": "chris.wong@sample.com",
            "position": "Security Analyst",
            "team": "Security & Compliance",
            "function": "Technology",
            "business_unit": "Risk & Compliance",
            "location": "Wellington",
            "leader_email": "alice.martinez@sample.com"
        },
        
        # Customer Support
        {
            "name": "Maria Garcia",
            "email": "maria.garcia@sample.com",
            "position": "Customer Support Lead",
            "team": "Customer Support",
            "function": "Customer Service",
            "business_unit": "Customer Experience",
            "location": "Auckland",
            "is_leader": True
        },
        {
            "name": "James Wilson",
            "email": "james.wilson@sample.com",
            "position": "Support Specialist",
            "team": "Customer Support",
            "function": "Customer Service",
            "business_unit": "Customer Experience",
            "location": "Hamilton",
            "leader_email": "maria.garcia@sample.com"
        },
    ]
    
    print(f"\n📝 Creating {len(employees_data)} employees...")
    
    # First pass: Create all employees
    employee_map = {}
    for emp_data in employees_data:
        employee = Employee(
            formal_name=emp_data["name"],
            email_address=emp_data["email"],
            position_title=emp_data["position"],
            team=emp_data["team"],
            function=emp_data["function"],
            business_unit=emp_data["business_unit"],
            location=emp_data["location"]
        )
        emp_id = db.insert_employee(employee)
        employee_map[emp_data["email"]] = emp_id
        print(f"  ✅ Created: {emp_data['name']} ({emp_data['position']})")
    
    # Second pass: Update people leaders
    print(f"\n👥 Setting up people leader relationships...")
    for emp_data in employees_data:
        if "leader_email" in emp_data:
            emp_id = employee_map[emp_data["email"]]
            leader_id = employee_map[emp_data["leader_email"]]
            db.update_employee_leader(emp_id, leader_id)
            print(f"  ✅ {emp_data['name']} → reports to → {emp_data['leader_email']}")
    
    print(f"\n🎯 Deriving skills from positions and teams...")
    # The database manager should auto-derive skills, but let's add some manually too
    skills_data = [
        (employee_map["john.smith@sample.com"], "network", "technical", 0.9, "position_title"),
        (employee_map["john.smith@sample.com"], "infrastructure", "technical", 0.8, "team"),
        (employee_map["sarah.johnson@sample.com"], "security", "technical", 0.9, "position_title"),
        (employee_map["sarah.johnson@sample.com"], "network", "technical", 0.8, "team"),
        (employee_map["emma.wilson@sample.com"], "provisioning", "technical", 0.9, "position_title"),
        (employee_map["emma.wilson@sample.com"], "BIA", "technical", 0.9, "position_title"),
        (employee_map["david.brown@sample.com"], "provisioning", "technical", 0.8, "position_title"),
        (employee_map["lisa.taylor@sample.com"], "provisioning", "technical", 0.8, "position_title"),
        (employee_map["lisa.taylor@sample.com"], "enterprise", "business", 0.7, "position_title"),
        (employee_map["robert.davis@sample.com"], "billing", "business", 0.9, "position_title"),
        (employee_map["jennifer.lee@sample.com"], "billing", "business", 0.8, "position_title"),
        (employee_map["alice.martinez@sample.com"], "security", "technical", 0.9, "position_title"),
        (employee_map["alice.martinez@sample.com"], "compliance", "business", 0.9, "position_title"),
    ]

    for emp_id, skill_name, skill_category, confidence, source in skills_data:
        skill = EmployeeSkill(
            employee_id=emp_id,
            skill_name=skill_name,
            skill_category=skill_category,
            confidence_score=confidence,
            source=source
        )
        db.insert_skill(skill)

    print(f"  ✅ Added {len(skills_data)} skills")

    print(f"\n🎯 Creating role ownership assignments...")
    # Add ownership data
    ownership_data = [
        (employee_map["emma.wilson@sample.com"], "BIA provisioning", "primary", "Provisioning Services"),
        (employee_map["david.brown@sample.com"], "BIA provisioning", "backup", "Provisioning Services"),
        (employee_map["lisa.taylor@sample.com"], "enterprise provisioning", "primary", "Provisioning Services"),
        (employee_map["john.smith@sample.com"], "network infrastructure", "primary", "Network Infrastructure"),
        (employee_map["sarah.johnson@sample.com"], "network security", "primary", "Network Infrastructure"),
        (employee_map["mike.chen@sample.com"], "network infrastructure", "backup", "Network Infrastructure"),
        (employee_map["robert.davis@sample.com"], "billing operations", "primary", "Billing Operations"),
        (employee_map["jennifer.lee@sample.com"], "billing operations", "backup", "Billing Operations"),
        (employee_map["alice.martinez@sample.com"], "security compliance", "primary", "Security & Compliance"),
        (employee_map["chris.wong@sample.com"], "security compliance", "backup", "Security & Compliance"),
        (employee_map["maria.garcia@sample.com"], "customer support", "primary", "Customer Support"),
    ]

    for emp_id, responsibility, ownership_type, team in ownership_data:
        ownership = RoleOwnership(
            employee_id=emp_id,
            responsibility_area=responsibility,
            ownership_type=ownership_type,
            team=team
        )
        db.insert_role_ownership(ownership)

    print(f"  ✅ Added {len(ownership_data)} ownership assignments")

    # Print summary
    print("\n" + "="*60)
    print("📊 Mock Data Summary")
    print("="*60)

    with db.get_connection() as conn:
        emp_count = conn.execute("SELECT COUNT(*) as c FROM employees").fetchone()['c']
        skill_count = conn.execute("SELECT COUNT(*) as c FROM employee_skills").fetchone()['c']
        ownership_count = conn.execute("SELECT COUNT(*) as c FROM role_ownership").fetchone()['c']

    print(f"Total Employees: {emp_count}")
    print(f"Total Skills: {skill_count}")
    print(f"Total Ownerships: {ownership_count}")

    print("\n✅ Mock data created successfully!")
    print("\n💡 You can now:")
    print("   1. Start the server: python scripts/start_server.py")
    print("   2. Test queries: curl -X POST http://localhost:8000/query \\")
    print("      -H 'Content-Type: application/json' \\")
    print("      -d '{\"query\": \"I need help with BIA provisioning\"}'")
    print("   3. Check health: curl http://localhost:8000/health")

    return True


if __name__ == "__main__":
    try:
        create_mock_data()
    except Exception as e:
        print(f"\n❌ Error creating mock data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


