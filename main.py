from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from werkzeug.security import check_password_hash
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from database import init_db
from models import User, Student, Grade, Module, Attendance
from analytics import (get_student_avg, get_attendance_rate, is_at_risk,
                       get_all_students_summary, get_grade_distribution,
                       get_class_performance, get_performance_trend,
                       get_module_averages)
from reporting import export_grades_csv, import_grades_csv, import_students_csv, generate_student_report
from utils import login_required, teacher_required, grade_label, grade_colour

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.secret_key = 'las-secret-key-change-in-production'

# ─── Auth ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = User.get_by_username(username)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── Dashboard ───────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    if session['role'] == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))

@app.route('/teacher/dashboard')
@teacher_required
def teacher_dashboard():
    students = get_all_students_summary()
    at_risk_students = [s for s in students if s['at_risk']]
    class_perf = get_class_performance()

    # Chart data - class averages per module
    module_labels = [r['code'] for r in class_perf]
    module_avgs = [r['avg_score'] for r in class_perf]

    # Grade distribution across all students
    all_avgs = [s['avg_grade'] for s in students]
    student_names = [s['name'].split()[0] for s in students]

    return render_template('teacher_dashboard.html',
        students=students,
        at_risk_students=at_risk_students,
        class_perf=class_perf,
        module_labels=json.dumps(module_labels),
        module_avgs=json.dumps(module_avgs),
        student_names=json.dumps(student_names),
        all_avgs=json.dumps(all_avgs),
        grade_label=grade_label,
        grade_colour=grade_colour
    )

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    student = Student.get_by_user_id(session['user_id'])
    if not student:
        flash('Student record not found.', 'danger')
        return redirect(url_for('login'))

    avg = get_student_avg(student['id'])
    attendance = get_attendance_rate(student['id'])
    at_risk, reasons = is_at_risk(student['id'])
    module_avgs = get_module_averages(student['id'])
    dates, scores = get_performance_trend(student['id'])

    return render_template('student_dashboard.html',
        student=student,
        avg=avg,
        attendance=attendance,
        at_risk=at_risk,
        reasons=reasons,
        module_avgs=module_avgs,
        trend_dates=json.dumps(dates),
        trend_scores=json.dumps(scores),
        grade_label=grade_label,
        grade_colour=grade_colour
    )

# ─── Student detail (teacher view) ───────────────────────────────────────────

@app.route('/teacher/student/<int:student_id>')
@teacher_required
def student_detail(student_id):
    student = Student.get_by_id(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('teacher_dashboard'))

    avg = get_student_avg(student_id)
    attendance = get_attendance_rate(student_id)
    at_risk, reasons = is_at_risk(student_id)
    module_avgs = get_module_averages(student_id)
    grades = Grade.get_by_student(student_id)
    att_summary = Attendance.get_summary_by_student(student_id)
    dates, scores = get_performance_trend(student_id)
    labels, grade_scores = get_grade_distribution(student_id)

    return render_template('student_detail.html',
        student=student,
        avg=avg,
        attendance=attendance,
        at_risk=at_risk,
        reasons=reasons,
        module_avgs=module_avgs,
        grades=grades,
        att_summary=att_summary,
        trend_dates=json.dumps(dates),
        trend_scores=json.dumps(scores),
        bar_labels=json.dumps(labels),
        bar_scores=json.dumps(grade_scores),
        grade_label=grade_label,
        grade_colour=grade_colour
    )

# ─── CSV Import / Export ─────────────────────────────────────────────────────

@app.route('/teacher/import/students', methods=['GET', 'POST'])
@teacher_required
def import_students():
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file or file.filename == '':
            flash('Please select a CSV file.', 'warning')
            return redirect(request.url)
        success, errors = import_students_csv(file.stream)
        flash(f'Added {success} student(s) successfully.', 'success')
        for err in errors:
            flash(err, 'danger')
        return redirect(url_for('teacher_dashboard'))
    return render_template('import_students.html')

@app.route('/teacher/import', methods=['GET', 'POST'])
@teacher_required
def import_csv():
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file or file.filename == '':
            flash('Please select a CSV file.', 'warning')
            return redirect(request.url)
        success, errors = import_grades_csv(file.stream)
        flash(f'Imported {success} grade(s) successfully.', 'success')
        for err in errors:
            flash(err, 'danger')
        return redirect(url_for('teacher_dashboard'))
    return render_template('import_csv.html')

@app.route('/teacher/export')
@teacher_required
def export_csv():
    csv_data = export_grades_csv()
    return Response(csv_data, mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=grades_export.csv'})

@app.route('/teacher/export/<int:student_id>')
@teacher_required
def export_student_csv(student_id):
    student = Student.get_by_id(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('teacher_dashboard'))
    csv_data = export_grades_csv(student_id)
    filename = f"{student['student_number']}_grades.csv"
    return Response(csv_data, mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={filename}'})

@app.route('/teacher/report/<int:student_id>')
@teacher_required
def download_report(student_id):
    report = generate_student_report(student_id)
    student = Student.get_by_id(student_id)
    filename = f"{student['student_number']}_report.txt"
    return Response(report, mimetype='text/plain',
                    headers={'Content-Disposition': f'attachment; filename={filename}'})

# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    app.run(debug=True)