"""
Excel data importer for Company Employee Directory
Imports employee data from Excel into the database, and links people leaders.

Notes:
- This importer performs a 2-pass import:
  1) Insert all employees (so everyone has an ID)
  2) Update people leader relationships (people_leader_id) once IDs exist
"""

import pandas as pd
from typing import Dict
import logging

from database.models import Employee
from database.db_manager import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExcelImporter:
    """Import employee data from an Excel file into the employee directory database."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.employee_cache: Dict[str, int] = {}  # email -> id mapping

    def import_from_excel(self, excel_path: str) -> Dict[str, int]:
        """
        Import employees from an Excel file.

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

        # Clean data (avoid NaN values causing issues)
        df = df.fillna('')

        stats = {
            'total_rows': len(df),
            'imported_employees': 0,
            'updated_people_leaders': 0,
            'errors': 0
        }

        # Pass 1: Import all employees (without people leader FK)
        logger.info("Pass 1: Importing employees...")
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

        # Pass 2: Update people leader relationships
        logger.info("Pass 2: Updating people leader relationships...")
        try:
            stats['updated_people_leaders'] = self._update_people_leaders(df)
        except Exception as e:
            logger.error(f"Error updating people leaders: {e}")
            stats['errors'] += 1

        logger.info(f"Import completed: {stats}")
        return stats

    def _row_to_employee(self, row: pd.Series) -> Employee:
        """Convert an Excel row to an Employee object."""
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

    def _update_people_leaders(self, df: pd.DataFrame) -> int:
        """
        Update people leader foreign keys after all employees are imported.

        This uses an approximate name match to locate the leader record.
        Returns the number of employees updated.
        """
        updated_count = 0

        for _, row in df.iterrows():
            email = str(row.get('Email Address', '')).strip().lower()
            leader_name = str(row.get('People Leader Formal Name', '')).strip()

            if not email or not leader_name:
                continue
            if email not in self.employee_cache:
                continue

            # Find leader by name (approximate match)
            leader = self._find_employee_by_name(leader_name)
            if not leader:
                continue

            # Update the employee's people_leader_id
            with self.db.get_connection() as conn:
                conn.execute(
                    """
                    UPDATE employees
                    SET people_leader_id = ?
                    WHERE id = ?
                    """,
                    (leader.id, self.employee_cache[email]),
                )
                updated_count += 1

        return updated_count

    def _find_employee_by_name(self, name: str) -> Employee:
        """Find an employee by name using a simple LIKE match."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM employees
                WHERE formal_name LIKE ?
                LIMIT 1
                """,
                (f"%{name}%",),
            )
            row = cursor.fetchone()
            if row:
                return self.db._row_to_employee(row)
        return None
