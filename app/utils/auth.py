from functools import wraps
from flask import session, redirect

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
