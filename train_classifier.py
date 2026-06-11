"""
train_classifier.py
===================
Standalone script to retrain the SVM classifier.
Run from project root:

    python train_classifier.py

Prerequisites:
  1. Student dataset images in  dataset/raw/<ROLL_NO>/*.jpg
  2. FaceNet model at           model/facenet.pb

Output:
  Aligned faces  → dataset/aligned/<ROLL_NO>/
  Classifier     → model/classifier.pkl
"""

import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ── Paths (edit if your layout differs) ──────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
RAW_DIR      = os.path.join(BASE_DIR, 'dataset', 'raw')
ALIGNED_DIR  = os.path.join(BASE_DIR, 'dataset', 'aligned')
FACENET_PB   = os.path.join(BASE_DIR, 'model', 'facenet.pb')
CLF_PATH     = os.path.join(BASE_DIR, 'model', 'classifier.pkl')


def main():
    # ── Sanity checks ─────────────────────────────────────────────────────────
    if not os.path.exists(RAW_DIR) or not os.listdir(RAW_DIR):
        logger.error('Raw dataset directory is empty: %s', RAW_DIR)
        sys.exit(1)

    if not os.path.exists(FACENET_PB):
        logger.error(
            'FaceNet model not found: %s\n'
            'Download from: https://github.com/davidsandberg/facenet '
            '(20180402-114759.pb) and rename to facenet.pb', FACENET_PB
        )
        sys.exit(1)

    from ml.face_pipeline import align_all_faces, build_embeddings, train_svm

    # ── Step 1: Detect & align faces ─────────────────────────────────────────
    logger.info('=== Step 1: Aligning faces with MTCNN ===')
    count = align_all_faces(RAW_DIR, ALIGNED_DIR)
    logger.info('Total aligned faces: %d', count)

    if count == 0:
        logger.error('No faces detected. Provide clearer, front-facing photos.')
        sys.exit(1)

    # ── Step 2: Extract FaceNet embeddings ────────────────────────────────────
    logger.info('=== Step 2: Extracting FaceNet embeddings ===')
    X, y, labels = build_embeddings(ALIGNED_DIR, FACENET_PB)
    logger.info('Embeddings shape: %s  |  Classes: %s', X.shape, labels)

    if len(set(y)) < 2:
        logger.error('Need at least 2 students with sufficient images to train SVM.')
        sys.exit(1)

    # ── Step 3: Train SVM ─────────────────────────────────────────────────────
    logger.info('=== Step 3: Training SVM classifier ===')
    summary = train_svm(X, y, labels, CLF_PATH)
    logger.info('Training complete: %s', summary)
    logger.info('Classifier saved to: %s', CLF_PATH)


if __name__ == '__main__':
    main()
