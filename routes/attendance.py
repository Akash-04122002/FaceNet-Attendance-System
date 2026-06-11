"""
routes/attendance.py
====================
Handles:
  /dashboard          – overview page
  /upload_classroom   – upload classroom image/video frame
  /mark_attendance    – run recognition + store records
  /view_attendance    – paginated attendance log
  /download_report    – generate and serve Excel report
"""

import os
import datetime
from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, current_app,
                   send_file, jsonify)
from werkzeug.utils import secure_filename
from database.db import query_db, execute_db
from routes.auth import login_required
from utils.email_utils import send_absent_notification

attendance_bp = Blueprint('attendance', __name__)

UPLOAD_TEMP = 'static/uploads/classroom'


def _allowed_file(filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    allowed = (current_app.config['ALLOWED_IMAGE_EXTENSIONS'] |
               current_app.config['ALLOWED_VIDEO_EXTENSIONS'])
    return ext in allowed


# ─────────────────────────────────────────────────────────────────────────────

@attendance_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with summary statistics."""
    total_students = query_db('SELECT COUNT(*) AS c FROM students', one=True)['c']
    today          = datetime.date.today().isoformat()
    today_present  = query_db(
        "SELECT COUNT(*) AS c FROM attendance WHERE date = ? AND status = 'Present'",
        (today,), one=True
    )['c']
    total_records  = query_db('SELECT COUNT(*) AS c FROM attendance', one=True)['c']
    recent         = query_db(
        '''SELECT a.date, a.time, a.status, s.name, s.roll_no
           FROM attendance a
           JOIN students s ON a.student_id = s.id
           ORDER BY a.date DESC, a.time DESC LIMIT 10'''
    )
    
    # Advanced Analytics
    # 1. Department-wise attendance percentage
    dept_stats = query_db('''
        SELECT s.department, 
               COUNT(*) as total, 
               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        GROUP BY s.department
    ''')
    
    dept_labels = []
    dept_percentages = []
    if dept_stats:
        for row in dept_stats:
            dept_labels.append(row['department'])
            if row['total'] > 0:
                dept_percentages.append(round((row['present'] / row['total']) * 100, 1))
            else:
                dept_percentages.append(0)
                
    # 2. Daily Attendance Trend (Last 7 Days)
    import json
    thirty_days_ago = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    trend_stats = query_db('''
        SELECT date, 
               SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present,
               SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent
        FROM attendance
        WHERE date >= ?
        GROUP BY date
        ORDER BY date ASC
    ''', (thirty_days_ago,))
    
    trend_labels = []
    trend_present = []
    trend_absent = []
    if trend_stats:
        for row in trend_stats:
            trend_labels.append(row['date'])
            trend_present.append(row['present'])
            trend_absent.append(row['absent'])

    return render_template(
        'dashboard.html',
        total_students=total_students,
        today_present=today_present,
        total_records=total_records,
        recent=recent,
        today=today,
        dept_labels=json.dumps(dept_labels),
        dept_percentages=json.dumps(dept_percentages),
        trend_labels=json.dumps(trend_labels),
        trend_present=json.dumps(trend_present),
        trend_absent=json.dumps(trend_absent)
    )


@attendance_bp.route('/upload_classroom', methods=['GET', 'POST'])
@login_required
def upload_classroom():
    """Upload a classroom image/video for recognition."""
    if request.method == 'POST':
        webcam_data = request.form.get('webcam_image')
        
        if webcam_data:
            import base64
            header, encoded = webcam_data.split(",", 1)
            data = base64.b64decode(encoded)
            filename = f"webcam_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            save_dir = os.path.join(current_app.root_path, UPLOAD_TEMP)
            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, filename)
            with open(file_path, "wb") as f:
                f.write(data)
            ext = 'jpg'
        else:
            file = request.files.get('classroom_file')
            if not file or not file.filename:
                flash('No file selected.', 'danger')
                return render_template('upload_classroom.html')
    
            if not _allowed_file(file.filename):
                flash('Invalid file type. Upload JPG/PNG image or MP4/AVI video.', 'danger')
                return render_template('upload_classroom.html')
    
            save_dir = os.path.join(current_app.root_path, UPLOAD_TEMP)
            os.makedirs(save_dir, exist_ok=True)
            filename  = secure_filename(file.filename)
            file_path = os.path.join(save_dir, filename)
            file.save(file_path)
            ext = filename.rsplit('.', 1)[-1].lower()

        # Determine extension type
        rel_path = f'{UPLOAD_TEMP}/{filename}'

        return render_template(
            'upload_classroom.html',
            uploaded=True,
            file_path=rel_path,
            file_ext=ext,
            filename=filename
        )

    return render_template('upload_classroom.html')


@attendance_bp.route('/mark_attendance', methods=['POST'])
@login_required
def mark_attendance():
    """
    Run the FaceNet recognition pipeline on the uploaded file
    and persist attendance records.
    """
    filename    = request.form.get('filename')
    target_date = request.form.get('date', datetime.date.today().isoformat())
    target_time = request.form.get('time', datetime.datetime.now().strftime('%H:%M:%S'))

    if not filename:
        flash('No file to process.', 'danger')
        return redirect(url_for('attendance.upload_classroom'))

    clf_path   = current_app.config['CLASSIFIER_PATH']
    facenet_pb = current_app.config['FACENET_MODEL_PATH']

    if not os.path.exists(clf_path):
        flash('Classifier not found. Please upload student images and train the model first.', 'warning')
        return redirect(url_for('upload.upload_dataset'))

    file_path = os.path.join(current_app.root_path, UPLOAD_TEMP, filename)
    ext       = filename.rsplit('.', 1)[-1].lower()

    # ── Run recognition ───────────────────────────────────────────────────────
    try:
        from ml.face_pipeline import recognize_faces_in_image, recognize_faces_in_video
        if ext in current_app.config['ALLOWED_VIDEO_EXTENSIONS']:
            recognized = recognize_faces_in_video(file_path, facenet_pb, clf_path,
                                                   current_app.config['RECOGNITION_THRESHOLD'])
        else:
            recognized = recognize_faces_in_image(file_path, facenet_pb, clf_path,
                                                   current_app.config['RECOGNITION_THRESHOLD'])
    except Exception as e:
        flash(f'Recognition error: {e}', 'danger')
        return redirect(url_for('attendance.upload_classroom'))

    # ── Mark attendance ───────────────────────────────────────────────────────
    marked_present = []
    marked_absent = []
    
    all_students = query_db('SELECT * FROM students')
    
    for student in all_students:
        status = 'Present' if student['roll_no'] in recognized else 'Absent'
        
        # Avoid duplicate entry for same student on same date
        existing = query_db(
            'SELECT id FROM attendance WHERE student_id = ? AND date = ?',
            (student['id'], target_date), one=True
        )
        if not existing:
            execute_db(
                'INSERT INTO attendance (student_id, date, time, status) VALUES (?, ?, ?, ?)',
                (student['id'], target_date, target_time, status)
            )
            if status == 'Present':
                marked_present.append(student['name'])
            else:
                marked_absent.append(student['name'])
                send_absent_notification(student, target_date)

    if marked_present or marked_absent:
        msg = f'Attendance marked: {len(marked_present)} Present, {len(marked_absent)} Absent.'
        flash(msg, 'success')
    else:
        flash('No new students to mark or all already marked.', 'info')

    # Auto-generate Excel report
    report_path = _generate_excel_report(target_date)
    if report_path:
        flash(f'Excel report generated: {os.path.basename(report_path)}', 'info')

    return redirect(url_for('attendance.view_attendance'))


@attendance_bp.route('/view_attendance')
@login_required
def view_attendance():
    """Paginated attendance log with date filter."""
    date_filter = request.args.get('date', '')
    dept_filter = request.args.get('department', '')
    page        = int(request.args.get('page', 1))
    per_page    = 20
    offset      = (page - 1) * per_page

    base_q  = '''SELECT a.id, a.date, a.time, a.status,
                        s.name, s.roll_no, s.department
                 FROM attendance a
                 JOIN students s ON a.student_id = s.id '''
    filters = []
    params  = []

    if date_filter:
        filters.append('a.date = ?')
        params.append(date_filter)
    if dept_filter:
        filters.append('s.department LIKE ?')
        params.append(f'%{dept_filter}%')

    where = ('WHERE ' + ' AND '.join(filters)) if filters else ''
    count_q = f'SELECT COUNT(*) AS c FROM attendance a JOIN students s ON a.student_id = s.id {where}'
    total   = query_db(count_q, params, one=True)['c']

    rows = query_db(
        f'{base_q} {where} ORDER BY a.date DESC, a.time DESC LIMIT ? OFFSET ?',
        params + [per_page, offset]
    )

    departments = [r['department'] for r in
                   query_db('SELECT DISTINCT department FROM students ORDER BY department')]

    return render_template(
        'attendance_report.html',
        records=rows,
        date_filter=date_filter,
        dept_filter=dept_filter,
        page=page,
        per_page=per_page,
        total=total,
        departments=departments
    )


@attendance_bp.route('/download_report')
@login_required
def download_report():
    """Generate Excel report for a given date and serve as download."""
    date_str = request.args.get('date', datetime.date.today().isoformat())
    path     = _generate_excel_report(date_str)
    if path and os.path.exists(path):
        return send_file(path, as_attachment=True,
                         download_name=os.path.basename(path))
    flash('No attendance data found for the selected date.', 'warning')
    return redirect(url_for('attendance.view_attendance'))


@attendance_bp.route('/manual_attendance', methods=['GET', 'POST'])
@login_required
def manual_attendance():
    """Manual attendance with radio buttons."""
    if request.method == 'POST':
        target_date = request.form.get('date', datetime.date.today().isoformat())
        target_time = request.form.get('time', datetime.datetime.now().strftime('%H:%M:%S'))
        
        all_students = query_db('SELECT * FROM students')
        marked_present = 0
        marked_absent = 0
        
        for student in all_students:
            status = request.form.get(f"status_{student['id']}")
            if not status:
                continue
                
            existing = query_db(
                'SELECT id FROM attendance WHERE student_id = ? AND date = ?',
                (student['id'], target_date), one=True
            )
            if not existing:
                execute_db(
                    'INSERT INTO attendance (student_id, date, time, status) VALUES (?, ?, ?, ?)',
                    (student['id'], target_date, target_time, status)
                )
            else:
                execute_db(
                    'UPDATE attendance SET status = ?, time = ? WHERE id = ?',
                    (status, target_time, existing['id'])
                )
            
            if status == 'Present':
                marked_present += 1
            else:
                marked_absent += 1
                send_absent_notification(student, target_date)
                    
        flash(f'Attendance saved: {marked_present} Present, {marked_absent} Absent.', 'success')
        
        # Auto-generate Excel report
        report_path = _generate_excel_report(target_date)
        if report_path:
            flash(f'Excel report generated: {os.path.basename(report_path)}', 'info')
            
        return redirect(url_for('attendance.view_attendance'))
        
    students = query_db('SELECT * FROM students ORDER BY name')
    return render_template('manual_attendance.html', students=students)


# ─────────────────────────────────────────────────────────────────────────────
# Excel report helper
# ─────────────────────────────────────────────────────────────────────────────

def _generate_excel_report(date_str: str) -> str | None:
    """
    Create an Excel workbook for a given date.
    Columns: Name | Roll No | Department | Date | Time | Status
    Returns the absolute file path, or None if no records found.
    """
    import xlsxwriter

    records = query_db(
        '''SELECT s.name, s.roll_no, s.department,
                  a.date, a.time, a.status
           FROM attendance a
           JOIN students s ON a.student_id = s.id
           WHERE a.date = ?
           ORDER BY s.name''',
        (date_str,)
    )

    if not records:
        return None

    reports_dir = current_app.config['REPORTS_DIR']
    os.makedirs(reports_dir, exist_ok=True)
    file_name = f'attendance_{date_str}.xlsx'
    file_path = os.path.join(reports_dir, file_name)

    workbook  = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet('Attendance')

    # ── Formats ───────────────────────────────────────────────────────────────
    header_fmt = workbook.add_format({
        'bold': True, 'bg_color': '#1a3c5e', 'font_color': '#FFFFFF',
        'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 12
    })
    present_fmt = workbook.add_format({
        'bg_color': '#d4edda', 'border': 1, 'align': 'center'
    })
    absent_fmt = workbook.add_format({
        'bg_color': '#f8d7da', 'border': 1, 'align': 'center'
    })
    cell_fmt = workbook.add_format({'border': 1})

    # ── Header row ────────────────────────────────────────────────────────────
    headers = ['#', 'Name', 'Roll No', 'Department', 'Date', 'Time', 'Status']
    col_widths = [5, 25, 12, 20, 12, 10, 10]

    for col, (h, w) in enumerate(zip(headers, col_widths)):
        worksheet.write(0, col, h, header_fmt)
        worksheet.set_column(col, col, w)

    worksheet.set_row(0, 22)

    # ── Title ─────────────────────────────────────────────────────────────────
    title_fmt = workbook.add_format({
        'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'
    })
    worksheet.merge_range('A1:G1', f'Attendance Report – {date_str}', title_fmt)
    # Re-write headers on row 1 (merge_range overwrote row 0)
    for col, (h, w) in enumerate(zip(headers, col_widths)):
        worksheet.write(1, col, h, header_fmt)

    # ── Data rows ─────────────────────────────────────────────────────────────
    for row_num, rec in enumerate(records, start=2):
        status_fmt = present_fmt if rec['status'] == 'Present' else absent_fmt
        worksheet.write(row_num, 0, row_num - 1,       cell_fmt)
        worksheet.write(row_num, 1, rec['name'],        cell_fmt)
        worksheet.write(row_num, 2, rec['roll_no'],     cell_fmt)
        worksheet.write(row_num, 3, rec['department'],  cell_fmt)
        worksheet.write(row_num, 4, rec['date'],        cell_fmt)
        worksheet.write(row_num, 5, rec['time'],        cell_fmt)
        worksheet.write(row_num, 6, rec['status'],      status_fmt)

    # ── Summary ───────────────────────────────────────────────────────────────
    summary_row = len(records) + 3
    present_count = sum(1 for r in records if r['status'] == 'Present')
    absent_count  = len(records) - present_count
    worksheet.write(summary_row,     1, 'Total Present:', workbook.add_format({'bold': True}))
    worksheet.write(summary_row,     2, present_count)
    worksheet.write(summary_row + 1, 1, 'Total Absent:',  workbook.add_format({'bold': True}))
    worksheet.write(summary_row + 1, 2, absent_count)

    workbook.close()
    return file_path
