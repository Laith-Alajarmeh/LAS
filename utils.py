from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def teacher_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'teacher':
            flash('Access denied: teachers only.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def grade_label(score):
    """Convert numeric score to grade label."""
    if score is None:
        return 'N/A'
    if score >= 70:
        return 'First'
    elif score >= 60:
        return '2:1'
    elif score >= 50:
        return '2:2'
    elif score >= 40:
        return 'Pass'
    else:
        return 'Fail'

def grade_colour(score):
    """Return a Bootstrap colour class for a score."""
    if score is None:
        return 'secondary'
    if score >= 70:
        return 'success'
    elif score >= 50:
        return 'warning'
    else:
        return 'danger'