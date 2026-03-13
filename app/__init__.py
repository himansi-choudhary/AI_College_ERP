import os
from flask import Flask, render_template, flash, redirect, request
from dotenv import load_dotenv

load_dotenv()

def create_app():

    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.secret_key = os.getenv("FLASK_SECRET_KEY")

    # Upload config
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(413)
    def file_too_large(e):
        flash("File too large! Maximum size allowed is 50MB.", "error")
        return redirect(request.url)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.student import student_bp
    from app.routes.teacher import teacher_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(admin_bp)

    return app