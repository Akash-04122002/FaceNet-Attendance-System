"""
database/db.py
==============
Provides get_db_connection() and init_db().
Supports both MySQL (production) and SQLite (development/fallback).
"""

import sqlite3
import os
from flask import current_app, g


# ─────────────────────────────────────────────────────────────────────────────
# Connection helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_db_connection():
    """
    Return an active database connection stored in Flask's 'g' object.
    Re-uses the same connection within a single request.
    """
    if 'db' not in g:
        db_type = current_app.config.get('DB_TYPE', 'sqlite')

        if db_type == 'postgres':
            g.db = _get_postgres_connection()
        else:
            g.db = _get_sqlite_connection()

    return g.db


def _get_sqlite_connection():
    """Open (or create) the SQLite database."""
    db_path = current_app.config['SQLITE_PATH']
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row   # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _get_postgres_connection():
    """Open a PostgreSQL connection using psycopg2."""
    try:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='Yoki143@',
            dbname='attendance_system',
        )
        return conn
    except Exception as exc:
        current_app.logger.error(f"PostgreSQL connection failed: {exc}. Falling back to SQLite.")
        return _get_sqlite_connection()


def close_db(e=None):
    """Close the database connection at the end of a request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Schema – SQL CREATE TABLE statements
# ─────────────────────────────────────────────────────────────────────────────

SQLITE_SCHEMA = """
-- ============================================================
-- Table: users
-- Stores admin / teacher accounts for the web application.
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    NOT NULL UNIQUE,
    email      TEXT    NOT NULL UNIQUE,
    password   TEXT    NOT NULL,          -- bcrypt / werkzeug hash
    role       TEXT    NOT NULL DEFAULT 'teacher',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Table: students
-- One row per enrolled student.
-- ============================================================
CREATE TABLE IF NOT EXISTS students (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    roll_no    TEXT    NOT NULL UNIQUE,
    department TEXT    NOT NULL,
    image_path TEXT                        -- path to representative photo
);

-- ============================================================
-- Table: attendance
-- One row per attendance record (student × date).
-- ============================================================
CREATE TABLE IF NOT EXISTS attendance (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    date       DATE    NOT NULL,
    time       TIME    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'Present',
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- ============================================================
-- Table: dataset_logs
-- Tracks how many training images were uploaded per student.
-- ============================================================
CREATE TABLE IF NOT EXISTS dataset_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  INTEGER NOT NULL,
    image_count INTEGER NOT NULL DEFAULT 0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- ============================================================
-- Table: marks
-- Stores marks details for students.
-- ============================================================
CREATE TABLE IF NOT EXISTS marks (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id     INTEGER NOT NULL,
    subject        TEXT NOT NULL,
    marks_obtained REAL NOT NULL,
    total_marks    REAL NOT NULL,
    date_recorded  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    username   VARCHAR(80)  NOT NULL UNIQUE,
    email      VARCHAR(120) NOT NULL UNIQUE,
    password   VARCHAR(255) NOT NULL,
    role       VARCHAR(20)  NOT NULL DEFAULT 'teacher',
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS students (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    roll_no    VARCHAR(30)  NOT NULL UNIQUE,
    department VARCHAR(100) NOT NULL,
    image_path VARCHAR(255),
    parent_email VARCHAR(120),
    parent_phone VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS attendance (
    id         SERIAL PRIMARY KEY,
    student_id INT     NOT NULL,
    date       DATE    NOT NULL,
    time       TIME    NOT NULL,
    status     VARCHAR(10) NOT NULL DEFAULT 'Present',
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE (student_id, date)
);

CREATE TABLE IF NOT EXISTS dataset_logs (
    id          SERIAL PRIMARY KEY,
    student_id  INT      NOT NULL,
    image_count INT      NOT NULL DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS marks (
    id             SERIAL PRIMARY KEY,
    student_id     INT      NOT NULL,
    subject        VARCHAR(100) NOT NULL,
    marks_obtained FLOAT    NOT NULL,
    total_marks    FLOAT    NOT NULL,
    date_recorded  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);
"""


def init_db():
    """
    Create all tables if they do not yet exist.
    Called once at startup from app.py.
    """
    from flask import current_app
    db_type = current_app.config.get('DB_TYPE', 'sqlite')

    if db_type == 'postgres':
        try:
            import psycopg2
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                user='postgres',
                password='Yoki143@',
                dbname='attendance_system'
            )
            cursor = conn.cursor()
            for statement in POSTGRES_SCHEMA.strip().split(';'):
                stmt = statement.strip()
                if stmt:
                    cursor.execute(stmt)
            conn.commit()
            cursor.close()
            conn.close()
            current_app.logger.info("PostgreSQL schema initialised.")
            return
        except Exception as exc:
            current_app.logger.warning(f"PostgreSQL init failed ({exc}), using SQLite.")

    # SQLite fallback
    db_path = current_app.config['SQLITE_PATH']
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SQLITE_SCHEMA)
    
    # Add columns for backwards compatibility if they don't exist
    try:
        conn.execute("ALTER TABLE students ADD COLUMN parent_email VARCHAR(120);")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE students ADD COLUMN parent_phone VARCHAR(20);")
    except Exception:
        pass
        
    conn.commit()
    conn.close()
    current_app.logger.info("SQLite schema initialised.")


def query_db(query, args=(), one=False):
    """
    Convenience wrapper – executes a SELECT and returns Row objects.
    Use execute_db() for INSERT / UPDATE / DELETE.
    """
    conn = get_db_connection()
    import sqlite3

    if not isinstance(conn, sqlite3.Connection):
        import psycopg2.extras
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(query.replace('?', '%s'), args)
        rv = cursor.fetchall()
        cursor.close()
    else:
        cursor = conn.execute(query, args)
        rv = cursor.fetchall()
        cursor.close()

    return (rv[0] if rv else None) if one else rv


def execute_db(query, args=()):
    """
    Execute a write query (INSERT / UPDATE / DELETE).
    Returns lastrowid.
    """
    conn = get_db_connection()
    import sqlite3

    if not isinstance(conn, sqlite3.Connection):
        cursor = conn.cursor()
        if query.strip().upper().startswith("INSERT") and "RETURNING" not in query.upper():
            cursor.execute(query.replace('?', '%s') + " RETURNING id", args)
            conn.commit()
            last_id = cursor.fetchone()[0] if cursor.rowcount > 0 else None
        else:
            cursor.execute(query.replace('?', '%s'), args)
            conn.commit()
            last_id = cursor.rowcount
        cursor.close()
    else:
        cursor = conn.execute(query, args)
        conn.commit()
        last_id = cursor.lastrowid
        cursor.close()

    return last_id
