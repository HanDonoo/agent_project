"""
Tools for AI Agent to interact with the employee database
These tools can be called by LLM or used directly
"""
from typing import List, Dict, Optional, Any
import json

from database.db_manager import DatabaseManager
from database.models import Employee


class EmployeeSearchTools:
    """
    Collection of tools that the AI agent can use to search for employees
    Each tool is a discrete function that can be called independently
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    # ============================================
    # Tool 1: Direct Email Lookup
    # ============================================
    
    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Find employee by exact email address
        
        Args:
            email: Employee email address
            
        Returns:
            Employee info dict or None
            
        Example:
            find_by_email("john.doe@onenz.co.nz")
        """
        employee = self.db.get_employee_by_email(email)
        if employee:
            return self._employee_to_dict(employee)
        return None
    
    # ============================================
    # Tool 2: Search by Team
    # ============================================
    
    def find_by_team(self, team_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find employees in a specific team
        
        Args:
            team_name: Team name (partial match supported)
            limit: Maximum number of results
            
        Returns:
            List of employee info dicts
            
        Example:
            find_by_team("Network Infrastructure")
        """
        employees = self.db.search_employees_by_criteria(
            team=team_name,
            limit=limit
        )
        return [self._employee_to_dict(emp) for emp in employees]
    
    # ============================================
    # Tool 3: Search by Role/Position
    # ============================================
    
    def find_by_role(self, role_keywords: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find employees by role/position title
        
        Args:
            role_keywords: Keywords in position title
            limit: Maximum number of results
            
        Returns:
            List of employee info dicts
            
        Example:
            find_by_role("Network Engineer")
        """
        employees = self.db.search_employees_by_criteria(
            position_keywords=role_keywords,
            limit=limit
        )
        return [self._employee_to_dict(emp) for emp in employees]
    
    # ============================================
    # Tool 4: Search by Skill
    # ============================================
    
    def find_by_skill(self, skill_name: str, min_confidence: float = 0.5) -> List[Dict[str, Any]]:
        """
        Find employees with a specific skill
        
        Args:
            skill_name: Skill name (e.g., "provisioning", "network")
            min_confidence: Minimum confidence score (0.0-1.0)
            
        Returns:
            List of employee info dicts with skill confidence
            
        Example:
            find_by_skill("provisioning", min_confidence=0.6)
        """
        employees = self.db.get_employees_by_skill(skill_name, min_confidence)
        return [self._employee_to_dict(emp) for emp in employees]
    
    # ============================================
    # Tool 5: Search by Responsibility/Ownership
    # ============================================
    
    def find_by_responsibility(self, responsibility: str) -> List[Dict[str, Any]]:
        """
        Find employees responsible for a specific area
        Returns primary owners first, then backups
        
        Args:
            responsibility: Responsibility area (e.g., "BIA provisioning")
            
        Returns:
            List of dicts with employee info and ownership type
            
        Example:
            find_by_responsibility("network setup")
        """
        owners = self.db.get_owners_by_responsibility(responsibility)
        
        results = []
        for owner_data in owners:
            emp_dict = self._employee_to_dict(owner_data['employee'])
            emp_dict['ownership_type'] = owner_data['ownership_type']
            emp_dict['responsibility_area'] = owner_data['responsibility_area']
            results.append(emp_dict)
        
        return results
    
    # ============================================
    # Tool 6: Full-Text Search
    # ============================================
    
    def search_fulltext(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Full-text search across all employee fields
        Uses SQLite FTS5 for fast searching
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of employee info dicts
            
        Example:
            search_fulltext("network provisioning Auckland")
        """
        employees = self.db.search_employees_fulltext(query, limit)
        return [self._employee_to_dict(emp) for emp in employees]
    
    # ============================================
    # Tool 7: Get Employee with Leader Info
    # ============================================
    
    def get_employee_with_leader(self, employee_id: int) -> Optional[Dict[str, Any]]:
        """
        Get employee info including their people leader
        Useful for escalation paths
        
        Args:
            employee_id: Employee ID
            
        Returns:
            Dict with employee and leader info
            
        Example:
            get_employee_with_leader(123)
        """
        employee = self.db.get_employee_by_id(employee_id)
        if not employee:
            return None
        
        result = self._employee_to_dict(employee)
        
        if employee.people_leader_id:
            leader = self.db.get_employee_by_id(employee.people_leader_id)
            if leader:
                result['people_leader'] = self._employee_to_dict(leader)
        
        return result
    
    # ============================================
    # Helper Methods
    # ============================================
    
    def _employee_to_dict(self, employee: Employee) -> Dict[str, Any]:
        """Convert Employee object to dictionary"""
        return {
            'id': employee.id,
            'name': employee.formal_name,
            'email': employee.email_address,
            'position': employee.position_title,
            'team': employee.team,
            'function': employee.function,
            'business_unit': employee.business_unit,
            'location': employee.location
        }

