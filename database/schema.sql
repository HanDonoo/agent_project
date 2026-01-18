-- One NZ Employee Directory Database Schema
-- Purpose: Support AI Agent for internal employee discovery and team formation

-- ============================================
-- 1. Employees Table (Core Data)
-- ============================================
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    formal_name TEXT NOT NULL,
    email_address TEXT UNIQUE NOT NULL,
    position_title TEXT NOT NULL,
    function TEXT,  -- Function (Label)
    business_unit TEXT,  -- Business Unit (Label)
    team TEXT,  -- Team (Label)
    location TEXT,  -- Location (Name)
    people_leader_id INTEGER,  -- Foreign key to self
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (people_leader_id) REFERENCES employees(id)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_email ON employees(email_address);
CREATE INDEX IF NOT EXISTS idx_team ON employees(team);
CREATE INDEX IF NOT EXISTS idx_function ON employees(function);
CREATE INDEX IF NOT EXISTS idx_business_unit ON employees(business_unit);
CREATE INDEX IF NOT EXISTS idx_people_leader ON employees(people_leader_id);

-- ============================================
-- 2. Derived Skills Table (AI-extracted)
-- ============================================
CREATE TABLE IF NOT EXISTS employee_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    skill_name TEXT NOT NULL,
    skill_category TEXT,  -- e.g., 'Technical', 'Domain', 'Process'
    confidence_score REAL DEFAULT 0.5,  -- 0.0 to 1.0
    source TEXT,  -- 'position_title', 'team', 'function', 'manual'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    UNIQUE(employee_id, skill_name)
);

CREATE INDEX IF NOT EXISTS idx_skill_name ON employee_skills(skill_name);
CREATE INDEX IF NOT EXISTS idx_employee_skill ON employee_skills(employee_id);

-- ============================================
-- 3. Role Ownership Table (Key for Survey Insight)
-- ============================================
CREATE TABLE IF NOT EXISTS role_ownership (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    responsibility_area TEXT NOT NULL,  -- e.g., 'BIA Provisioning', 'Network Setup'
    ownership_type TEXT DEFAULT 'primary',  -- 'primary', 'backup', 'escalation'
    team TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_responsibility ON role_ownership(responsibility_area);
CREATE INDEX IF NOT EXISTS idx_ownership_type ON role_ownership(ownership_type);

-- ============================================
-- 4. Query Log (For Analytics & Improvement)
-- ============================================
CREATE TABLE IF NOT EXISTS query_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_query TEXT NOT NULL,
    parsed_intent TEXT,
    recommended_employees TEXT,  -- JSON array of employee IDs
    feedback_score INTEGER,  -- 1-5 rating (optional)
    time_saved_minutes REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_session ON query_log(session_id);

-- ============================================
-- 5. Full-Text Search (FTS5 for fast search)
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

-- Triggers to keep FTS in sync
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

-- ============================================
-- 6. Common Queries/Patterns (Knowledge Base)
-- ============================================
CREATE TABLE IF NOT EXISTS query_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_keywords TEXT NOT NULL,  -- e.g., 'provisioning, BIA, setup'
    recommended_roles TEXT NOT NULL,  -- JSON array of role titles
    recommended_teams TEXT,  -- JSON array of team names
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pattern_keywords ON query_patterns(pattern_keywords);

