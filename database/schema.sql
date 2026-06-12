-- ============================================================
--  FaceNet Smart Attendance System – Database Schema
--  Run against PostgreSQL:  psql -U postgres -d attendance_system -f schema.sql
--  SQLite schema is handled automatically by db.py
-- ============================================================

-- ── Table: users ──────────────────────────────────────────────────────────
-- Stores admin / teacher login accounts.
CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    username   VARCHAR(80)  NOT NULL UNIQUE,
    email      VARCHAR(120) NOT NULL UNIQUE,
    password   VARCHAR(255) NOT NULL, -- werkzeug PBKDF2 hash
    role       VARCHAR(20)  NOT NULL DEFAULT 'teacher',
    created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ── Table: students ───────────────────────────────────────────────────────
-- One row per enrolled student.
CREATE TABLE IF NOT EXISTS students (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    roll_no    VARCHAR(30)  NOT NULL UNIQUE,
    department VARCHAR(100) NOT NULL,
    image_path VARCHAR(255),          -- relative path under /static/
    parent_email VARCHAR(120),
    parent_phone VARCHAR(20)
);


-- ── Table: attendance ─────────────────────────────────────────────────────
-- One row per attendance event (student × session date).
CREATE TABLE IF NOT EXISTS attendance (
    id         SERIAL PRIMARY KEY,
    student_id INT         NOT NULL,
    date       DATE        NOT NULL,
    time       TIME        NOT NULL,
    status     VARCHAR(10) NOT NULL DEFAULT 'Present',

    UNIQUE (student_id, date),   -- one record per day
    CONSTRAINT fk_att_student FOREIGN KEY (student_id)
        REFERENCES students(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- ── Table: dataset_logs ───────────────────────────────────────────────────
-- Tracks how many training images have been uploaded for each student.
CREATE TABLE IF NOT EXISTS dataset_logs (
    id          SERIAL PRIMARY KEY,
    student_id  INT      NOT NULL,
    image_count INT      NOT NULL DEFAULT 0,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_log_student FOREIGN KEY (student_id)
        REFERENCES students(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- ── Seed: default admin account ───────────────────────────────────────────
-- Password: admin123  (change immediately after first login!)
-- Hash generated with: werkzeug.security.generate_password_hash('admin123')
INSERT INTO users (username, email, password, role)
VALUES (
    'admin',
    'admin@college.edu',
    'scrypt:32768:8:1$YlZf0m...$...',  -- replace with real hash
    'admin'
) ON CONFLICT (username) DO NOTHING;
