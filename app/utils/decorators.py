from functools import wraps
from flask import session, redirect, url_for, flash, request, abort, jsonify
from app import db

def login_required(f):
    """Ensures that user is authenticated in session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required. Please log in.'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        from app.models.user import User
        # Verify user still exists and is not suspended
        user = db.session.get(User, session['user_id'])
        if not user or user.status == 'SUSPENDED':
            session.clear()
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Account is suspended or invalid.'}), 403
            flash('Your account is currently suspended. Please contact administrator.', 'danger')
            return redirect(url_for('auth.login'))
            
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles):
    """Restricts access to specified roles (e.g. 'ADMIN', 'OWNER', 'DRIVER')."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'success': False, 'message': 'Authentication required.'}), 401
                flash('Please log in to continue.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            user_role = session.get('role')
            if user_role not in allowed_roles:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'success': False, 'message': 'Access forbidden: insufficient role permissions.'}), 403
                flash('Access forbidden: You do not have permission to access this resource.', 'danger')
                return redirect(url_for('auth.dashboard_redirect'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def approved_owner_required(f):
    """Requires user to be an OWNER with 'APPROVED' status."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access owner portal.', 'warning')
            return redirect(url_for('auth.login'))
        
        from app.models.user import User
        user = db.session.get(User, session['user_id'])
        if not user or user.role != 'OWNER':
            flash('Access denied: Parking Owner portal only.', 'danger')
            return redirect(url_for('auth.dashboard_redirect'))
            
        if user.owner_status != 'APPROVED':
            flash('Your parking owner account is pending verification by the administrator.', 'info')
            return redirect(url_for('owner.approval_status'))
            
        return f(*args, **kwargs)
    return decorated_function
