"""
Excel data importer for Company Employee Directory
Imports employee data from Excel and derives skills automatically
"""
import pandas as pd
import re
from typing import List, Dict, Set
from pathlib import Path
import logging

from database.models import Employee, EmployeeSkill, RoleOwnership
from database.db_manager import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExcelImporter:
    """Import employee data from Excel file"""
    
    # Skill extraction patterns based on position titles and teams
    SKILL_PATTERNS = {
        # Technical skills
        'provisioning': ['provisioning', 'provision'],
        'network': ['network', 'networking', 'nw'],
        'cloud': ['cloud', 'aws', 'azure', 'gcp'],
        'security': ['security', 'infosec', 'cybersecurity'],
        'database': ['database', 'dba', 'sql'],
        'devops': ['devops', 'ci/cd', 'automation'],
        'api': ['api', 'integration'],
        'mobile': ['mobile', 'ios', 'android'],
        'web': ['web', 'frontend', 'backend'],
        
        # Domain skills
        'sales': ['sales', 'account', 'commercial'],
        'compliance': ['compliance', 'risk', 'audit', 'governance'],
        'product': ['product', 'pm'],
        'engineering': ['engineer', 'engineering', 'technical'],
        'support': ['support', 'helpdesk', 'service desk'],
        'analytics': ['analytics', 'data', 'bi', 'reporting'],
        'project management': ['project', 'programme', 'pmo'],
        
        # Business processes
        'bia': ['bia', 'business impact'],
        'billing': ['billing', 'invoice'],
        'crm': ['crm', 'customer relationship'],
        'procurement': ['procurement', 'purchasing'],
    }
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.employee_cache: Dict[str, int] = {}  # email -> id mapping
    
    def import_from_excel(self, excel_path: str) -> Dict[str, int]:
        """
        Import employees from Excel file
        
        Expected columns:
        - Formal Name
        - Email Address
        - People Leader Formal Name
        - Position Title
        - Function (Label)
        - Business Unit (Label)
        - Team (Label)
        - Location (Name)
        """
        logger.info(f"Starting import from {excel_path}")
        
        # Read Excel file
        df = pd.read_excel(excel_path)
        
        # Normalize column names
        df.columns = df.columns.str.strip()
        
        # Validate required columns
        required_cols = ['Formal Name', 'Email Address', 'Position Title']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Clean data
        df = df.fillna('')
        
        stats = {
            'total_rows': len(df),
            'imported_employees': 0,
            'imported_skills': 0,
            'imported_ownerships': 0,
            'errors': 0
        }
        
        # First pass: Import all employees (without people leader FK)
        logger.info("First pass: Importing employees...")
        for idx, row in df.iterrows():
            try:
                employee = self._row_to_employee(row)
                employee_id = self.db.insert_employee(employee)
                self.employee_cache[employee.email_address.lower()] = employee_id
                stats['imported_employees'] += 1
                
                if (idx + 1) % 100 == 0:
                    logger.info(f"Imported {idx + 1}/{len(df)} employees")
                    
            except Exception as e:
                logger.error(f"Error importing row {idx}: {e}")
                stats['errors'] += 1
        
        # Second pass: Update people leader relationships
        logger.info("Second pass: Updating people leader relationships...")
        self._update_people_leaders(df)
        
        # Third pass: Derive and import skills
        logger.info("Third pass: Deriving skills...")
        for email, emp_id in self.employee_cache.items():
            employee = self.db.get_employee_by_id(emp_id)
            if employee:
                skills = self._derive_skills(employee)
                for skill in skills:
                    try:
                        self.db.insert_skill(skill)
                        stats['imported_skills'] += 1
                    except Exception as e:
                        logger.error(f"Error inserting skill for {email}: {e}")
        
        logger.info(f"Import completed: {stats}")
        return stats
    
    def _row_to_employee(self, row: pd.Series) -> Employee:
        """Convert Excel row to Employee object"""
        return Employee(
            formal_name=str(row.get('Formal Name', '')).strip(),
            email_address=str(row.get('Email Address', '')).strip().lower(),
            position_title=str(row.get('Position Title', '')).strip(),
            function=str(row.get('Function (Label)', '')).strip() or None,
            business_unit=str(row.get('Business Unit (Label)', '')).strip() or None,
            team=str(row.get('Team (Label)', '')).strip() or None,
            location=str(row.get('Location (Name)', '')).strip() or None,
            people_leader_name=str(row.get('People Leader Formal Name', '')).strip() or None,
            is_active=True
        )

    def _update_people_leaders(self, df: pd.DataFrame):
        """Update people leader foreign keys after all employees are imported"""
        for idx, row in df.iterrows():
            email = str(row.get('Email Address', '')).strip().lower()
            leader_name = str(row.get('People Leader Formal Name', '')).strip()

            if email and leader_name and email in self.employee_cache:
                # Find leader by name (approximate match)
                leader = self._find_employee_by_name(leader_name)
                if leader:
                    # Update the employee's people_leader_id
                    with self.db.get_connection() as conn:
                        conn.execute("""
                            UPDATE employees
                            SET people_leader_id = ?
                            WHERE id = ?
                        """, (leader.id, self.employee_cache[email]))

    def _find_employee_by_name(self, name: str) -> Employee:
        """Find employee by name (fuzzy match)"""
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM employees
                WHERE formal_name LIKE ?
                LIMIT 1
            """, (f"%{name}%",))
            row = cursor.fetchone()
            if row:
                return self.db._row_to_employee(row)
        return None

    def _derive_skills(self, employee: Employee) -> List[EmployeeSkill]:
        """
        Derive skills from employee's position, team, and function
        Based on survey insight: don't rely on self-reported skills
        """
        skills = []
        text_to_analyze = ' '.join(filter(None, [
            employee.position_title,
            employee.team,
            employee.function
        ])).lower()

        # Extract skills using pattern matching
        for skill_name, patterns in self.SKILL_PATTERNS.items():
            for pattern in patterns:
                if re.search(r'\b' + re.escape(pattern) + r'\b', text_to_analyze):
                    # Determine source and confidence
                    source = 'position_title'
                    confidence = 0.7

                    if pattern in (employee.team or '').lower():
                        source = 'team'
                        confidence = 0.8
                    elif pattern in (employee.function or '').lower():
                        source = 'function'
                        confidence = 0.9

                    skills.append(EmployeeSkill(
                        employee_id=employee.id,
                        skill_name=skill_name,
                        skill_category=self._categorize_skill(skill_name),
                        confidence_score=confidence,
                        source=source
                    ))
                    break  # Only add each skill once

        return skills

    def _categorize_skill(self, skill_name: str) -> str:
        """Categorize skill into broad categories"""
        technical_skills = {'provisioning', 'network', 'cloud', 'security', 'database',
                           'devops', 'api', 'mobile', 'web'}
        domain_skills = {'sales', 'compliance', 'product', 'engineering', 'support',
                        'analytics', 'project management'}
        process_skills = {'bia', 'billing', 'crm', 'procurement'}

        if skill_name in technical_skills:
            return 'Technical'
        elif skill_name in domain_skills:
            return 'Domain'
        elif skill_name in process_skills:
            return 'Process'
        else:
            return 'Other'

    def derive_role_ownerships(self):
        """
        Derive role ownerships based on position titles and teams
        This addresses the survey insight about ownership clarity
        """
        logger.info("Deriving role ownerships...")

        # Common responsibility patterns
        ownership_patterns = {
            'provisioning': ['provisioning', 'provision'],
            'network setup': ['network', 'infrastructure'],
            'security compliance': ['security', 'compliance', 'risk'],
            'customer support': ['support', 'service desk', 'helpdesk'],
            'billing operations': ['billing', 'invoice'],
            'product management': ['product manager', 'product owner'],
            'project delivery': ['project manager', 'programme'],
        }

        count = 0
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM employees WHERE is_active = 1")
            employees = [self.db._row_to_employee(row) for row in cursor.fetchall()]

        for employee in employees:
            position_lower = employee.position_title.lower()

            for responsibility, patterns in ownership_patterns.items():
                for pattern in patterns:
                    if pattern in position_lower:
                        # Determine ownership type
                        ownership_type = 'primary'
                        if 'lead' in position_lower or 'manager' in position_lower:
                            ownership_type = 'primary'
                        elif 'senior' in position_lower:
                            ownership_type = 'primary'
                        elif 'junior' in position_lower or 'assistant' in position_lower:
                            ownership_type = 'backup'

                        ownership = RoleOwnership(
                            employee_id=employee.id,
                            responsibility_area=responsibility,
                            ownership_type=ownership_type,
                            team=employee.team
                        )

                        try:
                            self.db.insert_role_ownership(ownership)
                            count += 1
                        except Exception as e:
                            logger.error(f"Error inserting ownership: {e}")

                        break  # Only one ownership per responsibility

        logger.info(f"Derived {count} role ownerships")
        return count

