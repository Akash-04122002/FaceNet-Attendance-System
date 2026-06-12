"""
routes/auth.py
==============
Handles user registration, login, and logout.
Passwords are hashed with Werkzeug's generate_password_hash.
"""

from flask import (Blueprint, render_template, request,
                   redirect, url_for, session, flash)
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import query_db, execute_db
from functools import wraps

auth_bp = Blueprint('auth', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# Login-required decorator  (import from here in other routes)
# ─────────────────────────────────────────────────────────────────────────────

def login_required(f):
    """Redirect to login page if the user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new admin/teacher account."""
    if 'user_id' in session:
        return redirect(url_for('attendance.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        # ── Basic validation ──────────────────────────────────────────────────
        if not all([username, email, password, confirm]):
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')

        # ── Check duplicates ──────────────────────────────────────────────────
        existing = query_db(
            'SELECT id FROM users WHERE username = ? OR email = ?',
            (username, email), one=True
        )
        if existing:
            flash('Username or email already registered.', 'danger')
            return render_template('register.html')

        # ── Store hashed password ─────────────────────────────────────────────
        hashed_pw = generate_password_hash(password)
        execute_db(
            'INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)',
            (username, email, hashed_pw, 'teacher')
        )
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Authenticate an existing user."""
    if 'user_id' in session:
        return redirect(url_for('attendance.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = query_db(
            'SELECT * FROM users WHERE username = ?', (username,), one=True
        )

        if user and check_password_hash(user['password'], password):
            session.permanent = True
            session['user_id']  = user['id']
            session['username'] = user['username']
            session['role']     = user['role']
            flash(f"Welcome back, {user['username']}!", 'success')
            return redirect(url_for('attendance.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Clear session and redirect to login."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
