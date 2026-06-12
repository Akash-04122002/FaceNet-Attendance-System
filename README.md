# FaceNet Attendance System

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.0%2B-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Ready-blue)

A complete, automated Face Recognition Attendance Management System built with Python, Flask, FaceNet, MTCNN, and PostgreSQL. 

## 🌟 Features
- **Student Registration & Dataset Collection:** Upload and align training images for students.
- **Automated Face Recognition:** Uses advanced ML (MTCNN for face detection and FaceNet for facial embeddings) to recognize faces from images or webcam feeds.
- **Automated Attendance:** Automatically marks students as Present or Absent and records the data accurately into the database.
- **Absentee Email Notifications:** Automatically notifies parents when their child is absent.
- **Daily Excel Reports:** Generates structured `.xlsx` attendance reports for easy tracking.
- **Interactive Dashboard:** View total students, daily attendance metrics, and department-wise statistics.
- **PostgreSQL Database Integration:** Fully integrated with PostgreSQL for robust data management (with SQLite fallback).

## 🛠️ Technologies Used
- **Backend:** Python, Flask
- **Machine Learning:** TensorFlow, Keras, MTCNN, OpenCV, Scikit-learn
- **Database:** PostgreSQL (Primary), SQLite (Fallback)
- **Frontend:** HTML, CSS, JavaScript (Jinja2 Templates)

---

## 🚀 Setup and Installation

### 1. Prerequisites
- Python 3.8 or higher
- PostgreSQL Database Server

### 2. Clone the Repository
```bash
git clone https://github.com/yourusername/FaceNet-Attendance-System.git
cd FaceNet-Attendance-System
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup (PostgreSQL)
The application is pre-configured to run with PostgreSQL. You need to create the database and user locally:
1. Open your `psql` terminal or pgAdmin.
2. Run the following SQL commands:
   ```sql
   ALTER USER postgres WITH PASSWORD 'Yoki143@';
   CREATE DATABASE attendance_system;
   GRANT ALL PRIVILEGES ON DATABASE attendance_system TO postgres;
   ```
*(Note: If the PostgreSQL connection fails, the application will automatically fall back to using an SQLite database file `attendance.db` in the `database/` folder).*

### 5. Add the Pre-trained FaceNet Model
Download the pre-trained `facenet.pb` model file and place it inside the `model/` directory.

### 6. Run the Application
```bash
python app.py
```
The server will start at `http://127.0.0.1:5000`.

---

## 💻 Usage Instructions
1. **Login:** Access the web interface and log in using the default admin credentials.
   - **Username:** `admin`
   - **Password:** `admin123`
   *(Please change the password immediately after your first login).*
2. **Register Students:** Go to the students page to add their details (Roll No, Name, Department, Parent Email).
3. **Upload Dataset:** Navigate to the upload section, select the student, and upload their images. Click **Train Model** once uploads are complete.
4. **Mark Attendance:** Go to the Attendance page, upload a classroom photo or snap a webcam picture, and click to automatically recognize faces and mark attendance.

## 👨‍💻 Author
**Akash**