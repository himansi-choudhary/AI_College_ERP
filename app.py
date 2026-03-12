import os
from datetime import date
import time
from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return redirect('/login')
            if role and session.get('role') != role:
                return redirect('/login')
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ---------------- FILE SIZE ERROR HANDLER ----------------
@app.errorhandler(413)
def file_too_large(e):
    flash("File too large! Maximum size allowed is 50MB.", "error")
    return redirect(request.url)

# ---------------- ERROR PAGES ----------------
@app.errorhandler(404)
def not_found(e):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("errors/500.html"), 500

# ---------------- Database Connection ----------------
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

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
@login_required('admin')
def admin_dashboard():
    return render_template('admin/admin_dashboard.html')

@app.route('/teacher/dashboard')
@login_required('teacher')
def teacher_dashboard():
    return render_template('teacher/teacher_dashboard.html')

@app.route('/student/dashboard')
@login_required('student')
def student_dashboard():
    return render_template('student/student_dashboard.html')

# ---------------- STUDENT TIMETABLE ----------------
@app.route('/student/timetable')
@login_required('student')
def student_timetable():
    student_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT s.subject_name, t.day, t.start_time, t.end_time
        FROM student_classes sc
        JOIN timetable t ON sc.class_id = t.class_id
        JOIN subjects s ON t.subject_id = s.id
        WHERE sc.student_id = %s
        ORDER BY FIELD(t.day,'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday')
    """, (student_id,))

    schedule = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('student/timetable.html', schedule=schedule)

# ---------------- STUDENT ASSIGNMENTS ----------------
@app.route('/student/assignments')
@login_required('student')
def student_assignments():
    student_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT a.id, a.title, a.description, a.due_date,
               s.subject_name
        FROM assignments a
        JOIN subjects s ON a.subject_id = s.id
        JOIN student_classes sc ON sc.class_id = s.class_id
        WHERE sc.student_id = %s
    """, (student_id,))

    assignments = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'student/assignments.html',
        assignments=assignments
    )


# ---------------- STUDENT MATERIALS ----------------
@app.route('/student/materials')
@login_required('student')
def student_materials():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT m.title, m.file_name, s.subject_name
    FROM study_materials m
    JOIN subjects s ON m.subject_id = s.id
    """)

    materials = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'student/materials.html',
        materials=materials
    )
# ---------------- STUDENT TESTS ----------------
@app.route('/student/tests')
@login_required('student')
def student_tests():

    student_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT t.id, t.title, s.subject_name
        FROM tests t
        JOIN subjects s ON t.subject_id = s.id
        JOIN student_classes sc ON sc.class_id = s.class_id
        WHERE sc.student_id = %s
    """, (student_id,))

    tests = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'student/tests.html',
        tests=tests
    )


# ---------------- STUDENT ATTEMPT TEST ----------------
@app.route('/student/attempt_test/<int:test_id>', methods=['GET','POST'])
@login_required('student')
def attempt_test(test_id):

    student_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id FROM results
        WHERE student_id=%s AND test_id=%s
    """, (student_id, test_id))
    existing = cursor.fetchone()

    if existing:
        cursor.close()
        conn.close()
        flash("You have already attempted this test!", "error")
        return redirect('/student/tests')

    cursor.execute("""
    SELECT * FROM questions
    WHERE test_id=%s
    """,(test_id,))
    questions = cursor.fetchall()

    if request.method == 'POST':
        score = 0
        for q in questions:
            selected = request.form.get(str(q['id']))
            if selected == q['correct_option']:
                score += 1

        try:
            cursor.execute("""
                INSERT INTO results (student_id, test_id, score)
                VALUES (%s, %s, %s)
            """, (student_id, test_id, score))
            conn.commit()
            flash(f"Test submitted successfully! Your Score: {score}", "success")
        except mysql.connector.errors.IntegrityError:
            flash("You have already attempted this test!", "error")
        finally:
            cursor.close()
            conn.close()
        
        return redirect('/student/results')
    
    cursor.close()
    conn.close()

    return render_template(
        'student/attempt_test.html',
        questions=questions
    )

# ---------------- STUDENT RESULTS ----------------
@app.route('/student/results')
@login_required('student')
def student_results():

    student_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT t.id AS test_id, t.title, r.score, s.subject_name
    FROM results r
    JOIN tests t ON r.test_id = t.id
    JOIN subjects s ON t.subject_id = s.id
    WHERE r.student_id=%s
    """,(student_id,))

    results = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return render_template(
        'student/results.html',
        results=results
    )

