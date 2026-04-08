import csv
import io
from models import Grade, Student, Module
from database import get_db

def export_grades_csv(student_id=None):
    """Export grades to CSV. If student_id given, export just that student."""
    if student_id:
        grades = Grade.get_by_student(student_id)
        rows = [dict(g) for g in grades]
    else:
        grades = Grade.get_all()
        rows = [dict(g) for g in grades]

    output = io.StringIO()
    if not rows:
        return output.getvalue()

    fieldnames = ['student_number', 'student_name', 'module_code', 'module_name',
                  'assessment_name', 'score', 'max_score', 'date']
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()

def import_grades_csv(file_stream):
    """
    Import grades from a CSV file.
    Expected columns: student_number, module_code, assessment_name, score, max_score, date
    Returns (success_count, errors)
    """
    db = get_db()
    wrapper = io.TextIOWrapper(file_stream, encoding='utf-8')
    reader = csv.DictReader(wrapper)

    # Validate headers before processing any rows
    required = {'student_number', 'module_code', 'assessment_name', 'score', 'date'}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        missing = required - set(reader.fieldnames or [])
        return 0, [f"Missing required columns: {', '.join(missing)}"]

    success = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        try:
            student = db.execute('''
                SELECT s.id FROM students s WHERE s.student_number = ?
            ''', (row['student_number'].strip(),)).fetchone()
            if not student:
                errors.append(f"Row {i}: Student '{row['student_number']}' not found.")
                continue

            module = db.execute("SELECT id FROM modules WHERE code = ?",
                                (row['module_code'].strip(),)).fetchone()
            if not module:
                errors.append(f"Row {i}: Module '{row['module_code']}' not found.")
                continue

            score = float(row['score'])
            max_score = float(row['max_score']) if row.get('max_score', '').strip() else 100.0
            date = row['date'].strip()
            assessment = row['assessment_name'].strip()

            db.execute('''
                INSERT INTO grades (student_id, module_id, assessment_name, score, max_score, date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (student['id'], module['id'], assessment, score, max_score, date))
            success += 1
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    db.commit()
    db.close()
    return success, errors

def import_students_csv(file_stream):
    """
    Import new students from a CSV file.
    Expected columns: student_number, full_name, username, course, year
    Password defaults to 'password' for all new students.
    Returns (success_count, errors)
    """
    from werkzeug.security import generate_password_hash
    db = get_db()
    wrapper = io.TextIOWrapper(file_stream, encoding='utf-8')
    reader = csv.DictReader(wrapper)

    required = {'student_number', 'full_name', 'username'}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        missing = required - set(reader.fieldnames or [])
        return 0, [f"Missing required columns: {', '.join(missing)}"]

    success = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        try:
            username       = row['username'].strip()
            full_name      = row['full_name'].strip()
            student_number = row['student_number'].strip()
            course         = row.get('course', 'Computer Science').strip() or 'Computer Science'
            year           = int(row['year'].strip()) if row.get('year', '').strip() else 1

            # Check duplicates
            if db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone():
                errors.append(f"Row {i}: Username '{username}' already exists.")
                continue
            if db.execute("SELECT id FROM students WHERE student_number=?", (student_number,)).fetchone():
                errors.append(f"Row {i}: Student number '{student_number}' already exists.")
                continue

            db.execute(
                "INSERT INTO users (username, password, role, full_name) VALUES (?,?,?,?)",
                (username, generate_password_hash('password'), 'student', full_name)
            )
            user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.execute(
                "INSERT INTO students (user_id, student_number, course, year) VALUES (?,?,?,?)",
                (user_id, student_number, course, year)
            )
            success += 1
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    db.commit()
    db.close()
    return success, errors


def generate_student_report(student_id):
    """Return a plain-text summary report for a student."""
    from analytics import get_student_avg, get_attendance_rate, is_at_risk, get_module_averages
    student = Student.get_by_id(student_id)
    avg = get_student_avg(student_id)
    attendance = get_attendance_rate(student_id)
    at_risk, reasons = is_at_risk(student_id)
    module_avgs = get_module_averages(student_id)

    lines = [
        f"=== Student Report: {student['full_name']} ({student['student_number']}) ===",
        f"Course: {student['course']} | Year: {student['year']}",
        f"Overall Average Grade: {avg}%",
        f"Attendance Rate: {attendance}%",
        f"At Risk: {'YES' if at_risk else 'No'}",
    ]
    if reasons:
        lines.append("Risk Reasons:")
        for r in reasons:
            lines.append(f"  - {r}")
    lines.append("\nModule Breakdown:")
    if module_avgs:
        for code, data in module_avgs.items():
            lines.append(f"  {code} - {data['name']}: {data['avg']}%")
    else:
        lines.append("  No module data available.")
    return "\n".join(lines)