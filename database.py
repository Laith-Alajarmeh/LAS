import sqlite3

DATABASE = 'las.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('teacher', 'student')),
            full_name TEXT NOT NULL,
            email TEXT
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            student_number TEXT UNIQUE NOT NULL,
            course TEXT,
            year INTEGER
        );

        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            teacher_id INTEGER REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER REFERENCES students(id),
            module_id INTEGER REFERENCES modules(id),
            assessment_name TEXT NOT NULL,
            score REAL NOT NULL,
            max_score REAL NOT NULL DEFAULT 100,
            date TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER REFERENCES students(id),
            module_id INTEGER REFERENCES modules(id),
            date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('present', 'absent', 'late'))
        );
    ''')

    # Seed demo data
    from werkzeug.security import generate_password_hash

    # Demo teacher
    cursor.execute("SELECT id FROM users WHERE username='teacher1'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, role, full_name, email) VALUES (?,?,?,?,?)",
            ('teacher1', generate_password_hash('password'), 'teacher', 'Dr. Sarah Jones', 'sjones@uni.ac.uk'))
        teacher_id = cursor.lastrowid

        # Demo students
        students = [
            ('student1', 'Alice Brown', 'S001', 'Computer Science', 2),
            ('student2', 'Bob Smith', 'S002', 'Computer Science', 2),
            ('student3', 'Carol Davis', 'S003', 'Computer Science', 2),
            ('student4', 'Dan Wilson', 'S004', 'Computer Science', 2),
            ('student5', 'Eve Taylor', 'S005', 'Computer Science', 2),
        ]
        student_ids = []
        for uname, fname, snum, course, year in students:
            cursor.execute("INSERT INTO users (username, password, role, full_name) VALUES (?,?,?,?)",
                (uname, generate_password_hash('password'), 'student', fname))
            uid = cursor.lastrowid
            cursor.execute("INSERT INTO students (user_id, student_number, course, year) VALUES (?,?,?,?)",
                (uid, snum, course, year))
            student_ids.append(cursor.lastrowid)

        # Demo modules
        modules = [
            ('CS101', 'Introduction to Programming', teacher_id),
            ('CS201', 'Data Structures', teacher_id),
            ('CS301', 'Software Engineering', teacher_id),
        ]
        module_ids = []
        for code, name, tid in modules:
            cursor.execute("INSERT INTO modules (code, name, teacher_id) VALUES (?,?,?)", (code, name, tid))
            module_ids.append(cursor.lastrowid)

        # Demo grades
        import random, datetime
        random.seed(42)
        assessments = ['Coursework 1', 'Coursework 2', 'Midterm Exam', 'Final Exam']
        scores_map = {
            0: [78, 82, 75, 80],   # Alice - good
            1: [45, 50, 42, 48],   # Bob - at risk
            2: [90, 88, 92, 95],   # Carol - excellent
            3: [60, 58, 62, 55],   # Dan - average
            4: [30, 35, 28, 32],   # Eve - at risk
        }
        base_date = datetime.date(2025, 9, 1)
        for si, sid in enumerate(student_ids):
            for mi, mid in enumerate(module_ids):
                for ai, assessment in enumerate(assessments):
                    score = scores_map[si][ai] + random.randint(-5, 5)
                    score = max(0, min(100, score))
                    date = (base_date + datetime.timedelta(weeks=(mi * 4 + ai * 2))).isoformat()
                    cursor.execute("INSERT INTO grades (student_id, module_id, assessment_name, score, max_score, date) VALUES (?,?,?,?,?,?)",
                        (sid, mid, assessment, score, 100, date))

        # Demo attendance
        for si, sid in enumerate(student_ids):
            for mi, mid in enumerate(module_ids):
                for week in range(12):
                    date = (base_date + datetime.timedelta(weeks=week)).isoformat()
                    # Bob and Eve have poor attendance
                    if si in [1, 4]:
                        status = random.choice(['absent', 'absent', 'present', 'late'])
                    else:
                        status = random.choice(['present', 'present', 'present', 'late'])
                    cursor.execute("INSERT INTO attendance (student_id, module_id, date, status) VALUES (?,?,?,?)",
                        (sid, mid, date, status))

    conn.commit()
    conn.close()