# ---------------- AI RECOMMENDATION ----------------
@app.route('/student/ai_recommendation/<int:test_id>')
@login_required('student')
def ai_recommendation(test_id):
    student_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT score
    FROM results
    WHERE student_id=%s AND test_id=%s
    """,(student_id,test_id))

    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result and result['score'] < 3:
        message = "AI Suggestion: Revise this subject and practice more MCQ tests."
    else:
        message = "AI Suggestion: Good performance. Continue practicing."

    return message



# ---------------- STUDENT SUBMIT ASSIGNMENT ----------------
@app.route('/student/submit/<int:assignment_id>', methods=['GET','POST'])
@login_required('student')  
def submit_assignment(assignment_id):
    student_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':

        submission_text = request.form['submission_text']

        cursor.execute("""
        INSERT INTO submissions
        (assignment_id, student_id, submission_text)
        VALUES (%s,%s,%s)
        """,(assignment_id, student_id, submission_text))

        conn.commit()

        return redirect('/student/assignments')
    
    cursor.close()
    conn.close()

    return render_template('student/submit_assignment.html')

# ---------- TEACHER TIMETABLE ----------
@app.route('/teacher/timetable')
@login_required('teacher')  
def teacher_timetable():
    teacher_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT c.class_name, s.subject_name, t.day, t.start_time, t.end_time
        FROM timetable t
        JOIN classes c ON t.class_id = c.id
        JOIN subjects s ON t.subject_id = s.id
        WHERE t.teacher_id = %s
        ORDER BY FIELD(t.day,'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday')
    """, (teacher_id,))

    schedule = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('teacher/timetable.html', schedule=schedule)


# ---------------- TEACHER ASSIGNMENTS ----------------
@app.route('/teacher/assignments', methods=['GET', 'POST'])
@login_required('teacher')

def teacher_assignments():
    teacher_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Create assignment
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        subject_id = request.form['subject_id']
        due_date = request.form['due_date']

        cursor.execute("""
            INSERT INTO assignments (title, description, subject_id, teacher_id, due_date)
            VALUES (%s,%s,%s,%s,%s)
        """, (title, description, subject_id, teacher_id, due_date))

        conn.commit()

    # Subjects for dropdown
    cursor.execute("SELECT id, subject_name FROM subjects")
    subjects = cursor.fetchall()

    # Fetch assignments created by this teacher
    cursor.execute("""
        SELECT a.title, a.description, a.due_date, s.subject_name
        FROM assignments a
        JOIN subjects s ON a.subject_id = s.id
        WHERE a.teacher_id = %s
    """, (teacher_id,))

    assignments = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'teacher/assignments.html',
        subjects=subjects,
        assignments=assignments
    )


# ---------------- TEACHER CREATE TEST ----------------
@app.route('/teacher/create_test', methods=['GET','POST'])
@login_required('teacher')
def create_test():
    teacher_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':

        title = request.form['title']
        subject_id = request.form['subject_id']

        cursor.execute("""
        INSERT INTO tests (title, subject_id, teacher_id)
        VALUES (%s,%s,%s)
        """,(title,subject_id,teacher_id))

        conn.commit()

    cursor.execute("SELECT id, subject_name FROM subjects")
    subjects = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'teacher/create_test.html',
        subjects=subjects
    )

