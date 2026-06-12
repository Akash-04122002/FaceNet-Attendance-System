import sys
import os

# Add root directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from database.db import query_db, execute_db

def test_database_connection_and_fallback():
    print("Starting Automated Database Test...")
    app = create_app()
    
    with app.app_context():
        # Test 1: Check which database is actually being used
        print("\nTest 1: Checking database connection...")
        try:
            # Check the default admin user that should be seeded
            admin = query_db("SELECT * FROM users WHERE username = 'admin'", one=True)
            if admin:
                print("[OK] Database connected successfully!")
                print(f"[OK] Found seeded admin user. Email: {admin['email']}")
            else:
                print("[FAIL] Database connected, but admin user not found.")
        except Exception as e:
            print(f"[FAIL] Connection test failed: {e}")
            
        # Test 2: Test INSERT operation
        print("\nTest 2: Testing INSERT operation...")
        try:
            test_student_name = "Automated Test Student"
            test_roll_no = "TEST1234"
            
            # Check if exists first and delete if it does
            existing = query_db("SELECT id FROM students WHERE roll_no = ?", (test_roll_no,), one=True)
            if existing:
                execute_db("DELETE FROM students WHERE id = ?", (existing['id'],))
                
            student_id = execute_db(
                "INSERT INTO students (name, roll_no, department) VALUES (?, ?, ?)",
                (test_student_name, test_roll_no, "Computer Science")
            )
            print(f"[OK] INSERT successful! New student ID: {student_id}")
            
        except Exception as e:
            print(f"[FAIL] INSERT test failed: {e}")
            
        # Test 3: Test SELECT and UPDATE operations
        print("\nTest 3: Testing SELECT and UPDATE operations...")
        try:
            if student_id:
                # Update the student
                execute_db(
                    "UPDATE students SET department = ? WHERE id = ?",
                    ("Information Technology", student_id)
                )
                
                # Select the student to verify
                student = query_db("SELECT * FROM students WHERE id = ?", (student_id,), one=True)
                if student and student['department'] == "Information Technology":
                    print(f"[OK] SELECT and UPDATE successful! Department changed to: {student['department']}")
                else:
                    print("[FAIL] UPDATE failed to save or SELECT failed to retrieve the updated data.")
                
                # Cleanup: Delete test data
                execute_db("DELETE FROM students WHERE id = ?", (student_id,))
                print("[OK] Test data cleaned up successfully.")
        except Exception as e:
            print(f"[FAIL] SELECT/UPDATE test failed: {e}")

    print("\nAutomated testing completed.")

if __name__ == "__main__":
    test_database_connection_and_fallback()
