from flask import Blueprint, render_template, request, redirect, session, flash
from werkzeug.security import check_password_hash
from app.utils.db import get_db_connection

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def home():
    return render_template('home.html')

@auth_bp.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE email=%s",(email,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:

            if not user['is_active']:
                flash("Your account is deactivated. Contact admin.", "error")
                return redirect('/login')

            if check_password_hash(user['password'], password):

                session['user_id'] = user['id']
                session['role'] = user['role']

                if user['role']=="admin":
                    return redirect('/admin/dashboard')
                elif user['role']=="teacher":
                    return redirect('/teacher/dashboard')
                else:
                    return redirect('/student/dashboard')

        flash("Invalid email or password", "error")

    return render_template("login.html")

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully")
    return redirect('/login')