# ---------------- TEACHER ADD QUESTIONS ----------------
@app.route('/teacher/add_questions/<int:test_id>', methods=['GET','POST'])
@login_required('teacher')
def add_questions(test_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':

        q = request.form['question']
        a = request.form['a']
        b = request.form['b']
        c = request.form['c']
        d = request.form['d']
        correct = request.form['correct']
        cursor.execute("""
        INSERT INTO questions
        (test_id, question_text, option_a, option_b, option_c, option_d, correct_option)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,(test_id,q,a,b,c,d,correct))

        conn.commit()

    cursor.close()
    conn.close()

    return render_template(
        'teacher/add_questions.html',
        test_id=test_id
    )

# ---------------- TEACHER VIEW TEST RESULTS ----------------
@app.route('/teacher/results/<int:test_id>')
@login_required('teacher')
def teacher_results(test_id):
    teacher_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT u.name, r.score
    FROM results r
    JOIN users u ON r.student_id = u.id
    JOIN tests t ON r.test_id = t.id
    WHERE r.test_id=%s AND t.teacher_id=%s
    """,(test_id, teacher_id))

    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'teacher/results.html',
        results=results
    )

# ---------------- TEACHER EXPORT RESULTS TO CSV ----------------
import csv
from flask import Response

@app.route('/teacher/export_results/<int:test_id>')
@login_required('teacher')
def export_results(test_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT u.name AS student_name, r.score
    FROM results r
    JOIN users u ON r.student_id = u.id
    WHERE r.test_id=%s
    """, (test_id,))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    def generate():
        yield "Student,Score\n"
        for row in rows:
            yield f"{row['student_name']},{row['score']}\n"

    return Response(
        generate(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=results.csv"}
    )

# ---------------- TEACHER STUDY MATERIALS ----------------
@app.route('/teacher/materials', methods=['GET','POST'])
@login_required('teacher')
def teacher_materials():
    teacher_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':

        title = request.form['title']
        subject_id = request.form['subject_id']

        if 'file' not in request.files:
            flash("No file selected", "error")
            return redirect('/teacher/materials')

        file = request.files['file']

        if file and allowed_file(file.filename):

            filename = secure_filename(file.filename)

            unique_filename = str(int(time.time())) + "_" + filename

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)

            cursor.execute("""
            INSERT INTO study_materials
            (title, file_name, subject_id, teacher_id)
            VALUES (%s,%s,%s,%s)
            """,(title, unique_filename, subject_id, teacher_id))

            conn.commit()

            flash("Material uploaded successfully!", "success")

        else:
            flash("Invalid file type. Only PDF, DOC, PPT, Images allowed.", "error")
            return redirect('/teacher/materials')

    cursor.execute("SELECT id, subject_name FROM subjects")
    subjects = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'teacher/materials.html',
        subjects=subjects
    )

# ---------------- ADMIN: CREATE USER ----------------
@app.route('/admin/create-user', methods=['GET', 'POST'])
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
@app.route('/admin/analytics')
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
@app.route('/admin/users')
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
@app.route('/admin/toggle-user/<int:user_id>')
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
@app.route('/admin/search_students')
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
@app.route('/admin/classes')
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
@app.route('/admin/classes/add', methods=['GET', 'POST'])
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
@app.route('/admin/subjects')
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
@app.route('/admin/subjects/add', methods=['GET', 'POST'])
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
@app.route('/admin/classes/<int:class_id>/subjects')
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
@app.route('/admin/teacher-subjects')
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
@app.route('/admin/teacher-subjects/add', methods=['GET', 'POST'])
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
@app.route('/admin/assign-student', methods=['GET', 'POST'])
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

# ---------------- STUDENT: VIEW MY CLASS ----------------
@app.route('/student/my-class')
@login_required('student')
def student_my_class():


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
    cursor.close()
    conn.close()

    return render_template('student/my_class.html', class_data=class_data)

# ---------------- TEACHER: VIEW MY STUDENTS ----------------
@app.route('/teacher/my-students')
@login_required('teacher')
def teacher_my_students():

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
    cursor.close()
    conn.close()

    return render_template('teacher/my_students.html', students=students)

# ---------------- TEACHER: MARK ATTENDANCE ----------------
@app.route('/teacher/attendance', methods=['GET', 'POST'])
@login_required('teacher')
def mark_attendance():
    

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
    cursor.close()
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
