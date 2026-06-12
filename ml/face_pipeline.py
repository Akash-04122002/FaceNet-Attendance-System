"""
ml/face_pipeline.py
===================
Complete deep-learning pipeline:

  align_all_faces()        – MTCNN face detection + alignment
  build_embeddings()       – FaceNet 512-D embedding extraction
  train_svm()              – SVM classifier training
  recognize_faces_in_image() – predict identities in a photo
  recognize_faces_in_video() – predict identities across video frames

Dependencies:  mtcnn, tensorflow, scikit-learn, opencv-python, numpy, Pillow
"""

import os
import pickle
import logging
import numpy as np
import cv2
from PIL import Image

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
FACE_SIZE    = 160          # FaceNet expects 160×160 input
MIN_FACES    = 2            # minimum images per class to include in training
VIDEO_SKIP   = 15           # process every N-th frame for video inference


# ─────────────────────────────────────────────────────────────────────────────
# 1. Face Detection & Alignment (MTCNN)
# ─────────────────────────────────────────────────────────────────────────────

def get_mtcnn():
    """Lazy-load MTCNN detector (heavy import, do once)."""
    from mtcnn import MTCNN
    return MTCNN()


def detect_and_align(image_rgb: np.ndarray, detector) -> list[np.ndarray]:
    """
    Detect all faces in an RGB image and return aligned 160×160 crops.

    Parameters
    ----------
    image_rgb : H×W×3 numpy array (RGB)
    detector  : MTCNN instance

    Returns
    -------
    List of 160×160 RGB face crops (numpy arrays).
    """
    results = detector.detect_faces(image_rgb)
    faces   = []
    for res in results:
        confidence = res['confidence']
        if confidence < 0.90:
            continue
        x, y, w, h = res['box']
        x, y = max(0, x), max(0, y)
        face_crop = image_rgb[y:y+h, x:x+w]
        if face_crop.size == 0:
            continue
        face_pil  = Image.fromarray(face_crop).resize((FACE_SIZE, FACE_SIZE))
        faces.append(np.array(face_pil))
    return faces


def align_all_faces(raw_dir: str, aligned_dir: str) -> int:
    """
    Walk raw_dir/<roll_no>/*.jpg, detect faces, and save aligned crops
    to aligned_dir/<roll_no>/<index>.jpg.

    Returns total number of aligned faces saved.
    """
    detector  = get_mtcnn()
    total     = 0

    for roll_no in os.listdir(raw_dir):
        student_raw = os.path.join(raw_dir, roll_no)
        if not os.path.isdir(student_raw):
            continue

        student_aligned = os.path.join(aligned_dir, roll_no)
        os.makedirs(student_aligned, exist_ok=True)

        idx = 0
        for img_file in os.listdir(student_raw):
            img_path = os.path.join(student_raw, img_file)
            try:
                img     = cv2.imread(img_path)
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                faces   = detect_and_align(img_rgb, detector)
                for face in faces:
                    out_path = os.path.join(student_aligned, f'{idx:04d}.jpg')
                    Image.fromarray(face).save(out_path)
                    idx   += 1
                    total += 1
            except Exception as e:
                logger.warning(f'Skipping {img_path}: {e}')

        logger.info(f'  {roll_no}: {idx} aligned faces')

    return total


# ─────────────────────────────────────────────────────────────────────────────
# 2. FaceNet Embedding Extraction
# ─────────────────────────────────────────────────────────────────────────────

_facenet_session = None   # module-level cache

def load_facenet(model_path: str):
    """
    Load the FaceNet frozen graph (.pb) into a TF session.
    Returns the session and relevant tensors.
    """
    global _facenet_session
    if _facenet_session is not None:
        return _facenet_session

    import tensorflow as tf

    # TF2 compatibility – run in v1 graph mode
    tf.compat.v1.disable_eager_execution()
    graph = tf.compat.v1.Graph()
    with graph.as_default():
        graph_def = tf.compat.v1.GraphDef()
        with open(model_path, 'rb') as f:
            graph_def.ParseFromString(f.read())
        tf.compat.v1.import_graph_def(graph_def, name='')

    sess = tf.compat.v1.Session(graph=graph)
    images_placeholder    = graph.get_tensor_by_name('input:0')
    embeddings_tensor     = graph.get_tensor_by_name('embeddings:0')
    phase_train_placeholder = graph.get_tensor_by_name('phase_train:0')

    _facenet_session = (sess, images_placeholder, embeddings_tensor, phase_train_placeholder)
    return _facenet_session


def prewhiten(x: np.ndarray) -> np.ndarray:
    """Normalize pixel values (FaceNet-standard pre-processing)."""
    mean   = np.mean(x)
    std    = np.std(x)
    std_adj = np.maximum(std, 1.0 / np.sqrt(x.size))
    return (x - mean) / std_adj


def get_embedding(face_160: np.ndarray, model_path: str) -> np.ndarray:
    """
    Given a 160×160 RGB face crop, return a 512-D L2-normalised embedding.
    """
    sess, images_ph, embeddings_t, phase_train_ph = load_facenet(model_path)
    face = prewhiten(face_160.astype(np.float32))
    face = np.expand_dims(face, axis=0)   # (1, 160, 160, 3)
    feed = {images_ph: face, phase_train_ph: False}
    emb  = sess.run(embeddings_t, feed_dict=feed)
    return emb[0]   # (512,)


