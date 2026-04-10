# Utility functions
# Handles authentication decorators and grading helpers

from functools import wraps
from flask import session, redirect, url_for, flash


# Login required decorator
# Restricts access to authenticated users only
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check if user is logged in
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# Teacher required decorator
# Restricts access to users with teacher role only
def teacher_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check if user is logged in
        if 'user_id' not in session:
            flash('Please log in.', 'warning')
            return redirect(url_for('login'))

        # Check if user has teacher role
        if session.get('role') != 'teacher':
            flash('Access denied: teachers only.', 'danger')
            return redirect(url_for('dashboard'))

        return f(*args, **kwargs)
    return decorated


# Convert numeric score to grade classification
# Used for displaying academic results (UK grading system)
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


# Return Bootstrap colour class based on score
# Used for visual feedback in dashboards
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