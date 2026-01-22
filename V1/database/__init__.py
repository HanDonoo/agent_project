"""Database package for Company Employee Finder Agent"""
from .db_manager import DatabaseManager
from .models import Employee, EmployeeSkill, RoleOwnership, RecommendationResult, AgentResponse

__all__ = [
    'DatabaseManager',
    'Employee',
    'EmployeeSkill',
    'RoleOwnership',
    'RecommendationResult',
    'AgentResponse'
]

