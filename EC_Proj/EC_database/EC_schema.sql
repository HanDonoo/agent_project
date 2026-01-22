-- EC_schema.sql
-- Employee Directory DB (telecom mock + skills catalogue)

PRAGMA foreign_keys = ON;

-- ============================================
-- 1) Employees
-- ============================================
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    formal_name TEXT NOT NULL,
    email_address TEXT UNIQUE NOT NULL,
    position_title TEXT NOT NULL,
    function TEXT,
    business_unit TEXT,
    team TEXT,
    location TEXT,
    people_leader_id INTEGER,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (people_leader_id) REFERENCES employees(id)
);

CREATE INDEX IF NOT EXISTS idx_employees_email ON employees(email_address);
CREATE INDEX IF NOT EXISTS idx_employees_team ON employees(team);
CREATE INDEX IF NOT EXISTS idx_employees_function ON employees(function);
CREATE INDEX IF NOT EXISTS idx_employees_business_unit ON employees(business_unit);
CREATE INDEX IF NOT EXISTS idx_employees_people_leader ON employees(people_leader_id);

-- ============================================
-- 2) Skills catalogue (extensible)
-- ============================================
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(name);

-- ============================================
-- 3) Employee-selected skills + proficiency + verification
-- ============================================
CREATE TABLE IF NOT EXISTS employee_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    proficiency_level TEXT NOT NULL CHECK (proficiency_level IN ('awareness', 'skilled', 'advanced', 'expert')),
    is_verified BOOLEAN DEFAULT 0,
    verified_by_employee_id INTEGER,
    verified_at TIMESTAMP,
    verification_note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE,
    FOREIGN KEY (verified_by_employee_id) REFERENCES employees(id),
    UNIQUE(employee_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_employee_skills_employee ON employee_skills(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_skills_skill ON employee_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_employee_skills_verified ON employee_skills(is_verified);

-- ============================================
-- 4) Query Log (optional; kept for your agent)
-- ============================================
CREATE TABLE IF NOT EXISTS query_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_query TEXT NOT NULL,
    parsed_intent TEXT,
    recommended_employees TEXT,
    feedback_score INTEGER,
    time_saved_minutes REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_query_log_session ON query_log(session_id);

-- ============================================
-- 5) Full-Text Search (FTS5) for employees
-- ============================================
CREATE VIRTUAL TABLE IF NOT EXISTS employees_fts USING fts5(
    formal_name,
    email_address,
    position_title,
    function,
    business_unit,
    team,
    location,
    content=employees,
    content_rowid=id
);

CREATE TRIGGER IF NOT EXISTS employees_ai AFTER INSERT ON employees BEGIN
    INSERT INTO employees_fts(rowid, formal_name, email_address, position_title, function, business_unit, team, location)
    VALUES (new.id, new.formal_name, new.email_address, new.position_title, new.function, new.business_unit, new.team, new.location);
END;

CREATE TRIGGER IF NOT EXISTS employees_ad AFTER DELETE ON employees BEGIN
    DELETE FROM employees_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS employees_au AFTER UPDATE ON employees BEGIN
    UPDATE employees_fts SET
        formal_name = new.formal_name,
        email_address = new.email_address,
        position_title = new.position_title,
        function = new.function,
        business_unit = new.business_unit,
        team = new.team,
        location = new.location
    WHERE rowid = new.id;
END;
