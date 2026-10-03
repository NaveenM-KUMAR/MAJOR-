from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models.user import User
from app.models.parking import ParkingSpace
from app.models.notification import Notification
from app.services.auth_service import register_user, authenticate_user, logout_user
from app.utils.decorators import login_required
from app.utils.file_handler import save_uploaded_file

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    """Public Landing Page showcasing Community Parking System features."""
    if 'user_id' in session:
        return redirect(url_for('auth.dashboard_redirect'))
        
    # Highlight top featured community parking spaces
    featured_spaces = ParkingSpace.query.filter_by(
        is_active=True,
        approval_status='APPROVED'
    ).limit(6).all()
    
    return render_template('index.html', featured_spaces=featured_spaces)


@auth_bp.route('/how-it-works')
def how_it_works():
    """Explains community sharing model for Drivers & Property Owners."""
    return render_template('how_it_works.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
@auth_bp.route('/auth/register', methods=['GET', 'POST'])
def register():
    """User & Property Owner Registration."""
    if 'user_id' in session:
        return redirect(url_for('auth.dashboard_redirect'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'DRIVER').upper()
        
        owner_address = request.form.get('owner_address', '').strip()
        owner_id_proof_file = request.files.get('owner_id_proof')

        if not name or not email or not phone or not password:
            flash('Please complete all required fields.', 'warning')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match. Please verify.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'warning')
            return render_template('auth/register.html')

        saved_proof_filename = None
        if role == 'OWNER' and owner_id_proof_file and owner_id_proof_file.filename:
            try:
                saved_proof_filename = save_uploaded_file(owner_id_proof_file, custom_prefix='owner_id')
            except Exception as e:
                flash(f"Error uploading ID document: {str(e)}", 'danger')
                return render_template('auth/register.html')

        success, result = register_user(
            name=name,
            email=email,
            phone=phone,
            password=password,
            role=role,
            owner_address=owner_address if role == 'OWNER' else None,
            owner_id_proof=saved_proof_filename
        )

        if not success:
            flash(result, 'danger')
            return render_template('auth/register.html')

        if role == 'OWNER':
            flash('Registration submitted! Your owner account is pending verification by our admin team.', 'info')
        else:
            flash('Account created successfully! Please log in.', 'success')

        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
@auth_bp.route('/auth/login', methods=['GET', 'POST'])
def login():
    """Unified user authentication for all roles with multi-tab role switcher."""
    if request.method == 'GET' and 'user_id' in session and not request.args.get('switch'):
        return redirect(url_for('auth.dashboard_redirect'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'warning')
            return render_template('auth/login.html')

        success, user_or_err = authenticate_user(email, password)
        if not success:
            flash(user_or_err, 'danger')
            return render_template('auth/login.html')

        flash(f"Welcome back, {user_or_err.name}!", 'success')
        
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
            
        return redirect(url_for('auth.dashboard_redirect'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@auth_bp.route('/auth/logout')
def logout():
    """Logs out current user."""
    logout_user()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/dashboard')
@login_required
def dashboard_redirect():
    """Smart router directing users to role-specific dashboard."""
    role = session.get('role')
    if role == 'ADMIN':
        return redirect(url_for('admin.dashboard'))
    elif role == 'OWNER':
        return redirect(url_for('owner.dashboard'))
    else:
        return redirect(url_for('driver.dashboard'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """View and update profile settings."""
    user = db.session.get(User, session['user_id'])
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        new_password = request.form.get('new_password', '')
        
        if name:
            user.name = name
            session['user_name'] = name
        if phone:
            user.phone = phone

        if user.is_owner or user.role in ['OWNER', 'ADMIN']:
            upi_id = request.form.get('upi_id', '').strip()
            user.upi_id = upi_id if upi_id else None
            
        if new_password:
            if len(new_password) < 6:
                flash('New password must be at least 6 characters long.', 'warning')
            else:
                user.set_password(new_password)
                flash('Password updated successfully.', 'success')
                
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('auth.profile'))
        
    return render_template('auth/profile.html', user=user)


@auth_bp.route('/notifications/mark-read/<int:notif_id>', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    """Marks a user notification as read."""
    notif = Notification.query.filter_by(id=notif_id, user_id=session['user_id']).first()
    if notif:
        notif.is_read = True
        db.session.commit()
    return redirect(request.referrer or url_for('auth.dashboard_redirect'))
