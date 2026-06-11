import logging
import datetime

logger = logging.getLogger(__name__)

def simulate_send_email(to_email, to_phone, subject, body):
    """
    Simulates sending an email or SMS by printing it to the terminal with a beautiful format.
    In a production environment, this function would use smtplib or an API like Twilio/SendGrid.
    """
    if not to_email and not to_phone:
        logger.warning("No parent email or phone provided for notification.")
        return False
        
    print("\n" + "="*60)
    print("📧 [SIMULATED NOTIFICATION DISPATCH]")
    print(f"Time:    {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"To:      {to_email or 'No Email'} | Phone: {to_phone or 'No Phone'}")
    print(f"Subject: {subject}")
    print("-" * 60)
    print(body)
    print("=" * 60 + "\n")
    
    return True

def send_absent_notification(student, date_str):
    student_dict = dict(student)
    subject = f"Attendance Alert: {student_dict['name']} is Absent"
    body = f"""Dear Parent/Guardian,

This is to inform you that your ward, {student_dict['name']} (Roll No: {student_dict['roll_no']}), was marked ABSENT for the classes on {date_str}.

If you have any questions or concerns, please contact the department office.

Regards,
FaceNet Attendance System
"""
    return simulate_send_email(student_dict.get('parent_email'), student_dict.get('parent_phone'), subject, body)


def send_exam_results(student, marks_records):
    student_dict = dict(student)
    subject = f"Exam Results Published: {student_dict['name']}"
    
    body = f"Dear Parent/Guardian,\n\nThe recent exam results for {student_dict['name']} (Roll No: {student_dict['roll_no']}) have been published. Here is the summary:\n\n"
    
    for mark in marks_records:
        percentage = (mark['marks_obtained'] / mark['total_marks']) * 100
        body += f" - {mark['subject']}: {mark['marks_obtained']} / {mark['total_marks']} ({percentage:.1f}%)\n"
        
    body += "\nFor detailed feedback, please feel free to reach out to the class teacher.\n\nRegards,\nFaceNet Attendance System"
    
    return simulate_send_email(student_dict.get('parent_email'), student_dict.get('parent_phone'), subject, body)
