from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Literal

ProficiencyLevel = Literal["not_selected", "awareness", "skilled", "advanced", "expert"]

@dataclass
class Skill:
    id: Optional[int] = None
    name: str = ""

@dataclass
class EmployeeSkill:
    id: Optional[int] = None
    employee_id: int = 0
    skill_id: int = 0
    proficiency_level: ProficiencyLevel = "awareness"
    is_verified: bool = False

    verified_by_employee_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    verification_note: Optional[str] = None
