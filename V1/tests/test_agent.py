"""
Basic tests for the Employee Finder Agent
Run with: pytest tests/test_agent.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import DatabaseManager
from database.models import Employee, EmployeeSkill, RoleOwnership
from agent.employee_finder_agent import EmployeeFinderAgent


def test_database_initialization():
    """Test database initialization"""
    db = DatabaseManager(db_path=":memory:")  # In-memory database for testing
    stats = db.get_statistics()
    
    assert stats['total_employees'] == 0
    assert stats['total_teams'] == 0
    print("✅ Database initialization test passed")


def test_employee_insertion():
    """Test employee insertion and retrieval"""
    db = DatabaseManager(db_path=":memory:")
    
    # Create test employee
    employee = Employee(
        formal_name="John Doe",
        email_address="john.doe@sample.com",
        position_title="Senior Network Engineer",
        function="Technology",
        business_unit="IT",
        team="Network Infrastructure",
        location="Auckland"
    )
    
    # Insert
    emp_id = db.insert_employee(employee)
    assert emp_id > 0
    
    # Retrieve
    retrieved = db.get_employee_by_email("john.doe@sample.com")
    assert retrieved is not None
    assert retrieved.formal_name == "John Doe"
    assert retrieved.position_title == "Senior Network Engineer"
    
    print("✅ Employee insertion test passed")


def test_skill_derivation():
    """Test skill derivation from position title"""
    db = DatabaseManager(db_path=":memory:")
    
    # Create employee with network-related position
    employee = Employee(
        formal_name="Jane Smith",
        email_address="jane.smith@sample.com",
        position_title="Provisioning Specialist",
        team="Network Provisioning",
        function="Technology"
    )
    
    emp_id = db.insert_employee(employee)
    
    # Add skill
    skill = EmployeeSkill(
        employee_id=emp_id,
        skill_name="provisioning",
        skill_category="Technical",
        confidence_score=0.8,
        source="position_title"
    )
    
    db.insert_skill(skill)
    
    # Search by skill
    employees = db.get_employees_by_skill("provisioning")
    assert len(employees) > 0
    assert employees[0].email_address == "jane.smith@sample.com"
    
    print("✅ Skill derivation test passed")


def test_agent_query_parsing():
    """Test agent query parsing"""
    db = DatabaseManager(db_path=":memory:")
    agent = EmployeeFinderAgent(db)
    
    # Test query parsing
    parsed = agent._parse_query("I need help with BIA provisioning setup")
    
    assert 'provisioning' in parsed['domains']
    assert len(parsed['keywords']) > 0
    
    print("✅ Agent query parsing test passed")


def test_role_ownership():
    """Test role ownership functionality"""
    db = DatabaseManager(db_path=":memory:")
    
    # Create employee
    employee = Employee(
        formal_name="Alice Johnson",
        email_address="alice.johnson@sample.com",
        position_title="BIA Provisioning Lead",
        team="Provisioning"
    )
    
    emp_id = db.insert_employee(employee)
    
    # Add ownership
    ownership = RoleOwnership(
        employee_id=emp_id,
        responsibility_area="bia provisioning",
        ownership_type="primary",
        team="Provisioning"
    )
    
    db.insert_role_ownership(ownership)
    
    # Search by responsibility
    owners = db.get_owners_by_responsibility("bia provisioning")
    assert len(owners) > 0
    assert owners[0]['ownership_type'] == 'primary'
    
    print("✅ Role ownership test passed")


def test_full_agent_workflow():
    """Test complete agent workflow"""
    db = DatabaseManager(db_path=":memory:")
    agent = EmployeeFinderAgent(db)
    
    # Create test employees
    emp1 = Employee(
        formal_name="Bob Wilson",
        email_address="bob.wilson@sample.com",
        position_title="Network Provisioning Engineer",
        team="Network Operations",
        function="Technology"
    )
    
    emp_id = db.insert_employee(emp1)
    
    # Add ownership
    ownership = RoleOwnership(
        employee_id=emp_id,
        responsibility_area="network setup",
        ownership_type="primary"
    )
    db.insert_role_ownership(ownership)
    
    # Process query
    response = agent.process_query("I need help with network setup")
    
    assert response is not None
    assert len(response.understanding) > 0
    assert response.confidence_level in ['high', 'medium', 'low']
    
    print("✅ Full agent workflow test passed")


if __name__ == "__main__":
    print("Running Company Employee Finder Agent Tests\n")
    print("=" * 60)
    
    test_database_initialization()
    test_employee_insertion()
    test_skill_derivation()
    test_agent_query_parsing()
    test_role_ownership()
    test_full_agent_workflow()
    
    print("=" * 60)
    print("\n✅ All tests passed!")