def build_embeddings(aligned_dir: str, model_path: str):
    """
    Walk aligned_dir/<roll_no>/*.jpg, compute embeddings, and return:
      X      – (N, 512) float32 array of embeddings
      y      – (N,) int array of class indices
      labels – list of roll_no strings (index → roll_no)

    Skips classes with fewer than MIN_FACES samples.
    """
    labels = sorted([
        d for d in os.listdir(aligned_dir)
        if os.path.isdir(os.path.join(aligned_dir, d))
    ])

    X_list, y_list = [], []

    for class_idx, roll_no in enumerate(labels):
        class_dir = os.path.join(aligned_dir, roll_no)
        files     = [f for f in os.listdir(class_dir)
                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if len(files) < MIN_FACES:
            logger.warning(f'Skipping {roll_no} (only {len(files)} images, need {MIN_FACES})')
            continue

        for img_file in files:
            img_path = os.path.join(class_dir, img_file)
            try:
                face = np.array(Image.open(img_path).convert('RGB').resize((FACE_SIZE, FACE_SIZE)))
                emb  = get_embedding(face, model_path)
                X_list.append(emb)
                y_list.append(class_idx)
            except Exception as e:
                logger.warning(f'Embedding failed for {img_path}: {e}')

    if not X_list:
        raise ValueError('No embeddings generated. Check dataset and FaceNet model.')

    return np.array(X_list), np.array(y_list), labels


# ─────────────────────────────────────────────────────────────────────────────
# 3. SVM Classifier Training
# ─────────────────────────────────────────────────────────────────────────────

def train_svm(X: np.ndarray, y: np.ndarray, labels: list[str], clf_path: str) -> str:
    """
    Train a linear SVM with probability estimates on the embeddings.
    Saves the classifier (+ label list) to clf_path as a .pkl file.

    Returns a summary string.
    """
    from sklearn.svm import SVC
    from sklearn.preprocessing import LabelEncoder, Normalizer
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import cross_val_score

    # L2-normalise embeddings before SVM
    normalizer = Normalizer(norm='l2')
    X_norm = normalizer.fit_transform(X)

    # Encode string labels → integers
    le = LabelEncoder()
    le.fit(labels)
    y_enc = le.transform([labels[i] for i in y])

    clf = SVC(kernel='linear', probability=True, C=1.0)
    clf.fit(X_norm, y_enc)

    # Cross-validation accuracy
    scores = cross_val_score(clf, X_norm, y_enc, cv=min(5, len(set(y_enc))))
    acc    = scores.mean()

    # Persist everything needed at inference time
    os.makedirs(os.path.dirname(clf_path), exist_ok=True)
    with open(clf_path, 'wb') as f:
        pickle.dump({'classifier': clf,
                     'label_encoder': le,
                     'normalizer': normalizer,
                     'class_names': labels}, f)

    msg = (f'{len(set(y_enc))} classes, {len(X)} samples, '
           f'CV accuracy: {acc:.1%}')
    logger.info(f'SVM trained: {msg}')
    return msg


# ─────────────────────────────────────────────────────────────────────────────
# 4. Inference helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_classifier(clf_path: str):
    """Load the saved classifier bundle from disk."""
    with open(clf_path, 'rb') as f:
        bundle = pickle.load(f)
    return bundle


def predict_face(face_160: np.ndarray, model_path: str, clf_path: str, threshold: float):
    """
    Given a 160×160 RGB face crop, return predicted roll_no or None
    if confidence is below threshold.
    """
    bundle     = load_classifier(clf_path)
    clf        = bundle['classifier']
    le         = bundle['label_encoder']
    normalizer = bundle['normalizer']
    labels     = bundle['class_names']

    emb     = get_embedding(face_160, model_path)
    emb_n   = normalizer.transform([emb])
    proba   = clf.predict_proba(emb_n)[0]
    best_idx = np.argmax(proba)
    best_prob = proba[best_idx]

    if best_prob < threshold:
        return None, best_prob

    roll_no = labels[le.classes_[best_idx]]
    return roll_no, best_prob


def recognize_faces_in_image(image_path: str, model_path: str,
                              clf_path: str, threshold: float) -> set:
    """
    Detect and recognise all faces in a single classroom image.
    Returns a set of roll_no strings for students recognised above threshold.
    """
    detector   = get_mtcnn()
    img        = cv2.imread(image_path)
    img_rgb    = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    faces      = detect_and_align(img_rgb, detector)
    recognised = set()

    for face in faces:
        roll_no, prob = predict_face(face, model_path, clf_path, threshold)
        if roll_no:
            recognised.add(roll_no)
            logger.info(f'Recognised {roll_no} ({prob:.1%})')

    return recognised


def recognize_faces_in_video(video_path: str, model_path: str,
                              clf_path: str, threshold: float) -> set:
    """
    Process a video file frame-by-frame (every VIDEO_SKIP frames).
    Returns a set of all roll_nos recognised with sufficient confidence.
    """
    detector   = get_mtcnn()
    cap        = cv2.VideoCapture(video_path)
    recognised = set()
    frame_num  = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_num += 1
        if frame_num % VIDEO_SKIP != 0:
            continue

        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces   = detect_and_align(img_rgb, detector)
        for face in faces:
            roll_no, prob = predict_face(face, model_path, clf_path, threshold)
            if roll_no:
                recognised.add(roll_no)

    cap.release()
    return recognised
