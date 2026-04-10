# Reporting functions
# Handles CSV import/export and text report generation

import csv
import io
from models import Grade, Student, Module
from database import get_db


# Export grades to CSV
# If student_id is provided, export only that student's grades
def export_grades_csv(student_id=None):
    if student_id:
        grades = Grade.get_by_student(student_id)
        rows = [dict(g) for g in grades]
    else:
        grades = Grade.get_all()
        rows = [dict(g) for g in grades]

    # Create in-memory CSV output
    output = io.StringIO()

    # Return empty output if no grade rows exist
    if not rows:
        return output.getvalue()

    # Define CSV column order
    fieldnames = ['student_number', 'student_name', 'module_code', 'module_name',
                  'assessment_name', 'score', 'max_score', 'date']

    # Write CSV data
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)

    return output.getvalue()


# Import grades from CSV file
# Expected columns: student_number, module_code, assessment_name, score, max_score, date
def import_grades_csv(file_stream):
    db = get_db()

    # Wrap uploaded file stream for text reading
    wrapper = io.TextIOWrapper(file_stream, encoding='utf-8')
    reader = csv.DictReader(wrapper)

    # Validate required headers before processing rows
    required = {'student_number', 'module_code', 'assessment_name', 'score', 'date'}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        missing = required - set(reader.fieldnames or [])
        return 0, [f"Missing required columns: {', '.join(missing)}"]

    success = 0
    errors = []

    # Process each CSV row
    for i, row in enumerate(reader, start=2):
        try:
            # Find matching student by student number
            student = db.execute('''
                SELECT s.id FROM students s WHERE s.student_number = ?
            ''', (row['student_number'].strip(),)).fetchone()

            if not student:
                errors.append(f"Row {i}: Student '{row['student_number']}' not found.")
                continue

            # Find matching module by module code
            module = db.execute("SELECT id FROM modules WHERE code = ?",
                                (row['module_code'].strip(),)).fetchone()

            if not module:
                errors.append(f"Row {i}: Module '{row['module_code']}' not found.")
                continue

            # Read and clean grade values
            score = float(row['score'])
            max_score = float(row['max_score']) if row.get('max_score', '').strip() else 100.0
            date = row['date'].strip()
            assessment = row['assessment_name'].strip()

            # Insert grade record
            db.execute('''
                INSERT INTO grades (student_id, module_id, assessment_name, score, max_score, date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (student['id'], module['id'], assessment, score, max_score, date))

            success += 1

        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    # Save imported records
    db.commit()
    db.close()

    return success, errors


# Import student records from CSV file
# Expected columns: student_number, full_name, username, course, year
def import_students_csv(file_stream):
    from werkzeug.security import generate_password_hash

    db = get_db()

    # Wrap uploaded file stream for text reading
    wrapper = io.TextIOWrapper(file_stream, encoding='utf-8')
    reader = csv.DictReader(wrapper)

    # Validate required headers
    required = {'student_number', 'full_name', 'username'}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        missing = required - set(reader.fieldnames or [])
        return 0, [f"Missing required columns: {', '.join(missing)}"]

    success = 0
    errors = []

    # Process each CSV row
    for i, row in enumerate(reader, start=2):
        try:
            # Read and clean student values
            username = row['username'].strip()
            full_name = row['full_name'].strip()
            student_number = row['student_number'].strip()
            course = row.get('course', 'Computer Science').strip() or 'Computer Science'
            year = int(row['year'].strip()) if row.get('year', '').strip() else 1

            # Check for duplicate usernames
            if db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone():
                errors.append(f"Row {i}: Username '{username}' already exists.")
                continue

            # Check for duplicate student numbers
            if db.execute("SELECT id FROM students WHERE student_number=?", (student_number,)).fetchone():
                errors.append(f"Row {i}: Student number '{student_number}' already exists.")
                continue

            # Insert new student user account
            db.execute(
                "INSERT INTO users (username, password, role, full_name) VALUES (?,?,?,?)",
                (username, generate_password_hash('password'), 'student', full_name)
            )

            # Get ID of inserted user
            user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Insert linked student record
            db.execute(
                "INSERT INTO students (user_id, student_number, course, year) VALUES (?,?,?,?)",
                (user_id, student_number, course, year)
            )

            success += 1

        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    # Save imported records
    db.commit()
    db.close()

    return success, errors


# Generate plain-text report for one student
# Includes averages, attendance, risk status, and module breakdown
def generate_student_report(student_id):
    from analytics import get_student_avg, get_attendance_rate, is_at_risk, get_module_averages

    # Get student and analytics data
    student = Student.get_by_id(student_id)
    avg = get_student_avg(student_id)
    attendance = get_attendance_rate(student_id)
    at_risk, reasons = is_at_risk(student_id)
    module_avgs = get_module_averages(student_id)

    # Build report lines
    lines = [
        f"=== Student Report: {student['full_name']} ({student['student_number']}) ===",
        f"Course: {student['course']} | Year: {student['year']}",
        f"Overall Average Grade: {avg}%",
        f"Attendance Rate: {attendance}%",
        f"At Risk: {'YES' if at_risk else 'No'}",
    ]

    # Add risk reasons if present
    if reasons:
        lines.append("Risk Reasons:")
        for r in reasons:
            lines.append(f"  - {r}")

    # Add module averages
    lines.append("\nModule Breakdown:")
    if module_avgs:
        for code, data in module_avgs.items():
            lines.append(f"  {code} - {data['name']}: {data['avg']}%")
    else:
        lines.append("  No module data available.")

    return "\n".join(lines)