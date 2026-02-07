import os
from datetime import date
from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# ---------------- Database Connection ----------------
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

# ---------------- Session Guard Helper ----------------
def login_required(role=None):
    if 'user_id' not in session:
        return redirect('/login')
    if role and session.get('role') != role:
        return redirect('/login')

# ---------------- Home Route ----------------
@app.route('/')
def home():
    return "AI College ERP Running"

# ---------------- Login Route ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            if not user['is_active']:
                flash("Your account is deactivated. Please contact the admin.", "error")
                return redirect('/login')
            
            if check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['role'] = user['role']

                if user['role'] == 'admin':
                    return redirect('/admin/dashboard')
                elif user['role'] == 'teacher':
                    return redirect('/teacher/dashboard')
                else:
                    return redirect('/student/dashboard')

        flash("Invalid email or password", "error")
        return redirect('/login')

    return render_template('login.html')

# ---------------- Dashboard Routes ----------------
@app.route('/admin/dashboard')
def admin_dashboard():
    guard = login_required('admin')
    if guard:
        return guard
    return render_template('admin/admin_dashboard.html')

@app.route('/teacher/dashboard')
def teacher_dashboard():
    guard = login_required('teacher')
    if guard:
        return guard
    return render_template('teacher/teacher_dashboard.html')

@app.route('/student/dashboard')
def student_dashboard():
    guard = login_required('student')
    if guard:
        return guard
    return render_template('student/student_dashboard.html')

# ---------------- ADMIN: CREATE USER ----------------
@app.route('/admin/create-user', methods=['GET', 'POST'])
def create_user():
    guard = login_required('admin')
    if guard:
        return guard

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        INSERT INTO users (name, email, password, role)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (name, email, hashed_password, role))
        conn.commit()

        cursor.close()
        conn.close()

        flash("User created successfully", "success")
        return redirect('/admin/create-user')

    return render_template('admin/create_user.html')

# ---------------- ADMIN: VIEW USERS LIST ----------------
@app.route('/admin/users')
def view_users():
    guard = login_required('admin')
    if guard:
        return guard

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, name, email, role, is_active FROM users")
    users = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin/users_list.html', users=users)

# ---------------- ADMIN: TOGGLE USER STATUS ----------------
@app.route('/admin/toggle-user/<int:user_id>')
def toggle_user(user_id):
    guard = login_required('admin')
    if guard:
        return guard

    # Prevent admin from deactivating themselves
    if user_id == session.get('user_id'):
        flash("You cannot deactivate your own account", "error")
        return redirect('/admin/users')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET is_active = NOT is_active
        WHERE id = %s
    """, (user_id,))
    conn.commit()

    cursor.close()
    conn.close()

    flash("User status updated successfully", "success")
    return redirect('/admin/users')

# ---------------- ADMIN: VIEW CLASSES ----------------
@app.route('/admin/classes')
def view_classes():
    guard = login_required('admin')
    if guard:
        return guard

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM classes WHERE is_active=1")
    classes = cursor.fetchall()
    conn.close()

    return render_template('admin/classes_list.html', classes=classes)

# ---------------- ADMIN: ADD CLASS ----------------
@app.route('/admin/classes/add', methods=['GET', 'POST'])
def add_class():
    guard = login_required('admin')
    if guard:
        return guard

    if request.method == 'POST':
        class_name = request.form['class_name']
        academic_year = request.form['academic_year']

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO classes (class_name, academic_year) VALUES (%s, %s)",
                (class_name, academic_year)
            )
            conn.commit()
            flash("Class added successfully")
        except:
            flash("Class already exists")
        finally:
            conn.close()

        return redirect('/admin/classes')

    return render_template('admin/add_class.html')

# ---------------- ADMIN: VIEW SUBJECTS ----------------
@app.route('/admin/subjects')
def view_subjects():
    guard = login_required('admin')
    if guard:
        return guard

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT subjects.id, subjects.subject_name, classes.class_name
        FROM subjects
        JOIN classes ON subjects.class_id = classes.id
        WHERE subjects.is_active = 1
    """)
    subjects = cursor.fetchall()

    conn.close()
    return render_template('admin/subjects_list.html', subjects=subjects)

