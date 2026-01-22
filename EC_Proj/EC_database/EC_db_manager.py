"""
Database manager for Company Employee Directory

Updated:
- Supports employee-selected skills with proficiency + verification
- Removes derived skill fields (confidence/source/category)
- Removes role ownership operations
"""
import sqlite3
from typing import List, Optional, Dict, Any, Literal
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime

from .EC_models import Employee, QueryLog

ProficiencyLevel = Literal["awareness", "skilled", "advanced", "expert"]
_ALLOWED_LEVELS = {"awareness", "skilled", "advanced", "expert"}


class DatabaseManager:
    """Manages SQLite database operations"""

    def __init__(self, db_path: str = "data/employee_directory.db"):
        self.db_path = db_path
        self._ensure_db_directory()
        self._initialize_database()

    def _ensure_db_directory(self):
        """Create database directory if it doesn't exist"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            # enforce FK constraints
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _initialize_database(self):
        """Initialize database schema"""
        schema_path = Path(__file__).parent / "EC_schema.sql"
        with self.get_connection() as conn:
            with open(schema_path, "r") as f:
                conn.executescript(f.read())

    # ============================================
    # Employee Operations
    # ============================================

    def insert_employee(self, employee: Employee) -> int:
        """Insert a new employee and return the ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO employees (
                    formal_name, email_address, position_title, function,
                    business_unit, team, location, people_leader_id, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    employee.formal_name,
                    employee.email_address,
                    employee.position_title,
                    employee.function,
                    employee.business_unit,
                    employee.team,
                    employee.location,
                    employee.people_leader_id,
                    employee.is_active,
                ),
            )
            return int(cursor.lastrowid)

    def update_employee_leader(self, employee_id: int, leader_id: int) -> bool:
        """Update employee's people leader"""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE employees SET people_leader_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (leader_id, employee_id),
            )
            return True

    def get_employee_by_email(self, email: str) -> Optional[Employee]:
        """Get employee by email address"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM employees WHERE email_address = ? AND is_active = 1",
                (email,),
            )
            row = cursor.fetchone()
            return self._row_to_employee(row) if row else None

    def get_employee_by_id(self, employee_id: int) -> Optional[Employee]:
        """Get employee by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM employees WHERE id = ? AND is_active = 1",
                (employee_id,),
            )
            row = cursor.fetchone()
            return self._row_to_employee(row) if row else None

    def search_employees_fulltext(self, query: str, limit: int = 20) -> List[Employee]:
        """Full-text search across employee data"""
        fts_query = (
            query.replace('"', "")
            .replace("?", "")
            .replace("*", "")
            .replace("(", "")
            .replace(")", "")
        )
        words = fts_query.split()
        if not words:
            return []
        fts_query = " OR ".join(f'"{word}"' for word in words)

        with self.get_connection() as conn:
            try:
                cursor = conn.execute(
                    """
                    SELECT e.* FROM employees e
                    JOIN employees_fts fts ON e.id = fts.rowid
                    WHERE employees_fts MATCH ?
                      AND e.is_active = 1
                    LIMIT ?
                    """,
                    (fts_query, limit),
                )
                return [self._row_to_employee(row) for row in cursor.fetchall()]
            except Exception as e:
                print(f"FTS5 search error: {e}, query: {fts_query}")
                return []

    def search_employees_by_criteria(
        self,
        team: Optional[str] = None,
        function: Optional[str] = None,
        business_unit: Optional[str] = None,
        position_keywords: Optional[str] = None,
        limit: int = 50,
    ) -> List[Employee]:
        """Search employees by specific criteria"""
        query = "SELECT * FROM employees WHERE is_active = 1"
        params: List[Any] = []

        if team:
            query += " AND team LIKE ?"
            params.append(f"%{team}%")

        if function:
            query += " AND function LIKE ?"
            params.append(f"%{function}%")

        if business_unit:
            query += " AND business_unit LIKE ?"
            params.append(f"%{business_unit}%")

        if position_keywords:
            query += " AND position_title LIKE ?"
            params.append(f"%{position_keywords}%")

        query += " LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_employee(row) for row in cursor.fetchall()]

    # ============================================
    # Skills (Employee-selected + Verified)
    # ============================================

    def get_or_create_skill_id(self, skill_name: str) -> int:
        """Ensure a skill exists in skills table and return its id."""
        name = (skill_name or "").strip()
        if not name:
            raise ValueError("skill_name must be non-empty")

        with self.get_connection() as conn:
            row = conn.execute("SELECT id FROM skills WHERE name = ?", (name,)).fetchone()
            if row:
                return int(row["id"])

            cur = conn.execute("INSERT INTO skills(name) VALUES(?)", (name,))
            return int(cur.lastrowid)

    def upsert_employee_skill(
        self,
        employee_id: int,
        skill_name: str,
        proficiency_level: ProficiencyLevel,
        is_verified: bool = False,
        verified_by_employee_id: Optional[int] = None,
        verified_at: Optional[datetime] = None,
        verification_note: Optional[str] = None,
    ) -> int:
        """
        Attach/update a skill for an employee.
        Returns employee_skills.id.
        """
        level = (proficiency_level or "").strip().lower()
        if level not in _ALLOWED_LEVELS:
            raise ValueError(f"Invalid proficiency_level: {proficiency_level}. Allowed: {sorted(_ALLOWED_LEVELS)}")

        skill_id = self.get_or_create_skill_id(skill_name)

        verified_at_str = verified_at.isoformat() if isinstance(verified_at, datetime) else None
        is_verified_int = 1 if is_verified else 0

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO employee_skills(
                    employee_id, skill_id, proficiency_level, is_verified,
                    verified_by_employee_id, verified_at, verification_note,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, NULL)
                ON CONFLICT(employee_id, skill_id)
                DO UPDATE SET
                    proficiency_level = excluded.proficiency_level,
                    is_verified = excluded.is_verified,
                    verified_by_employee_id = excluded.verified_by_employee_id,
                    verified_at = excluded.verified_at,
                    verification_note = excluded.verification_note,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    employee_id,
                    skill_id,
                    level,
                    is_verified_int,
                    verified_by_employee_id,
                    verified_at_str,
                    verification_note,
                ),
            )

            row = conn.execute(
                "SELECT id FROM employee_skills WHERE employee_id = ? AND skill_id = ?",
                (employee_id, skill_id),
            ).fetchone()
            return int(row["id"])

    def get_skills_for_employee(self, employee_id: int) -> List[Dict[str, Any]]:
        """Return all skills for an employee with proficiency + verification."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    s.name AS skill_name,
                    es.proficiency_level,
                    es.is_verified,
                    es.verified_by_employee_id,
                    es.verified_at,
                    es.verification_note
                FROM employee_skills es
                JOIN skills s ON s.id = es.skill_id
                WHERE es.employee_id = ?
                ORDER BY s.name COLLATE NOCASE
                """,
                (employee_id,),
            )
            return [
                {
                    "skill_name": row["skill_name"],
                    "proficiency_level": row["proficiency_level"],
                    "is_verified": bool(row["is_verified"]),
                    "verified_by_employee_id": row["verified_by_employee_id"],
                    "verified_at": row["verified_at"],
                    "verification_note": row["verification_note"],
                }
                for row in cursor.fetchall()
            ]

    def remove_employee_skill(self, employee_id: int, skill_name: str) -> bool:
        """Remove a skill from an employee (by skill name)."""
        name = (skill_name or "").strip()
        if not name:
            return False

        with self.get_connection() as conn:
            row = conn.execute("SELECT id FROM skills WHERE name = ?", (name,)).fetchone()
            if not row:
                return False

            skill_id = int(row["id"])
            conn.execute(
                "DELETE FROM employee_skills WHERE employee_id = ? AND skill_id = ?",
                (employee_id, skill_id),
            )
            return True

    def get_employees_by_skill(
        self,
        skill_name: str,
        min_level: ProficiencyLevel = "awareness",
        verified_only: bool = False,
        limit: int = 100,
    ) -> List[Employee]:
        """Find employees with a skill filtered by min proficiency and verification."""
        level_rank = {"awareness": 1, "skilled": 2, "advanced": 3, "expert": 4}
        min_level_norm = (min_level or "").strip().lower()
        if min_level_norm not in level_rank:
            raise ValueError(f"Invalid min_level: {min_level}")

        name = (skill_name or "").strip()
        if not name:
            return []

        verified_clause = "AND es.is_verified = 1" if verified_only else ""

        with self.get_connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT e.*
                FROM employees e
                JOIN employee_skills es ON e.id = es.employee_id
                JOIN skills s ON s.id = es.skill_id
                WHERE s.name LIKE ?
                  AND e.is_active = 1
                  AND (
                      CASE es.proficiency_level
                          WHEN 'awareness' THEN 1
                          WHEN 'skilled' THEN 2
                          WHEN 'advanced' THEN 3
                          WHEN 'expert' THEN 4
                          ELSE 0
                      END
                  ) >= ?
                  {verified_clause}
                ORDER BY
                  (
                      CASE es.proficiency_level
                          WHEN 'expert' THEN 4
                          WHEN 'advanced' THEN 3
                          WHEN 'skilled' THEN 2
                          WHEN 'awareness' THEN 1
                          ELSE 0
                      END
                  ) DESC,
                  es.is_verified DESC,
                  e.formal_name ASC
                LIMIT ?
                """,
                (f"%{name}%", level_rank[min_level_norm], limit),
            )
            return [self._row_to_employee(row) for row in cursor.fetchall()]

    # ============================================
    # Query Logging
    # ============================================

    def log_query(self, log: QueryLog) -> int:
        """Log a user query for analytics"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO query_log (
                    session_id, user_query, parsed_intent,
                    recommended_employees, feedback_score, time_saved_minutes
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    log.session_id,
                    log.user_query,
                    log.parsed_intent,
                    log.recommended_employees,
                    log.feedback_score,
                    log.time_saved_minutes,
                ),
            )
            return int(cursor.lastrowid)

    # ============================================
    # Helper Methods
    # ============================================

    def _row_to_employee(self, row: sqlite3.Row) -> Employee:
        """Convert database row to Employee object"""
        return Employee(
            id=row["id"],
            formal_name=row["formal_name"],
            email_address=row["email_address"],
            position_title=row["position_title"],
            function=row["function"],
            business_unit=row["business_unit"],
            team=row["team"],
            location=row["location"],
            people_leader_id=row["people_leader_id"],
            is_active=bool(row["is_active"]),
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        with self.get_connection() as conn:
            stats: Dict[str, Any] = {}

            cursor = conn.execute("SELECT COUNT(*) as count FROM employees WHERE is_active = 1")
            stats["total_employees"] = cursor.fetchone()["count"]

            cursor = conn.execute("SELECT COUNT(DISTINCT team) as count FROM employees WHERE is_active = 1")
            stats["total_teams"] = cursor.fetchone()["count"]

            cursor = conn.execute("SELECT COUNT(*) as count FROM query_log")
            stats["total_queries"] = cursor.fetchone()["count"]

            return stats
