-- EC Skills Finder - Mock Employees Seed (editable)
-- Purpose: Insert a small, high-signal set of TEST employees + skills into your SQLite DB.
-- How to run:
--   sqlite3 data/employee_directory_200_mock.db < ec_mock_employees_seed.sql
--
-- Notes:
-- - Uses employee IDs 901–905 so you can easily remove later.
-- - Uses INSERT OR IGNORE for skills so it’s safe to re-run.
-- - Adjust names/emails/teams/skills below as you like.

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

----------------------------------------------------------------------
-- 1) Employees (edit freely)
----------------------------------------------------------------------

-- Valid Employee 1 — Perfect technical match
INSERT OR REPLACE INTO employees (id, formal_name, email_address, position_title, team, is_active)
VALUES (901, 'Valid Employee1 (TEST)', 'valid.employee1@company.co.nz', 'Senior Data Engineer', 'Data Platform', 1);

-- Valid Employee 2 — Partial match, strong domain
INSERT OR REPLACE INTO employees (id, formal_name, email_address, position_title, team, is_active)
VALUES (902, 'Valid Employee2 (TEST)', 'valid.employee2@company.co.nz', 'Analytics Manager', 'Business Intelligence', 1);

-- Valid Employee 3 — Wrong title, right skills
INSERT OR REPLACE INTO employees (id, formal_name, email_address, position_title, team, is_active)
VALUES (903, 'Valid Employee3 (TEST)', 'valid.employee3@company.co.nz', 'Operations Analyst', 'Operations', 1);

-- Valid Employee 4 — Right title, wrong skills (false-positive guardrail)
INSERT OR REPLACE INTO employees (id, formal_name, email_address, position_title, team, is_active)
VALUES (904, 'Valid Employee4 (TEST)', 'valid.employee4@company.co.nz', 'Data Engineer', 'Digital', 1);

-- Valid Employee 5 — Risk / compliance specialist
INSERT OR REPLACE INTO employees (id, formal_name, email_address, position_title, team, is_active)
VALUES (905, 'Valid Emplyee5 (TEST)', 'valid.employee5@company.co.nz', 'Risk & Compliance Lead', 'Enterprise Risk', 1);

----------------------------------------------------------------------
-- 2) Skills (edit freely; exact names matter for matching)
--    Add/remove skills in this list as needed.
----------------------------------------------------------------------

INSERT OR IGNORE INTO skills (name) VALUES
  ('Data Engineering'),
  ('Cloud Platforms'),
  ('Machine Learning'),
  ('Budgeting & Forecasting'),
  ('Stakeholder Management'),
  ('SQL'),
  ('Automation'),
  ('Excel'),
  ('Reporting'),
  ('Compliance & Controls'),
  ('Risk Strategy'),
  ('Data Privacy');

----------------------------------------------------------------------
-- 3) Employee ↔ Skill links (edit freely)
--    Proficiency levels: awareness | skilled | advanced | expert
--    is_verified: 1 or 0 (use 1 for stable test data)
----------------------------------------------------------------------

-- Helper pattern:
-- INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, is_verified)
-- SELECT <EMP_ID>, id, '<LEVEL>', 1 FROM skills WHERE name = '<SKILL NAME>';

-- Employee 901 — Valid Employee1 (TEST)
INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, is_verified)
SELECT 901, id, 'expert', 1 FROM skills WHERE name = 'Data Engineering';
INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, is_verified)
SELECT 901, id, 'advanced', 1 FROM skills WHERE name = 'Cloud Platforms';
INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, is_verified)
SELECT 901, id, 'skilled', 1 FROM skills WHERE name = 'Machine Learning';

-- Employee 902 — Valid Employee2 (TEST)
INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, is_verified)
SELECT 902, id, 'skilled', 1 FROM skills WHERE name = 'Data Engineering';
INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, is_verified)
SELECT 902, id, 'advanced', 1 FROM skills WHERE name = 'Budgeting & Forecasting';
INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, is_verified)
SELECT 902, id, 'expert', 1 FROM skills WHERE name = 'Stakeholder Management';

-- Employee 903 — Valid Employee3 (TEST)
INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, is_verified)
SELECT 903, id, 'advanced', 1 FROM skills WHERE name = 'Data Engineering';
INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, is_verified)
SELECT 903, id, 'expert', 1 FROM skills WHERE name = 'SQL';
INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, is_verified)
SELECT 903, id, 'skilled', 1 FROM skills WHERE name = 'Automation';

-- Employee 904 — Valid Employee4 (TEST)
INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, is_verified)
SELECT 904, id, 'skilled', 1 FROM skills WHERE name = 'Excel';
INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, is_verified)
SELECT 904, id, 'awareness', 1 FROM skills WHERE name = 'Reporting';

-- Employee 905 — Valid Employee5 (TEST)
INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, is_verified)
SELECT 905, id, 'expert', 1 FROM skills WHERE name = 'Compliance & Controls';
INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, is_verified)
SELECT 905, id, 'advanced', 1 FROM skills WHERE name = 'Risk Strategy';
INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, is_verified)
SELECT 905, id, 'expert', 1 FROM skills WHERE name = 'Data Privacy';

COMMIT;

----------------------------------------------------------------------
-- OPTIONAL: Cleanup (uncomment to remove test employees)
-- WARNING: This will delete test employees and their skill links.
----------------------------------------------------------------------
-- BEGIN TRANSACTION;
-- DELETE FROM employee_skills WHERE employee_id BETWEEN 901 AND 905;
-- DELETE FROM employees WHERE id BETWEEN 901 AND 905;
-- COMMIT;
