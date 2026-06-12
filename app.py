"""
FaceNet Smart Attendance System
================================
Main Flask application entry point.
Registers all blueprints and initializes the app.
"""

from flask import Flask, redirect, url_for
from config import Config
from database.db import init_db
from routes.auth import auth_bp
from routes.students import students_bp
from routes.attendance import attendance_bp
from routes.upload import upload_bp


def create_app():
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # ── Initialize database (create tables if not exist) ──────────────────────
    with app.app_context():
        init_db()

    # ── Register blueprints ───────────────────────────────────────────────────
    app.register_blueprint(auth_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(upload_bp)

    # ── Root redirect ─────────────────────────────────────────────────────────
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
