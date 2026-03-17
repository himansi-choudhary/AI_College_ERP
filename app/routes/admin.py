from flask import Blueprint, render_template, request, redirect, flash, session
from app.utils.db import get_db_connection
from app.utils.auth import login_required
from werkzeug.security import generate_password_hash
import mysql.connector

# ---------------- ADMIN DASHBOARD ----------------
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
@admin_bp.route('/dashboard')
@login_required('admin')
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Stats queries
    cursor.execute("SELECT COUNT(*) total FROM users WHERE role='student'")
    students = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) total FROM users WHERE role='teacher'")
    teachers = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) total FROM classes WHERE is_active=1")
    classes = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) total FROM subjects WHERE is_active=1")
    subjects = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) total FROM tests")
    tests = cursor.fetchone()['total']

    cursor.execute("SELECT id, name, email, role FROM users ORDER BY id DESC LIMIT 5")
    recent_users = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'admin/admin_dashboard.html',
        students=students,
        teachers=teachers,
        classes=classes,
        subjects=subjects,
        tests=tests,
        recent_users=recent_users
    )

# ---------------- ADMIN: CREATE USER ----------------
@admin_bp.route('/create-user', methods=['GET', 'POST'])
@login_required('admin')
def create_user():

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

# ---------------- ADMIN ANALYTICS ----------------
@admin_bp.route('/analytics')
@login_required('admin')
def admin_analytics():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) total FROM users WHERE role='student'")
    students = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) total FROM users WHERE role='teacher'")
    teachers = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) total FROM tests")
    tests = cursor.fetchone()['total']

    cursor.close()
    conn.close()

    return render_template(
        'admin/analytics.html',
        students=students,
        teachers=teachers,
        tests=tests
    )

# ---------------- ADMIN: VIEW USERS LIST ----------------
@admin_bp.route('/users')
@login_required('admin')
def view_users():


    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, name, email, role, is_active FROM users")
    users = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin/users_list.html', users=users)

# ---------------- ADMIN: TOGGLE USER STATUS ----------------
@admin_bp.route('/toggle-user/<int:user_id>')
@login_required('admin')
def toggle_user(user_id):

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

# ---------------- ADMIN: SEARCH STUDENTS ----------------
@admin_bp.route('/search_students')
@login_required('admin')
def search_students():

    keyword = request.args.get('q', ' ').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT * FROM users
    WHERE role='student'
    AND name LIKE %s
    """,('%'+keyword+'%',))  

    students = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'admin/search_students.html',
        students=students
    )


# ---------------- ADMIN: VIEW CLASSES ----------------
@admin_bp.route('/classes')
@login_required('admin')
def view_classes():


    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM classes WHERE is_active=1")
    classes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin/classes_list.html', classes=classes)

# ---------------- ADMIN: ADD CLASS ----------------
@admin_bp.route('/classes/add', methods=['GET', 'POST'])
@login_required('admin')
def add_class():

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
            cursor.close()
            conn.close()

        return redirect('/admin/classes')

    return render_template('admin/add_class.html')

# ---------------- ADMIN: VIEW SUBJECTS ----------------
@admin_bp.route('/subjects')
@login_required('admin')
def view_subjects():


    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT subjects.id, subjects.subject_name, classes.class_name
        FROM subjects
        JOIN classes ON subjects.class_id = classes.id
        WHERE subjects.is_active = 1
    """)
    subjects = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('admin/subjects_list.html', subjects=subjects)

# ---------------- ADMIN: ADD SUBJECT ----------------
@admin_bp.route('/subjects/add', methods=['GET', 'POST'])
@login_required('admin')
def add_subject():

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

        cursor.close()
        conn.close()

        return redirect('/admin/subjects')

    cursor.execute("SELECT id, class_name FROM classes WHERE is_active=1")
    classes = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('admin/add_subject.html', classes=classes)

# ---------------- CLASS → SUBJECTS VIEW ----------------
@admin_bp.route('/classes/<int:class_id>/subjects')
@login_required('admin')
def class_subjects(class_id):


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

    cursor.close()
    conn.close()
    return render_template(
        'admin/class_subjects.html',
        class_data=class_data,
        subjects=subjects
    )

# ---------------- TEACHER ↔ SUBJECT ↔ CLASS ----------------

# View existing mappings
@admin_bp.route('/teacher-subjects')
@login_required('admin')
def view_teacher_subjects():


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

    cursor.close()
    conn.close()
    return render_template('admin/teacher_subjects_list.html', mappings=mappings)

# Add a new mapping
@admin_bp.route('/teacher-subjects/add', methods=['GET', 'POST'])
@login_required('admin')
def add_teacher_subject():

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
        
        cursor.close()
        conn.close()

        return redirect('/admin/teacher-subjects')

    # GET method: fetch dropdowns
    cursor.execute("SELECT id, name FROM users WHERE role='teacher' AND is_active=1")
    teachers = cursor.fetchall()

    cursor.execute("SELECT id, class_name FROM classes WHERE is_active=1")
    classes = cursor.fetchall()

    cursor.execute("SELECT id, subject_name FROM subjects WHERE is_active=1")
    subjects = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template(
        'admin/assign_teacher_subject.html',
        teachers=teachers,
        classes=classes,
        subjects=subjects
    )

# ---------------- ADMIN: ASSIGN STUDENT TO CLASS ----------------
@admin_bp.route('/assign-student', methods=['GET', 'POST'])
@login_required('admin')
def assign_student_class():

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

        cursor.close()
        conn.close()
        return redirect('/admin/assign-student')
    
    # GET: dropdown data
    cursor.execute("SELECT id, name FROM users WHERE role='student' AND is_active=1")
    students = cursor.fetchall()

    cursor.execute("SELECT id, class_name FROM classes WHERE is_active=1")
    classes = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('admin/assign_student_class.html', students=students, classes=classes)

