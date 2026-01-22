"""
Data models for Employee Directory
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Employee:
    """Employee model"""
    formal_name: str
    email_address: str
    position_title: str
    function: Optional[str] = None
    business_unit: Optional[str] = None
    team: Optional[str] = None
    location: Optional[str] = None
    people_leader_id: Optional[int] = None
    is_active: bool = True
    id: Optional[int] = None


@dataclass
class QueryLog:
    """Query log model for analytics"""
    session_id: str
    user_query: str
    parsed_intent: Optional[str] = None
    recommended_employees: Optional[str] = None
    feedback_score: Optional[int] = None
    time_saved_minutes: Optional[float] = None
    id: Optional[int] = None
