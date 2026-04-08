# Models

from database import get_db

class User:
    @staticmethod
    def get_by_username(username):
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        db.close()
        return user

    @staticmethod
    def get_by_id(user_id):
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        db.close()
        return user


class Student:
    @staticmethod
    def get_all():
        db = get_db()
        students = db.execute('''
            SELECT s.id, s.student_number, s.course, s.year,
                   u.full_name, u.email, u.username
            FROM students s JOIN users u ON s.user_id = u.id
            ORDER BY u.full_name
        ''').fetchall()
        db.close()
        return students

    @staticmethod
    def get_by_user_id(user_id):
        db = get_db()
        student = db.execute('''
            SELECT s.id, s.student_number, s.course, s.year,
                   u.full_name, u.email, u.username
            FROM students s JOIN users u ON s.user_id = u.id
            WHERE u.id = ?
        ''', (user_id,)).fetchone()
        db.close()
        return student

    @staticmethod
    def get_by_id(student_id):
        db = get_db()
        student = db.execute('''
            SELECT s.id, s.student_number, s.course, s.year,
                   u.full_name, u.email, u.username
            FROM students s JOIN users u ON s.user_id = u.id
            WHERE s.id = ?
        ''', (student_id,)).fetchone()
        db.close()
        return student


class Grade:
    @staticmethod
    def get_by_student(student_id):
        db = get_db()
        grades = db.execute('''
            SELECT g.*, m.name as module_name, m.code as module_code
            FROM grades g JOIN modules m ON g.module_id = m.id
            WHERE g.student_id = ?
            ORDER BY g.date
        ''', (student_id,)).fetchall()
        db.close()
        return grades

    @staticmethod
    def get_all():
        db = get_db()
        grades = db.execute('''
            SELECT g.*, m.name as module_name, m.code as module_code,
                   u.full_name as student_name, s.student_number
            FROM grades g
            JOIN modules m ON g.module_id = m.id
            JOIN students s ON g.student_id = s.id
            JOIN users u ON s.user_id = u.id
            ORDER BY g.date DESC
        ''').fetchall()
        db.close()
        return grades

    @staticmethod
    def insert_many(rows):
        db = get_db()
        db.executemany('''
            INSERT INTO grades (student_id, module_id, assessment_name, score, max_score, date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', rows)
        db.commit()
        db.close()


class Module:
    @staticmethod
    def get_all():
        db = get_db()
        modules = db.execute("SELECT * FROM modules").fetchall()
        db.close()
        return modules

    @staticmethod
    def get_by_id(module_id):
        db = get_db()
        module = db.execute("SELECT * FROM modules WHERE id = ?", (module_id,)).fetchone()
        db.close()
        return module


class Attendance:
    @staticmethod
    def get_by_student(student_id):
        db = get_db()
        records = db.execute('''
            SELECT a.*, m.name as module_name, m.code as module_code
            FROM attendance a JOIN modules m ON a.module_id = m.id
            WHERE a.student_id = ?
            ORDER BY a.date DESC
        ''', (student_id,)).fetchall()
        db.close()
        return records

    @staticmethod
    def get_summary_by_student(student_id):
        db = get_db()
        summary = db.execute('''
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status='present' THEN 1 ELSE 0 END) as present,
                SUM(CASE WHEN status='absent' THEN 1 ELSE 0 END) as absent,
                SUM(CASE WHEN status='late' THEN 1 ELSE 0 END) as late
            FROM attendance WHERE student_id = ?
        ''', (student_id,)).fetchone()
        db.close()
        return summary