# ---------------- ADMIN: ADD SUBJECT ----------------
@app.route('/admin/subjects/add', methods=['GET', 'POST'])
def add_subject():
    guard = login_required('admin')
    if guard:
        return guard

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        subject_name = request.form['subject_name']
        class_id = request.form['class_id']

        cursor2 = conn.cursor()
        cursor2.execute(
            "INSERT INTO subjects (subject_name, class_id) VALUES (%s, %s)",
            (subject_name, class_id)
        )
        conn.commit()
        cursor2.close()

        flash("Subject added successfully", "success")
        conn.close()
        return redirect('/admin/subjects')

    cursor.execute("SELECT id, class_name FROM classes WHERE is_active=1")
    classes = cursor.fetchall()

    conn.close()
    return render_template('admin/add_subject.html', classes=classes)

# ---------------- CLASS → SUBJECTS VIEW ----------------
@app.route('/admin/classes/<int:class_id>/subjects')
def class_subjects(class_id):
    guard = login_required('admin')
    if guard:
        return guard

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get class info
    cursor.execute("SELECT * FROM classes WHERE id=%s", (class_id,))
    class_data = cursor.fetchone()

    # Get subjects for this class
    cursor.execute("""
        SELECT subject_name
        FROM subjects
        WHERE class_id=%s AND is_active=1
    """, (class_id,))
    subjects = cursor.fetchall()

    conn.close()
    return render_template(
        'admin/class_subjects.html',
        class_data=class_data,
        subjects=subjects
    )

# ---------------- TEACHER ↔ SUBJECT ↔ CLASS ----------------

# View existing mappings
@app.route('/admin/teacher-subjects')
def view_teacher_subjects():
    guard = login_required('admin')
    if guard:
        return guard

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT ts.id, u.name AS teacher_name, c.class_name, s.subject_name
        FROM teacher_subjects ts
        JOIN users u ON ts.teacher_id = u.id
        JOIN classes c ON ts.class_id = c.id
        JOIN subjects s ON ts.subject_id = s.id
    """)
    mappings = cursor.fetchall()

    conn.close()
    return render_template('admin/teacher_subjects_list.html', mappings=mappings)

# Add a new mapping
@app.route('/admin/teacher-subjects/add', methods=['GET', 'POST'])
def add_teacher_subject():
    guard = login_required('admin')
    if guard:
        return guard

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        teacher_id = request.form['teacher_id']
        class_id = request.form['class_id']
        subject_id = request.form['subject_id']

        try:
            cursor2 = conn.cursor()
            cursor2.execute(
                "INSERT INTO teacher_subjects (teacher_id, class_id, subject_id) VALUES (%s, %s, %s)",
                (teacher_id, class_id, subject_id)
            )
            conn.commit()
            cursor2.close()
            flash("Teacher assigned successfully", "success")
        except mysql.connector.errors.IntegrityError:
            flash("This mapping already exists", "error")
        
        conn.close()
        return redirect('/admin/teacher-subjects')

    # GET method: fetch dropdowns
    cursor.execute("SELECT id, name FROM users WHERE role='teacher' AND is_active=1")
    teachers = cursor.fetchall()

    cursor.execute("SELECT id, class_name FROM classes WHERE is_active=1")
    classes = cursor.fetchall()

    cursor.execute("SELECT id, subject_name FROM subjects WHERE is_active=1")
    subjects = cursor.fetchall()

    conn.close()
    return render_template(
        'admin/assign_teacher_subject.html',
        teachers=teachers,
        classes=classes,
        subjects=subjects
    )

# ---------------- ADMIN: ASSIGN STUDENT TO CLASS ----------------
@app.route('/admin/assign-student', methods=['GET', 'POST'])
def assign_student_class():
    guard = login_required('admin')
    if guard:
        return guard

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        student_id = request.form['student_id']
        class_id = request.form['class_id']

        try:
            cursor2 = conn.cursor()
            cursor2.execute("""
                INSERT INTO student_classes (student_id, class_id)
                VALUES (%s, %s)
            """, (student_id, class_id))
            conn.commit()
            cursor2.close()
            flash("Student assigned to class successfully", "success")
        except mysql.connector.errors.IntegrityError:
            flash("Student already assigned to a class", "error")

        conn.close()
        return redirect('/admin/assign-student')
    
    # GET: dropdown data
    cursor.execute("SELECT id, name FROM users WHERE role='student' AND is_active=1")
    students = cursor.fetchall()

    cursor.execute("SELECT id, class_name FROM classes WHERE is_active=1")
    classes = cursor.fetchall()

    conn.close()
    return render_template('admin/assign_student_class.html', students=students, classes=classes)

# ---------------- STUDENT: VIEW MY CLASS ----------------
@app.route('/student/my-class')
def student_my_class():
    guard = login_required('student')
    if guard:
        return guard

    student_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT c.class_name, c.academic_year
        FROM student_classes sc
        JOIN classes c ON sc.class_id = c.id
        WHERE sc.student_id = %s
    """, (student_id,))

    class_data = cursor.fetchone()
    conn.close()

    return render_template('student/my_class.html', class_data=class_data)

