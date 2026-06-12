"""
routes/upload.py
================
Handles:
  /upload_dataset  – upload training images for a student
  /train_model     – run MTCNN alignment + FaceNet embedding + SVM training
"""

import os
import pickle
from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, current_app, jsonify)
from werkzeug.utils import secure_filename
from database.db import query_db, execute_db
from routes.auth import login_required

upload_bp = Blueprint('upload', __name__)


def _allowed_image(filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext in current_app.config['ALLOWED_IMAGE_EXTENSIONS']


# ─────────────────────────────────────────────────────────────────────────────

@upload_bp.route('/upload_dataset', methods=['GET', 'POST'])
@login_required
def upload_dataset():
    """Upload multiple training images for a specific student."""
    students = query_db('SELECT id, name, roll_no FROM students ORDER BY name')

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        images     = request.files.getlist('images')

        if not student_id:
            flash('Please select a student.', 'danger')
            return render_template('upload.html', students=students)

        student = query_db('SELECT * FROM students WHERE id = ?', (student_id,), one=True)
        if not student:
            flash('Student not found.', 'danger')
            return render_template('upload.html', students=students)

        # Save images to dataset/raw/<roll_no>/
        raw_dir = os.path.join(current_app.config['DATASET_RAW_DIR'], student['roll_no'])
        os.makedirs(raw_dir, exist_ok=True)

        saved = 0
        for img in images:
            if img and img.filename and _allowed_image(img.filename):
                filename = secure_filename(f"{saved+1:04d}_{img.filename}")
                img.save(os.path.join(raw_dir, filename))
                saved += 1

        if saved == 0:
            flash('No valid images uploaded. Accepted: jpg, jpeg, png.', 'warning')
            return render_template('upload.html', students=students)

        # Log the upload
        execute_db(
            'INSERT INTO dataset_logs (student_id, image_count) VALUES (?, ?)',
            (student_id, saved)
        )
        flash(f'{saved} image(s) uploaded for {student["name"]}. '
              'Now click "Train Model" to update the classifier.', 'success')
        return redirect(url_for('upload.upload_dataset'))

    return render_template('upload.html', students=students)


@upload_bp.route('/train_model', methods=['POST'])
@login_required
def train_model():
    """
    Full training pipeline:
      1. Detect & align faces with MTCNN (writes to dataset/aligned/)
      2. Generate 512-D FaceNet embeddings for every aligned face
      3. Train an SVM classifier on the embeddings
      4. Save classifier.pkl to model/
    """
    from ml.face_pipeline import align_all_faces, build_embeddings, train_svm

    raw_dir     = current_app.config['DATASET_RAW_DIR']
    aligned_dir = current_app.config['DATASET_ALIGNED_DIR']
    model_dir   = current_app.config['MODEL_DIR']
    facenet_pb  = current_app.config['FACENET_MODEL_PATH']
    clf_path    = current_app.config['CLASSIFIER_PATH']

    # Step 1 – align faces
    aligned_count = align_all_faces(raw_dir, aligned_dir)
    if aligned_count == 0:
        flash('No faces detected in uploaded images. '
              'Please upload clearer photos.', 'danger')
        return redirect(url_for('upload.upload_dataset'))

    # Step 2 & 3 – embeddings + SVM
    ok, msg = build_embeddings_and_train(
        aligned_dir, facenet_pb, clf_path, model_dir
    )
    if ok:
        flash(f'Model trained successfully! ({msg})', 'success')
    else:
        flash(f'Training error: {msg}', 'danger')

    return redirect(url_for('upload.upload_dataset'))


def build_embeddings_and_train(aligned_dir, facenet_pb, clf_path, model_dir):
    """Wrapper that calls ml/face_pipeline.py functions."""
    try:
        from ml.face_pipeline import build_embeddings, train_svm
        X, y, labels = build_embeddings(aligned_dir, facenet_pb)
        if len(set(y)) < 2:
            return False, 'Need at least 2 students with face data to train.'
        msg = train_svm(X, y, labels, clf_path)
        return True, msg
    except FileNotFoundError as e:
        return False, f'FaceNet model not found: {e}. Download facenet.pb and place it in /model/.'
    except Exception as e:
        return False, str(e)
