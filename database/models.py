"""
Data models for One NZ Employee Directory Agent
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class Employee:
    """Employee data model matching Excel structure"""
    formal_name: str
    email_address: str
    position_title: str
    function: Optional[str] = None
    business_unit: Optional[str] = None
    team: Optional[str] = None
    location: Optional[str] = None
    people_leader_name: Optional[str] = None  # From Excel
    people_leader_id: Optional[int] = None  # Resolved FK
    is_active: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'formal_name': self.formal_name,
            'email_address': self.email_address,
            'position_title': self.position_title,
            'function': self.function,
            'business_unit': self.business_unit,
            'team': self.team,
            'location': self.location,
            'people_leader_id': self.people_leader_id,
            'is_active': self.is_active
        }


@dataclass
class EmployeeSkill:
    """Derived skills for employees"""
    employee_id: int
    skill_name: str
    skill_category: Optional[str] = None
    confidence_score: float = 0.5
    source: str = 'derived'
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class RoleOwnership:
    """Role ownership and accountability"""
    employee_id: int
    responsibility_area: str
    ownership_type: str = 'primary'  # primary, backup, escalation
    team: Optional[str] = None
    is_active: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class RecommendationResult:
    """Agent recommendation output"""
    employee: Employee
    match_score: float
    match_reasons: List[str] = field(default_factory=list)
    ownership_type: Optional[str] = None  # primary, backup, escalation
    people_leader: Optional[Employee] = None

    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            'employee': self.employee.to_dict(),
            'match_score': round(self.match_score, 2),
            'match_reasons': self.match_reasons,
            'ownership_type': self.ownership_type,
            'people_leader': self.people_leader.to_dict() if self.people_leader else None
        }


@dataclass
class AgentResponse:
    """Complete agent response structure"""
    understanding: str  # What the agent understood
    recommended_roles: List[str]  # Roles/teams first (Survey insight)
    recommendations: List[RecommendationResult]
    confidence_level: str  # 'high', 'medium', 'low'
    disclaimer: str  # RAI compliance
    estimated_time_saved: float  # Minutes
    next_steps: List[str] = field(default_factory=list)

    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            'understanding': self.understanding,
            'recommended_roles': self.recommended_roles,
            'recommendations': [r.to_dict() for r in self.recommendations],
            'confidence_level': self.confidence_level,
            'disclaimer': self.disclaimer,
            'estimated_time_saved': self.estimated_time_saved,
            'next_steps': self.next_steps
        }


@dataclass
class QueryLog:
    """Query logging for analytics"""
    session_id: str
    user_query: str
    parsed_intent: Optional[str] = None
    recommended_employees: Optional[str] = None  # JSON
    feedback_score: Optional[int] = None
    time_saved_minutes: Optional[float] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None

