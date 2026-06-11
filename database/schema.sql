-- ============================================================
--  FaceNet Smart Attendance System – Database Schema
--  Run against MySQL:  mysql -u root -p < schema.sql
--  SQLite schema is handled automatically by db.py
-- ============================================================

CREATE DATABASE IF NOT EXISTS attendance_system
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE attendance_system;

-- ── Table: users ──────────────────────────────────────────────────────────
-- Stores admin / teacher login accounts.
CREATE TABLE IF NOT EXISTS users (
    id         INT          NOT NULL AUTO_INCREMENT,
    username   VARCHAR(80)  NOT NULL,
    email      VARCHAR(120) NOT NULL,
    password   VARCHAR(255) NOT NULL COMMENT 'werkzeug PBKDF2 hash',
    role       VARCHAR(20)  NOT NULL DEFAULT 'teacher',
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_username (username),
    UNIQUE KEY uq_email    (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── Table: students ───────────────────────────────────────────────────────
-- One row per enrolled student.
CREATE TABLE IF NOT EXISTS students (
    id         INT          NOT NULL AUTO_INCREMENT,
    name       VARCHAR(100) NOT NULL,
    roll_no    VARCHAR(30)  NOT NULL,
    department VARCHAR(100) NOT NULL,
    image_path VARCHAR(255)          COMMENT 'relative path under /static/',

    PRIMARY KEY (id),
    UNIQUE KEY uq_roll_no (roll_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── Table: attendance ─────────────────────────────────────────────────────
-- One row per attendance event (student × session date).
CREATE TABLE IF NOT EXISTS attendance (
    id         INT         NOT NULL AUTO_INCREMENT,
    student_id INT         NOT NULL,
    date       DATE        NOT NULL,
    time       TIME        NOT NULL,
    status     VARCHAR(10) NOT NULL DEFAULT 'Present',

    PRIMARY KEY (id),
    UNIQUE KEY uq_student_date (student_id, date),   -- one record per day
    FOREIGN KEY fk_att_student (student_id)
        REFERENCES students(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── Table: dataset_logs ───────────────────────────────────────────────────
-- Tracks how many training images have been uploaded for each student.
CREATE TABLE IF NOT EXISTS dataset_logs (
    id          INT      NOT NULL AUTO_INCREMENT,
    student_id  INT      NOT NULL,
    image_count INT      NOT NULL DEFAULT 0,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    FOREIGN KEY fk_log_student (student_id)
        REFERENCES students(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── Seed: default admin account ───────────────────────────────────────────
-- Password: admin123  (change immediately after first login!)
-- Hash generated with: werkzeug.security.generate_password_hash('admin123')
INSERT IGNORE INTO users (username, email, password, role)
VALUES (
    'admin',
    'admin@college.edu',
    'pbkdf2:sha256:600000$abc123$aabbccdd...',  -- replace with real hash
    'admin'
);
