"""
FaceNet Smart Attendance System
Main Flask application entry point (Render-ready)
"""

from flask import Flask, redirect, url_for
from config import Config
from database.db import init_db

from routes.auth import auth_bp
from routes.students import students_bp
from routes.attendance import attendance_bp
from routes.upload import upload_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize DB
    with app.app_context():
        init_db()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(upload_bp)

    # Root route
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app


# ✅ IMPORTANT: expose app for gunicorn
app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)