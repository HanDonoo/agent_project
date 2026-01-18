"""
Database manager for One NZ Employee Directory
"""
import sqlite3
import os
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from pathlib import Path

from .models import Employee, EmployeeSkill, RoleOwnership, QueryLog


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
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _initialize_database(self):
        """Initialize database schema"""
        schema_path = Path(__file__).parent / "schema.sql"
        
        with self.get_connection() as conn:
            with open(schema_path, 'r') as f:
                conn.executescript(f.read())
    
    # ============================================
    # Employee Operations
    # ============================================
    
    def insert_employee(self, employee: Employee) -> int:
        """Insert a new employee and return the ID"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO employees (
                    formal_name, email_address, position_title, function,
                    business_unit, team, location, people_leader_id, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                employee.formal_name, employee.email_address, employee.position_title,
                employee.function, employee.business_unit, employee.team,
                employee.location, employee.people_leader_id, employee.is_active
            ))
            return cursor.lastrowid

    def update_employee_leader(self, employee_id: int, leader_id: int) -> bool:
        """Update employee's people leader"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE employees SET people_leader_id = ? WHERE id = ?
            """, (leader_id, employee_id))
            return True
    
    def get_employee_by_email(self, email: str) -> Optional[Employee]:
        """Get employee by email address"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM employees WHERE email_address = ? AND is_active = 1
            """, (email,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_employee(row)
            return None
    
    def get_employee_by_id(self, employee_id: int) -> Optional[Employee]:
        """Get employee by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM employees WHERE id = ? AND is_active = 1
            """, (employee_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_employee(row)
            return None
    
    def search_employees_fulltext(self, query: str, limit: int = 20) -> List[Employee]:
        """Full-text search across employee data"""
        # Escape FTS5 special characters and prepare query
        # Remove special FTS5 characters that might cause syntax errors
        fts_query = query.replace('"', '').replace('?', '').replace('*', '').replace('(', '').replace(')', '')
        # Split into words and join with OR
        words = fts_query.split()
        if not words:
            return []
        fts_query = ' OR '.join(f'"{word}"' for word in words)

        with self.get_connection() as conn:
            try:
                cursor = conn.execute("""
                    SELECT e.* FROM employees e
                    JOIN employees_fts fts ON e.id = fts.rowid
                    WHERE employees_fts MATCH ?
                    AND e.is_active = 1
                    LIMIT ?
                """, (fts_query, limit))

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
        limit: int = 50
    ) -> List[Employee]:
        """Search employees by specific criteria"""
        query = "SELECT * FROM employees WHERE is_active = 1"
        params = []
        
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
    # Skills Operations
    # ============================================

    def insert_skill(self, skill: EmployeeSkill) -> int:
        """Insert employee skill"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO employee_skills (
                    employee_id, skill_name, skill_category, confidence_score, source
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                skill.employee_id, skill.skill_name, skill.skill_category,
                skill.confidence_score, skill.source
            ))
            return cursor.lastrowid

    def get_employees_by_skill(self, skill_name: str, min_confidence: float = 0.3) -> List[Employee]:
        """Find employees with a specific skill"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT e.* FROM employees e
                JOIN employee_skills es ON e.id = es.employee_id
                WHERE es.skill_name LIKE ?
                AND es.confidence_score >= ?
                AND e.is_active = 1
                ORDER BY es.confidence_score DESC
            """, (f"%{skill_name}%", min_confidence))

            return [self._row_to_employee(row) for row in cursor.fetchall()]

    # ============================================
    # Role Ownership Operations
    # ============================================

    def insert_role_ownership(self, ownership: RoleOwnership) -> int:
        """Insert role ownership record"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO role_ownership (
                    employee_id, responsibility_area, ownership_type, team, is_active
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                ownership.employee_id, ownership.responsibility_area,
                ownership.ownership_type, ownership.team, ownership.is_active
            ))
            return cursor.lastrowid

    def get_owners_by_responsibility(self, responsibility: str) -> List[Dict[str, Any]]:
        """Get employees responsible for a specific area (with ownership type)"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT e.*, ro.ownership_type, ro.responsibility_area
                FROM employees e
                JOIN role_ownership ro ON e.id = ro.employee_id
                WHERE ro.responsibility_area LIKE ?
                AND ro.is_active = 1
                AND e.is_active = 1
                ORDER BY
                    CASE ro.ownership_type
                        WHEN 'primary' THEN 1
                        WHEN 'backup' THEN 2
                        WHEN 'escalation' THEN 3
                        ELSE 4
                    END
            """, (f"%{responsibility}%",))

            results = []
            for row in cursor.fetchall():
                employee = self._row_to_employee(row)
                results.append({
                    'employee': employee,
                    'ownership_type': row['ownership_type'],
                    'responsibility_area': row['responsibility_area']
                })
            return results

    # ============================================
    # Query Logging
    # ============================================

    def log_query(self, log: QueryLog) -> int:
        """Log a user query for analytics"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO query_log (
                    session_id, user_query, parsed_intent,
                    recommended_employees, feedback_score, time_saved_minutes
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                log.session_id, log.user_query, log.parsed_intent,
                log.recommended_employees, log.feedback_score, log.time_saved_minutes
            ))
            return cursor.lastrowid

    # ============================================
    # Helper Methods
    # ============================================

    def _row_to_employee(self, row: sqlite3.Row) -> Employee:
        """Convert database row to Employee object"""
        return Employee(
            id=row['id'],
            formal_name=row['formal_name'],
            email_address=row['email_address'],
            position_title=row['position_title'],
            function=row['function'],
            business_unit=row['business_unit'],
            team=row['team'],
            location=row['location'],
            people_leader_id=row['people_leader_id'],
            is_active=bool(row['is_active'])
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        with self.get_connection() as conn:
            stats = {}

            # Total employees
            cursor = conn.execute("SELECT COUNT(*) as count FROM employees WHERE is_active = 1")
            stats['total_employees'] = cursor.fetchone()['count']

            # Total teams
            cursor = conn.execute("SELECT COUNT(DISTINCT team) as count FROM employees WHERE is_active = 1")
            stats['total_teams'] = cursor.fetchone()['count']

            # Total queries logged
            cursor = conn.execute("SELECT COUNT(*) as count FROM query_log")
            stats['total_queries'] = cursor.fetchone()['count']

            return stats