# ---------------- TEACHER: VIEW MY STUDENTS ----------------
@app.route('/teacher/my-students')
def teacher_my_students():
    guard = login_required('teacher')
    if guard:
        return guard

    teacher_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT DISTINCT u.name, u.email, c.class_name
        FROM teacher_subjects ts
        JOIN student_classes sc ON ts.class_id = sc.class_id
        JOIN users u ON sc.student_id = u.id
        JOIN classes c ON ts.class_id = c.id
        WHERE ts.teacher_id = %s
    """, (teacher_id,))

    students = cursor.fetchall()
    conn.close()

    return render_template('teacher/my_students.html', students=students)

# ---------------- TEACHER: MARK ATTENDANCE ----------------
@app.route('/teacher/attendance', methods=['GET', 'POST'])
def mark_attendance():
    guard = login_required('teacher')
    if guard:
        return guard

    teacher_id = session.get('user_id')
    today = date.today()

    conn = get_db_connection()

    # Use a dictionary cursor for fetching mapping
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT ts.subject_id, ts.class_id, s.subject_name, c.class_name
        FROM teacher_subjects ts
        JOIN subjects s ON ts.subject_id = s.id
        JOIN classes c ON ts.class_id = c.id
        WHERE ts.teacher_id = %s
    """, (teacher_id,))
    mapping = cursor.fetchall()  
    cursor.close()  

    if not mapping:
        conn.close()
        flash("No subject assigned", "error")
        return redirect('/teacher/dashboard')
    
    mapping = mapping[0]

    # Use a **new cursor** for fetching students
    student_cursor = conn.cursor(dictionary=True)
    student_cursor.execute("""
        SELECT u.id, u.name
        FROM student_classes sc
        JOIN users u ON sc.student_id = u.id
        WHERE sc.class_id = %s
    """, (mapping['class_id'],))
    students = student_cursor.fetchall()
    student_cursor.close()

    if request.method == 'POST':
        # Separate cursor for inserting attendance
        insert_cursor = conn.cursor()
        for student in students:
            status = request.form.get(f"status_{student['id']}")
            if status not in ['Present', 'Absent']:
                continue
            insert_cursor.execute("""
                INSERT INTO attendance (student_id, subject_id, date, status)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE status=%s
            """, (student['id'], mapping['subject_id'], today, status, status))
        
        conn.commit()
        insert_cursor.close()
        conn.close()
        flash("Attendance saved successfully", "success")
        return redirect('/teacher/attendance')

    # GET request: render attendance form
    conn.close()
    return render_template(
        'teacher/mark_attendance.html',
        students=students,
        subject=mapping,
        today=today
    )


# ---------------- Logout Route ----------------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect('/login')

# ---------------- Run Flask ----------------
if __name__ == '__main__':
    app.run(debug=True)
