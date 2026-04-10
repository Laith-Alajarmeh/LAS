from models import Grade, Attendance, Student
from database import get_db

# Named thresholds
# Easier to explain in portfolio and change later if needed
LOW_GRADE_THRESHOLD = 50
LOW_ATTENDANCE_THRESHOLD = 70
DECLINE_THRESHOLD = 15


# Convert grade row into percentage
# Uses max_score so calculations still work if assessments are not out of 100
def _pct(grade_row):
    """Convert a grade row to a percentage, respecting max_score."""
    max_score = grade_row['max_score'] or 100
    return (grade_row['score'] / max_score) * 100


# Calculate overall average grade for one student
# Returns average percentage across all assessments
def get_student_avg(student_id):
    grades = Grade.get_by_student(student_id)
    if not grades:
        return 0
    total_pct = sum(_pct(g) for g in grades)
    return round(total_pct / len(grades), 1)


# Calculate module averages for one student
# Groups grades by module and returns average percentage for each module
def get_module_averages(student_id):
    grades = Grade.get_by_student(student_id)
    modules = {}
    for g in grades:
        key = g['module_code']
        if key not in modules:
            modules[key] = {'name': g['module_name'], 'percentages': []}
        modules[key]['percentages'].append(_pct(g))

    if not modules:
        return {}

    return {
        k: {
            'name': v['name'],
            'avg': round(sum(v['percentages']) / len(v['percentages']), 1),
            'scores': [round(p, 1) for p in v['percentages']]
        }
        for k, v in modules.items()
    }


# Calculate attendance rate for one student
# Late attendance counts as half attendance
def get_attendance_rate(student_id):
    summary = Attendance.get_summary_by_student(student_id)
    if not summary or summary['total'] == 0:
        return 100
    rate = (summary['present'] + summary['late'] * 0.5) / summary['total'] * 100
    return round(rate, 1)


# Check if a student is at risk
# Risk is based on low grades, poor attendance, or declining performance
def is_at_risk(student_id):
    avg = get_student_avg(student_id)
    attendance = get_attendance_rate(student_id)
    reasons = []

    # Check low grade threshold
    if avg < LOW_GRADE_THRESHOLD:
        reasons.append(f"Low average grade ({avg}%)")

    # Check attendance threshold
    if attendance < LOW_ATTENDANCE_THRESHOLD:
        reasons.append(f"Poor attendance ({attendance}%)")

    # Check declining trend
    # Compare last 2 assessments with the 2 before them
    grades = Grade.get_by_student(student_id)
    if len(grades) >= 4:
        recent_avg = sum(_pct(g) for g in grades[-2:]) / 2
        earlier_avg = sum(_pct(g) for g in grades[-4:-2]) / 2
        drop = earlier_avg - recent_avg
        if drop > DECLINE_THRESHOLD:
            reasons.append(f"Declining performance (dropped {round(drop, 1)} points)")

    return len(reasons) > 0, reasons


# Generate summary data for all students
# Used mainly for teacher dashboard
def get_all_students_summary():
    students = Student.get_all()
    results = []

    for s in students:
        avg = get_student_avg(s['id'])
        attendance = get_attendance_rate(s['id'])
        at_risk, reasons = is_at_risk(s['id'])

        results.append({
            'id': s['id'],
            'name': s['full_name'],
            'student_number': s['student_number'],
            'course': s['course'],
            'avg_grade': avg,
            'attendance': attendance,
            'at_risk': at_risk,
            'risk_reasons': reasons
        })

    return results


# Get labels and scores for student grade chart
# Used for assessment breakdown visualisation
def get_grade_distribution(student_id):
    grades = Grade.get_by_student(student_id)
    labels = [f"{g['module_code']} - {g['assessment_name']}" for g in grades]
    scores = [round(_pct(g), 1) for g in grades]
    return labels, scores


# Calculate average class performance for each module
# Uses SQL to compute percentage averages across all students
def get_class_performance():
    """Average percentage score per module, respecting max_score."""
    db = get_db()
    rows = db.execute('''
        SELECT m.code, m.name,
               ROUND(AVG(g.score * 100.0 / g.max_score), 1) AS avg_score,
               COUNT(DISTINCT g.student_id) AS student_count
        FROM grades g JOIN modules m ON g.module_id = m.id
        GROUP BY m.id
    ''').fetchall()
    db.close()
    return rows


# Get performance trend for one student
# Returns assessment dates and percentage scores for line chart display
def get_performance_trend(student_id):
    grades = Grade.get_by_student(student_id)
    dates = [g['date'] for g in grades]
    scores = [round(_pct(g), 1) for g in grades]
    return dates, scores