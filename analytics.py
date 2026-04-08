from models import Grade, Attendance, Student
from database import get_db

# Named thresholds - easier to discuss in the portfolio and adjust in future
LOW_GRADE_THRESHOLD = 50
LOW_ATTENDANCE_THRESHOLD = 70
DECLINE_THRESHOLD = 15


def _pct(grade_row):
    """Convert a grade row to a percentage, respecting max_score."""
    max_score = grade_row['max_score'] or 100
    return (grade_row['score'] / max_score) * 100


def get_student_avg(student_id):
    grades = Grade.get_by_student(student_id)
    if not grades:
        return 0
    total_pct = sum(_pct(g) for g in grades)
    return round(total_pct / len(grades), 1)


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


def get_attendance_rate(student_id):
    summary = Attendance.get_summary_by_student(student_id)
    if not summary or summary['total'] == 0:
        return 100
    rate = (summary['present'] + summary['late'] * 0.5) / summary['total'] * 100
    return round(rate, 1)


def is_at_risk(student_id):
    avg = get_student_avg(student_id)
    attendance = get_attendance_rate(student_id)
    reasons = []

    if avg < LOW_GRADE_THRESHOLD:
        reasons.append(f"Low average grade ({avg}%)")
    if attendance < LOW_ATTENDANCE_THRESHOLD:
        reasons.append(f"Poor attendance ({attendance}%)")

    # Declining trend: compare last 2 assessments vs the 2 before
    grades = Grade.get_by_student(student_id)
    if len(grades) >= 4:
        recent_avg  = sum(_pct(g) for g in grades[-2:]) / 2
        earlier_avg = sum(_pct(g) for g in grades[-4:-2]) / 2
        drop = earlier_avg - recent_avg
        if drop > DECLINE_THRESHOLD:
            reasons.append(f"Declining performance (dropped {round(drop, 1)} points)")

    return len(reasons) > 0, reasons


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


def get_grade_distribution(student_id):
    grades = Grade.get_by_student(student_id)
    labels = [f"{g['module_code']} - {g['assessment_name']}" for g in grades]
    scores = [round(_pct(g), 1) for g in grades]
    return labels, scores


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


def get_performance_trend(student_id):
    grades = Grade.get_by_student(student_id)
    dates  = [g['date'] for g in grades]
    scores = [round(_pct(g), 1) for g in grades]
    return dates, scores