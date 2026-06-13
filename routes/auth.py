"""
routes/auth.py
==============
Handles user registration, login, and logout.
Passwords are hashed with Werkzeug's generate_password_hash.
"""

import re
import random
from datetime import datetime, timedelta
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
        phone    = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        # ── Basic validation ──────────────────────────────────────────────────
        if not all([username, email, phone, password, confirm]):
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if len(password) < 8 or \
           not re.search(r"[A-Z]", password) or \
           not re.search(r"[a-z]", password) or \
           not re.search(r"\d", password) or \
           not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            flash('Password must be at least 8 characters long, and include an uppercase letter, lowercase letter, number, and special character.', 'danger')
            return render_template('register.html')

        # ── Check duplicates ──────────────────────────────────────────────────
        existing = query_db(
            'SELECT id FROM users WHERE username = ? OR email = ? OR phone = ?',
            (username, email, phone), one=True
        )
        if existing:
            flash('Username, email, or phone already registered.', 'danger')
            return render_template('register.html')

        # ── Store hashed password ─────────────────────────────────────────────
        hashed_pw = generate_password_hash(password)
        execute_db(
            'INSERT INTO users (username, email, phone, password, role) VALUES (?, ?, ?, ?, ?)',
            (username, email, phone, hashed_pw, 'teacher')
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


@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        if not phone:
            flash('Phone number is required.', 'danger')
            return render_template('forgot_password.html')
            
        user = query_db('SELECT id FROM users WHERE phone = ?', (phone,), one=True)
        if user:
            otp = str(random.randint(100000, 999999))
            expiry = (datetime.now() + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
            execute_db('UPDATE users SET reset_otp = ?, otp_expiry = ? WHERE id = ?', (otp, expiry, user['id']))
            print(f"\n{'='*40}\nOTP FOR PHONE {phone} IS {otp}\n{'='*40}\n")
            session['reset_phone'] = phone
            flash('An OTP has been sent to your phone number.', 'info')
            return redirect(url_for('auth.verify_otp'))
        else:
            flash('No account found with that phone number.', 'danger')
            
    return render_template('forgot_password.html')

@auth_bp.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'reset_phone' not in session:
        return redirect(url_for('auth.forgot_password'))
        
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        phone = session['reset_phone']
        
        user = query_db('SELECT id, reset_otp, otp_expiry FROM users WHERE phone = ?', (phone,), one=True)
        if user and user['reset_otp'] == otp:
            if user['otp_expiry']:
                expiry = datetime.strptime(user['otp_expiry'], '%Y-%m-%d %H:%M:%S')
                if datetime.now() <= expiry:
                    session['otp_verified'] = True
                    flash('OTP verified successfully. You may now reset your password.', 'success')
                    return redirect(url_for('auth.reset_password'))
                else:
                    flash('OTP has expired. Please request a new one.', 'danger')
            else:
                 flash('Invalid OTP request.', 'danger')
        else:
            flash('Invalid OTP.', 'danger')
            
    return render_template('verify_otp.html')

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_phone' not in session or not session.get('otp_verified'):
        return redirect(url_for('auth.forgot_password'))
        
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html')
            
        if len(password) < 8 or \
           not re.search(r"[A-Z]", password) or \
           not re.search(r"[a-z]", password) or \
           not re.search(r"\d", password) or \
           not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            flash('Password must be at least 8 characters long, and include an uppercase letter, lowercase letter, number, and special character.', 'danger')
            return render_template('reset_password.html')
            
        phone = session['reset_phone']
        hashed_pw = generate_password_hash(password)
        execute_db('UPDATE users SET password = ?, reset_otp = NULL, otp_expiry = NULL WHERE phone = ?', (hashed_pw, phone))
        
        # Clear reset session vars
        session.pop('reset_phone', None)
        session.pop('otp_verified', None)
        
        flash('Password reset successfully. Please login with your new password.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('reset_password.html')
