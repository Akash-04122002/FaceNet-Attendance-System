"""
routes/students.py
==================
CRUD operations for student records:
  /add_student   – register a new student
  /view_students – list all students
  /delete_student/<id> – remove a student
"""

import os
from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, current_app)
from werkzeug.utils import secure_filename
from database.db import query_db, execute_db
from routes.auth import login_required
from utils.email_utils import send_exam_results

students_bp = Blueprint('students', __name__)


def _allowed_image(filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext in current_app.config['ALLOWED_IMAGE_EXTENSIONS']


# ─────────────────────────────────────────────────────────────────────────────

@students_bp.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    """Add a new student to the database."""
    if request.method == 'POST':
        name         = request.form.get('name', '').strip()
        roll_no      = request.form.get('roll_no', '').strip().upper()
        department   = request.form.get('department', '').strip()
        parent_email = request.form.get('parent_email', '').strip()
        parent_phone = request.form.get('parent_phone', '').strip()
        photo        = request.files.get('photo')

        if not all([name, roll_no, department]):
            flash('Name, Roll No, and Department are required.', 'danger')
            return render_template('add_student.html')

        # Check duplicate roll number
        dup = query_db(
            'SELECT id FROM students WHERE roll_no = ?', (roll_no,), one=True
        )
        if dup:
            flash(f'Roll number {roll_no} already exists.', 'danger')
            return render_template('add_student.html')

        # Save optional profile photo
        image_path = None
        if photo and photo.filename and _allowed_image(photo.filename):
            filename  = secure_filename(f"{roll_no}_{photo.filename}")
            save_dir  = os.path.join(current_app.static_folder, 'uploads', 'profiles')
            os.makedirs(save_dir, exist_ok=True)
            photo.save(os.path.join(save_dir, filename))
            image_path = f'uploads/profiles/{filename}'

        execute_db(
            'INSERT INTO students (name, roll_no, department, image_path, parent_email, parent_phone) VALUES (?, ?, ?, ?, ?, ?)',
            (name, roll_no, department, image_path, parent_email, parent_phone)
        )
        flash(f'Student {name} added successfully!', 'success')
        return redirect(url_for('students.view_students'))

    return render_template('add_student.html')


@students_bp.route('/view_students')
@login_required
def view_students():
    """Display all registered students."""
    all_students = query_db('SELECT * FROM students ORDER BY name')
    # Attach dataset image counts
    for s in all_students:
        log = query_db(
            'SELECT COALESCE(SUM(image_count),0) AS cnt FROM dataset_logs WHERE student_id = ?',
            (s['id'],), one=True
        )
        s = dict(s)   # make mutable (Row objects are read-only)
    students_with_counts = []
    for s in all_students:
        row = dict(s)
        log = query_db(
            'SELECT COALESCE(SUM(image_count),0) AS cnt FROM dataset_logs WHERE student_id = ?',
            (row['id'],), one=True
        )
        row['image_count'] = log['cnt'] if log else 0
        students_with_counts.append(row)

    return render_template('view_students.html', students=students_with_counts)


@students_bp.route('/delete_student/<int:student_id>', methods=['POST'])
@login_required
def delete_student(student_id):
    """Soft-delete a student (CASCADE removes attendance records too)."""
    student = query_db('SELECT * FROM students WHERE id = ?', (student_id,), one=True)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students.view_students'))

    execute_db('DELETE FROM students WHERE id = ?', (student_id,))
    flash(f'Student {student["name"]} removed.', 'info')
    return redirect(url_for('students.view_students'))


@students_bp.route('/student/<int:student_id>/marks')
@login_required
def student_marks(student_id):
    """View marks profile of a student."""
    student = query_db('SELECT * FROM students WHERE id = ?', (student_id,), one=True)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students.view_students'))
    
    marks = query_db('SELECT * FROM marks WHERE student_id = ? ORDER BY date_recorded DESC', (student_id,))

    return render_template('student_marks.html', student=student, marks=marks)


@students_bp.route('/student/<int:student_id>/attendance')
@login_required
def student_attendance(student_id):
    """View attendance chart of a student."""
    student = query_db('SELECT * FROM students WHERE id = ?', (student_id,), one=True)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students.view_students'))
    
    attendance_records = query_db('SELECT status, COUNT(*) as count FROM attendance WHERE student_id = ? GROUP BY status', (student_id,))
    present_count = 0
    absent_count = 0
    if attendance_records:
        for rec in attendance_records:
            if rec['status'] == 'Present':
                present_count = rec['count']
            else:
                absent_count = rec['count']

    return render_template('student_attendance.html', student=student, present_count=present_count, absent_count=absent_count)


@students_bp.route('/student/<int:student_id>/add_mark', methods=['POST'])
@login_required
def add_mark(student_id):
    """Add a new marks record for the student."""
    subject = request.form.get('subject', '').strip()
    marks_obtained = request.form.get('marks_obtained', type=float)
    total_marks = request.form.get('total_marks', type=float)
    
    if not subject or marks_obtained is None or total_marks is None:
        flash('Please provide subject, marks obtained, and total marks.', 'danger')
        return redirect(url_for('students.student_marks', student_id=student_id))
        
    execute_db('INSERT INTO marks (student_id, subject, marks_obtained, total_marks) VALUES (?, ?, ?, ?)', 
               (student_id, subject, marks_obtained, total_marks))
    flash('Marks added successfully.', 'success')
    return redirect(url_for('students.student_marks', student_id=student_id))


@students_bp.route('/student/<int:student_id>/send_marks_email', methods=['POST'])
@login_required
def send_marks_email(student_id):
    """Send exam results to parent via simulated email/SMS."""
    student = query_db('SELECT * FROM students WHERE id = ?', (student_id,), one=True)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students.view_students'))
        
    marks = query_db('SELECT * FROM marks WHERE student_id = ? ORDER BY date_recorded DESC', (student_id,))
    if not marks:
        flash('No marks to send.', 'warning')
        return redirect(url_for('students.student_marks', student_id=student_id))
        
    success = send_exam_results(student, marks)
    if success:
        flash('Results sent to parent successfully!', 'success')
    else:
        flash('Could not send results. Parent email/phone is missing.', 'danger')
        
    return redirect(url_for('students.student_marks', student_id=student_id))
