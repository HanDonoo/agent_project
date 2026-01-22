"""
create_new_db_with_mock_data.py

Creates a NEW SQLite DB file and seeds a telecom-style org with mock data:
- 200 employees (chief + managers + employees)
- Skills catalogue imported from EC_skills_catalogue.py (extensible, no fixed length)
- Employee-selected skills with proficiency levels: awareness/skilled/advanced/expert
- Optional verification (verified by the employee's people leader)

Expected repo layout (relative to this file):
EC_proj/
  EC_database/EC_schema.sql
  data_creation/create_new_db_with_mock_data.py   (this file)
  data_creation/EC_skills_catalogue.py            (SKILLS_CATALOGUE defined here)
  data/                                           (DB output folder)

Run:
  python3 EC_proj/data_creation/create_new_db_with_mock_data.py

WARNING:
- This script deletes the output DB if it already exists.
"""

from __future__ import annotations

import random
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple

# ==========================================================
# Import the skills catalogue (same folder as this script)
# ==========================================================
try:
    from EC_skills_catalogue import SKILLS_CATALOGUE
except ModuleNotFoundError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parent))
    from EC_skills_catalogue import SKILLS_CATALOGUE  # type: ignore


# ==========================================================
# Configuration
# ==========================================================
RANDOM_SEED = 42

TOTAL_EMPLOYEES = 200
CHIEF_COUNT = 1
MANAGER_COUNT = 24
EMPLOYEE_COUNT = TOTAL_EMPLOYEES - CHIEF_COUNT - MANAGER_COUNT

COMPANY_DOMAIN = "company.co.nz"
LOCATIONS = ["Auckland", "Wellington", "Christchurch", "Hamilton", "Dunedin"]

FUNCTIONS: List[Tuple[str, str]] = [
    ("Technology", "Network"),
    ("Technology", "Engineering"),
    ("Technology", "Security"),
    ("Technology", "Data"),
    ("Commercial", "Sales"),
    ("Commercial", "Product"),
    ("Operations", "NOC"),
    ("Operations", "Service Desk"),
    ("Operations", "Field Ops"),
    ("Corporate", "Finance"),
    ("Corporate", "People"),
]

ROLE_TITLES = {
    "Network": ["Network Engineer", "Senior Network Engineer", "Transmission Engineer", "IP/MPLS Engineer", "RAN Engineer", "Core Network Engineer"],
    "Engineering": ["Software Engineer", "Senior Software Engineer", "DevOps Engineer", "Platform Engineer", "SRE", "Integration Engineer"],
    "Security": ["Security Analyst", "Security Engineer", "SOC Analyst", "GRC Analyst", "IAM Engineer"],
    "Data": ["Data Analyst", "Senior Data Analyst", "Data Engineer", "BI Developer", "Analytics Engineer"],
    "Sales": ["Account Manager", "Senior Account Manager", "Sales Engineer", "Solutions Specialist"],
    "Product": ["Product Manager", "Senior Product Manager", "Product Owner"],
    "NOC": ["NOC Engineer", "Incident Coordinator", "Operations Analyst"],
    "Service Desk": ["Service Desk Specialist", "Service Desk Lead"],
    "Field Ops": ["Field Technician", "Field Engineer", "Site Engineer"],
    "Finance": ["Financial Analyst", "Finance Business Partner"],
    "People": ["People Partner", "Recruiter"],
}

MANAGER_TITLES = [
    "Engineering Manager",
    "Network Operations Manager",
    "Security Manager",
    "Data & Analytics Manager",
    "Sales Manager",
    "Product Manager",
    "NOC Manager",
    "Service Desk Manager",
    "Field Operations Manager",
]

TEAM_BY_FUNCTION = {
    "Network": ["RAN", "Core Network", "IP/MPLS", "Transmission", "Network Operations"],
    "Engineering": ["Platform Engineering", "Integration", "Automation", "Digital Channels"],
    "Security": ["Cybersecurity", "SOC", "GRC"],
    "Data": ["Customer Insights", "Data Platform", "BI & Reporting"],
    "Sales": ["Enterprise Sales", "SMB Sales", "Public Sector"],
    "Product": ["Mobile Product", "Broadband Product", "Enterprise Product"],
    "NOC": ["NOC", "Incident Response"],
    "Service Desk": ["Service Desk"],
    "Field Ops": ["Field Operations", "Site Deployment"],
    "Finance": ["Finance"],
    "People": ["People & Culture"],
}


