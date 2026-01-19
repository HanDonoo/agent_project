#!/usr/bin/env python3
"""
Script to import employee data from Excel file
Usage: python scripts/import_employees.py <path_to_excel_file>
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import DatabaseManager
from data_import.excel_importer import ExcelImporter
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_employees.py <path_to_excel_file>")
        print("\nExpected Excel columns:")
        print("  - Formal Name")
        print("  - Email Address")
        print("  - People Leader Formal Name")
        print("  - Position Title")
        print("  - Function (Label)")
        print("  - Business Unit (Label)")
        print("  - Team (Label)")
        print("  - Location (Name)")
        sys.exit(1)
    
    excel_path = sys.argv[1]
    
    if not os.path.exists(excel_path):
        logger.error(f"File not found: {excel_path}")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("Company Employee Directory - Data Import")
    logger.info("=" * 60)
    
    # Initialize database and importer
    logger.info("Initializing database...")
    db_manager = DatabaseManager()
    
    logger.info("Creating importer...")
    importer = ExcelImporter(db_manager)
    
    # Import data
    logger.info(f"Importing from: {excel_path}")
    stats = importer.import_from_excel(excel_path)
    
    # Derive role ownerships
    logger.info("Deriving role ownerships...")
    ownership_count = importer.derive_role_ownerships()
    stats['imported_ownerships'] = ownership_count
    
    # Print summary
    logger.info("=" * 60)
    logger.info("Import Summary:")
    logger.info(f"  Total rows processed: {stats['total_rows']}")
    logger.info(f"  Employees imported: {stats['imported_employees']}")
    logger.info(f"  Skills derived: {stats['imported_skills']}")
    logger.info(f"  Ownerships derived: {stats['imported_ownerships']}")
    logger.info(f"  Errors: {stats['errors']}")
    logger.info("=" * 60)
    
    # Get database statistics
    db_stats = db_manager.get_statistics()
    logger.info("Database Statistics:")
    logger.info(f"  Total active employees: {db_stats['total_employees']}")
    logger.info(f"  Total teams: {db_stats['total_teams']}")
    logger.info("=" * 60)
    
    logger.info("✅ Import completed successfully!")


if __name__ == "__main__":
    main()

