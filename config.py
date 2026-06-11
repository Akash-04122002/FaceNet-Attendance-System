"""
config.py
=========
Central configuration for the Flask application.
Switch between MySQL and SQLite by editing DB_TYPE below.
"""

import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'facenet-attendance-secret-2024')
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # ── Database (set DB_TYPE = 'mysql' or 'sqlite') ──────────────────────────
    DB_TYPE = os.environ.get('DB_TYPE', 'sqlite')   # change to 'mysql' for prod

    # MySQL config (used when DB_TYPE == 'mysql')
    MYSQL_HOST     = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT     = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER     = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'password')
    MYSQL_DB       = os.environ.get('MYSQL_DB', 'attendance_system')

    # SQLite path (used when DB_TYPE == 'sqlite')
    SQLITE_PATH = os.path.join(BASE_DIR, 'database', 'attendance.db')

    # ── File upload paths ─────────────────────────────────────────────────────
    DATASET_RAW_DIR     = os.path.join(BASE_DIR, 'dataset', 'raw')
    DATASET_ALIGNED_DIR = os.path.join(BASE_DIR, 'dataset', 'aligned')
    MODEL_DIR           = os.path.join(BASE_DIR, 'model')
    REPORTS_DIR         = os.path.join(BASE_DIR, 'reports')
    UPLOAD_FOLDER       = os.path.join(BASE_DIR, 'static', 'uploads')

    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov'}
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024   # 100 MB

    # ── FaceNet / Model ───────────────────────────────────────────────────────
    FACENET_MODEL_PATH  = os.path.join(MODEL_DIR, 'facenet.pb')
    CLASSIFIER_PATH     = os.path.join(MODEL_DIR, 'classifier.pkl')
    EMBEDDING_SIZE      = 512
    RECOGNITION_THRESHOLD = 0.75   # SVM probability threshold
