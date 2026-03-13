from datetime import date
from flask import Blueprint, render_template, request, session, redirect, flash, Response, current_app
from app.utils.db import get_db_connection
from app.utils.auth import login_required
from werkzeug.utils import secure_filename
import csv
import time
import os

# Set of allowed file extensions for study materials
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------- TEACHER DASHBOARD ----------
teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')
@teacher_bp.route('/dashboard')
@login_required('teacher')
def teacher_dashboard():
    return render_template('teacher/teacher_dashboard.html')

# ---------- TEACHER TIMETABLE ----------
@teacher_bp.route('/timetable')
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
@teacher_bp.route('/assignments', methods=['GET', 'POST'])
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
@teacher_bp.route('/create_test', methods=['GET','POST'])
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
@teacher_bp.route('/add_questions/<int:test_id>', methods=['GET','POST'])
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
@teacher_bp.route('/results/<int:test_id>')
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
@teacher_bp.route('/export_results/<int:test_id>')
@login_required('teacher')
def export_results(test_id):
    teacher_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT u.name AS student_name, r.score
    FROM results r
    JOIN users u ON r.student_id = u.id
    JOIN tests t ON r.test_id = t.id
    WHERE r.test_id=%s AND t.teacher_id=%s
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
@teacher_bp.route('/materials', methods=['GET','POST'])
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

            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
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

# ---------------- TEACHER: VIEW MY STUDENTS ----------------
@teacher_bp.route('/my-students')
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
@teacher_bp.route('/attendance', methods=['GET', 'POST'])
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

    mapping = cursor.fetchone()  
    cursor.close()  

    if not mapping:
        conn.close()
        flash("No subject assigned", "error")
        return redirect('/teacher/dashboard')

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
