from flask import Blueprint, render_template, session, request, redirect, flash
from app.utils.db import get_db_connection
from app.utils.auth import login_required
import mysql.connector
#---------------- STUDENT DASHBOARD ----------------
student_bp = Blueprint('student', __name__, url_prefix='/student')
@student_bp.route('/dashboard')
@login_required('student')
def student_dashboard():
    return render_template('student/student_dashboard.html')

# ---------------- STUDENT TIMETABLE ----------------
@student_bp.route('/timetable')
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
@student_bp.route('/assignments')
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
@student_bp.route('/materials')
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
@student_bp.route('/tests')
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
@student_bp.route('/attempt_test/<int:test_id>', methods=['GET','POST'])
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
@student_bp.route('/results')
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
@student_bp.route('/ai_recommendation/<int:test_id>')
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
@student_bp.route('/submit/<int:assignment_id>', methods=['GET','POST'])
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

# ---------------- STUDENT: VIEW MY CLASS ----------------
@student_bp.route('/my-class')
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
        LIMIT 1    
    """, (student_id,))
    class_data = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('student/my_class.html', class_data=class_data)