# ==========================================================
# Reliable path resolution (relative, but with good diagnostics)
# ==========================================================
def project_root_from_script() -> Path:
    # EC_proj/data_creation/<thisfile> -> EC_proj
    return Path(__file__).resolve().parent.parent


def resolve_schema_path() -> Path:
    """
    Attempts several RELATIVE candidates from the script location.
    Prints what it tried if nothing is found.
    """
    root = project_root_from_script()

    candidates = [
        root / "EC_database" / "EC_schema.sql",
        root / "EC_database" / "EC_schema.SQL",
        # in case someone created a different casing folder
        root / "EC_Database" / "EC_schema.sql",
        # in case schema lives under a nested EC_Proj/ folder (you mentioned EC_Proj earlier)
        root.parent / "EC_Proj" / "EC_database" / "EC_schema.sql",
        root.parent / "EC_Proj" / "EC_database" / "EC_schema.SQL",
    ]

    for c in candidates:
        if c.exists():
            return c

    msg = ["EC_schema.sql not found. Tried these paths:"]
    msg.extend([f" - {c}" for c in candidates])
    raise FileNotFoundError("\n".join(msg))


def resolve_db_path() -> Path:
    root = project_root_from_script()
    out_dir = root / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / "employee_directory_200_mock.db"


# ==========================================================
# Identity helpers
# ==========================================================
def make_identifier(role: str, n: int) -> str:
    return f"{role.lower()}.{n:03d}"


def make_email(role: str, n: int) -> str:
    return f"{make_identifier(role, n)}@{COMPANY_DOMAIN}".lower()


def make_formal_name(role: str, n: int) -> str:
    return f"{role.capitalize()} {n:03d}"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ==========================================================
# DB helpers
# ==========================================================
def create_db(db_path: Path, schema_path: Path) -> sqlite3.Connection:
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    return conn


