# FaceNet Smart Attendance System
### Flask + Deep Learning + RDBMS | Final-Year Engineering Project

---

## 📁 Project Structure

```
facenet_attendance/
├── app.py                   ← Flask app factory & entry point
├── config.py                ← All configuration (DB, paths, thresholds)
├── requirements.txt
├── train_classifier.py      ← Standalone training script
│
├── routes/
│   ├── auth.py              ← /register  /login  /logout
│   ├── students.py          ← /add_student  /view_students  /delete_student
│   ├── attendance.py        ← /dashboard  /upload_classroom  /mark_attendance  /view_attendance  /download_report
│   └── upload.py            ← /upload_dataset  /train_model
│
├── ml/
│   └── face_pipeline.py     ← MTCNN + FaceNet + SVM full pipeline
│
├── database/
│   └── db.py                ← MySQL / SQLite connection + schema + helpers
│
├── templates/
│   ├── base.html            ← Sidebar layout
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── add_student.html
│   ├── view_students.html
│   ├── upload.html          ← Dataset upload + train
│   ├── upload_classroom.html
│   └── attendance_report.html
│
├── static/
│   ├── css/
│   ├── js/
│   └── uploads/
│
├── model/
│   ├── facenet.pb           ← Download separately (see below)
│   └── classifier.pkl       ← Generated after training
│
├── dataset/
│   ├── raw/                 ← <roll_no>/ folders with uploaded images
│   └── aligned/             ← 160×160 face crops from MTCNN
│
└── reports/                 ← Auto-generated Excel files
```

---

## ⚡ Quick Start

### 1. Clone & set up environment

```bash
git clone <repo-url>
cd facenet_attendance
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Download FaceNet model

Download the pre-trained FaceNet model (20180402-114759):

```
https://drive.google.com/file/d/1EXPBSXwTaqrSC0OhUdXNmKSh9qJUfNui/view
```

Extract and rename the `.pb` file to `facenet.pb`, place at:
```
model/facenet.pb
```

### 3. Configure database

**Option A – SQLite (default, zero config)**
Nothing to do. The database file is created automatically at `database/attendance.db`.

**Option B – MySQL**
```sql
CREATE DATABASE attendance_system;
```
Then edit `config.py`:
```python
DB_TYPE        = 'mysql'
MYSQL_HOST     = 'localhost'
MYSQL_USER     = 'root'
MYSQL_PASSWORD = 'your_password'
MYSQL_DB       = 'attendance_system'
```
Or use environment variables (recommended):
```bash
export DB_TYPE=mysql
export MYSQL_PASSWORD=your_password
```

### 4. Run the application

```bash
python app.py
```
Open http://localhost:5000

---

## 🗄️ Database Schema

```sql
-- Users (admin / teacher accounts)
CREATE TABLE users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    NOT NULL UNIQUE,
    email      TEXT    NOT NULL UNIQUE,
    password   TEXT    NOT NULL,          -- werkzeug hashed
    role       TEXT    NOT NULL DEFAULT 'teacher',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Students
CREATE TABLE students (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    roll_no    TEXT    NOT NULL UNIQUE,
    department TEXT    NOT NULL,
    image_path TEXT
);

-- Attendance records
CREATE TABLE attendance (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    date       DATE    NOT NULL,
    time       TIME    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'Present',
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- Dataset upload logs
CREATE TABLE dataset_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  INTEGER NOT NULL,
    image_count INTEGER NOT NULL DEFAULT 0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);
```

---

## 🔄 Workflow

```
1. Register teacher account  →  /register
2. Add students              →  /add_student
3. Upload face images        →  /upload_dataset  (20–50 per student)
4. Train classifier          →  click "Train Model" button
5. Take attendance           →  /upload_classroom → upload classroom photo/video
6. View & export             →  /view_attendance  →  Download Excel
```

---

## 🧠 AI Pipeline

```
Classroom Image
      │
      ▼
  [MTCNN]  ─── detect & align all faces → 160×160 crops
      │
      ▼
  [FaceNet] ── compute 512-D L2 embedding for each crop
      │
      ▼
  [SVM]    ─── predict class (roll_no) + confidence score
      │
      ▼
  threshold check  →  mark attendance in DB
```

| Component | Purpose |
|-----------|---------|
| MTCNN | Multi-task Cascaded CNN for face detection + landmark alignment |
| FaceNet | Deep CNN (Inception-ResNet-v1) for 512-D face embeddings |
| SVM | Linear Support Vector Machine with probability calibration |

---

## 🔧 Training Only (CLI)

```bash
# Place images in dataset/raw/<ROLL_NO>/
python train_classifier.py
```

---

## 📊 Excel Report Format

`reports/attendance_YYYY-MM-DD.xlsx`

| # | Name | Roll No | Department | Date | Time | Status |
|---|------|---------|------------|------|------|--------|
| 1 | Priya Sharma | CS2024001 | Computer Science | 2024-03-15 | 09:02:31 | Present |

- Color-coded: Present = green, Absent = red
- Summary row: total present / absent count

---

## 🛣️ API Routes

| Method | Route | Description |
|--------|-------|-------------|
| GET/POST | `/register` | User registration |
| GET/POST | `/login` | User login |
| GET | `/logout` | Clear session |
| GET | `/dashboard` | Overview stats |
| GET/POST | `/add_student` | Add student |
| GET | `/view_students` | List students |
| POST | `/delete_student/<id>` | Remove student |
| GET/POST | `/upload_dataset` | Upload training images |
| POST | `/train_model` | Retrain classifier |
| GET/POST | `/upload_classroom` | Upload classroom file |
| POST | `/mark_attendance` | Run recognition + mark |
| GET | `/view_attendance` | Paginated log + filter |
| GET | `/download_report` | Download Excel |

---

## 🔐 Security Features

- Passwords hashed with `werkzeug.security.generate_password_hash` (PBKDF2-SHA256)
- Flask session-based authentication with 8-hour lifetime
- `login_required` decorator on all protected routes
- CSRF-safe: POST-only for destructive actions
- File type validation for all uploads
- Parameterised SQL queries (no SQL injection)

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, Flask 3.x |
| AI | MTCNN, FaceNet (TF2), scikit-learn SVM |
| Database | MySQL 8.x (prod) / SQLite (dev) |
| Frontend | Bootstrap 5.3, Bootstrap Icons |
| Reports | XlsxWriter |
| Auth | Werkzeug security |