def insert_employee(
    conn: sqlite3.Connection,
    role: str,
    n: int,
    title: str,
    function: str,
    business_unit: str,
    team: str,
    location: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO employees (
            formal_name, email_address, position_title, function,
            business_unit, team, location, people_leader_id, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 1)
        """,
        (make_formal_name(role, n), make_email(role, n), title, function, business_unit, team, location),
    )
    return int(cur.lastrowid)


def set_leader(conn: sqlite3.Connection, employee_id: int, leader_id: int) -> None:
    conn.execute(
        "UPDATE employees SET people_leader_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (leader_id, employee_id),
    )


def get_or_create_skill_id(conn: sqlite3.Connection, skill_name: str) -> int:
    name = (skill_name or "").strip()
    if not name:
        raise ValueError("skill_name must be non-empty")

    row = conn.execute("SELECT id FROM skills WHERE name = ?", (name,)).fetchone()
    if row:
        return int(row["id"])

    cur = conn.execute("INSERT INTO skills(name) VALUES(?)", (name,))
    return int(cur.lastrowid)


def upsert_employee_skill(
    conn: sqlite3.Connection,
    employee_id: int,
    skill_name: str,
    proficiency_level: str,
    is_verified: bool,
    verified_by_employee_id: Optional[int],
) -> None:
    level = (proficiency_level or "").strip().lower()
    if level not in {"awareness", "skilled", "advanced", "expert"}:
        raise ValueError(f"Invalid proficiency_level: {proficiency_level}")

    skill_id = get_or_create_skill_id(conn, skill_name)

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
            1 if is_verified else 0,
            verified_by_employee_id if is_verified else None,
            iso_now() if is_verified else None,
            "Verified (mock)" if is_verified else None,
        ),
    )


# ==========================================================
# Seeding logic
# ==========================================================
def pick_business_unit_and_function(rng: random.Random) -> Tuple[str, str]:
    return rng.choice(FUNCTIONS)


def pick_team(rng: random.Random, function: str) -> str:
    return rng.choice(TEAM_BY_FUNCTION.get(function, [function]))


def pick_employee_title(rng: random.Random, function: str) -> str:
    return rng.choice(ROLE_TITLES.get(function, [f"{function} Specialist"]))


def pick_level(rng: random.Random) -> str:
    x = rng.random()
    if x < 0.20:
        return "awareness"
    if x < 0.60:
        return "skilled"
    if x < 0.90:
        return "advanced"
    return "expert"


def should_verify(rng: random.Random, level: str, role: str) -> bool:
    base = {"awareness": 0.05, "skilled": 0.15, "advanced": 0.30, "expert": 0.50}[level]
    if role in {"manager", "chief"}:
        base += 0.10
    return rng.random() < min(base, 0.85)


def seed_telecom_org(conn: sqlite3.Connection) -> None:
    rng = random.Random(RANDOM_SEED)

    if EMPLOYEE_COUNT <= 0:
        raise ValueError("EMPLOYEE_COUNT must be > 0 (check counts).")
    if not SKILLS_CATALOGUE:
        raise ValueError("SKILLS_CATALOGUE is empty. Populate EC_skills_catalogue.py.")

    # Preload catalogue into master skills table
    for s in SKILLS_CATALOGUE:
        get_or_create_skill_id(conn, s)

    print(f"Loaded {len(SKILLS_CATALOGUE)} skills from catalogue")

    # Chief
    chief_id = insert_employee(
        conn,
        role="chief",
        n=1,
        title="Chief Executive Officer",
        function="Executive",
        business_unit="Corporate",
        team="Executive",
        location=rng.choice(LOCATIONS),
    )

    # Managers
    manager_ids: List[int] = []
    for i in range(1, MANAGER_COUNT + 1):
        bu, func = pick_business_unit_and_function(rng)
        team = pick_team(rng, func)
        title = rng.choice(MANAGER_TITLES)
        m_id = insert_employee(conn, "manager", i, title, func, bu, team, rng.choice(LOCATIONS))
        set_leader(conn, m_id, chief_id)
        manager_ids.append(m_id)

    # Employees
    employee_ids: List[int] = []
    for i in range(1, EMPLOYEE_COUNT + 1):
        bu, func = pick_business_unit_and_function(rng)
        team = pick_team(rng, func)
        title = pick_employee_title(rng, func)
        e_id = insert_employee(conn, "employee", i, title, func, bu, team, rng.choice(LOCATIONS))
        set_leader(conn, e_id, rng.choice(manager_ids))
        employee_ids.append(e_id)

    def assign_skills(person_id: int, role: str) -> None:
        leader_row = conn.execute("SELECT people_leader_id FROM employees WHERE id = ?", (person_id,)).fetchone()
        leader_id = int(leader_row["people_leader_id"]) if leader_row and leader_row["people_leader_id"] else None

        if role == "chief":
            k = rng.randint(10, 16)
        elif role == "manager":
            k = rng.randint(8, 14)
        else:
            k = rng.randint(6, 12)

        k = min(k, len(SKILLS_CATALOGUE))
        chosen = rng.sample(SKILLS_CATALOGUE, k)

        for skill in chosen:
            level = pick_level(rng)
            verified = should_verify(rng, level, role)
            upsert_employee_skill(conn, person_id, skill, level, verified, leader_id)

    assign_skills(chief_id, "chief")
    for mid in manager_ids:
        assign_skills(mid, "manager")
    for eid in employee_ids:
        assign_skills(eid, "employee")

    print("✔ Seeded org + skills")


def sanity_check(conn: sqlite3.Connection) -> None:
    n_emp = conn.execute("SELECT COUNT(*) AS c FROM employees").fetchone()["c"]
    n_skills = conn.execute("SELECT COUNT(*) AS c FROM skills").fetchone()["c"]
    n_emp_sk = conn.execute("SELECT COUNT(*) AS c FROM employee_skills").fetchone()["c"]
    n_verified = conn.execute("SELECT COUNT(*) AS c FROM employee_skills WHERE is_verified = 1").fetchone()["c"]

    print("\n--- Sanity checks ---")
    print(f"Employees: {n_emp} (expected {TOTAL_EMPLOYEES})")
    print(f"Skills (master): {n_skills} (>= {len(SKILLS_CATALOGUE)})")
    print(f"Employee skill selections: {n_emp_sk} (varies)")
    print(f"Verified selections: {n_verified}")


def main() -> None:
    schema_path = resolve_schema_path()
    db_path = resolve_db_path()

    print(f"Using schema: {schema_path}")
    print(f"Creating DB:   {db_path}")

    conn = create_db(db_path=db_path, schema_path=schema_path)
    try:
        seed_telecom_org(conn)
        conn.commit()
        sanity_check(conn)
        print(f"\n✅ Created new DB with mock data at: {db_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
