from flask import session
from app import db
from app.models.user import User
from app.services.audit_service import log_audit_event

def register_user(name, email, phone, password, role='DRIVER', owner_address=None, owner_id_proof=None):
    """
    Registers a new Driver or Owner user.
    Owners automatically enter 'PENDING' approval status.
    """
    email = email.strip().lower()
    phone = phone.strip()
    name = name.strip()
    
    if User.query.filter((User.email == email) | (User.phone == phone)).first():
        return False, "An account with this email address or phone number already exists."
        
    user = User(
        name=name,
        email=email,
        phone=phone,
        role=role,
        status='ACTIVE'
    )
    user.set_password(password)
    
    if role == 'OWNER':
        user.owner_status = 'PENDING'
        user.owner_address = owner_address
        user.owner_id_proof = owner_id_proof
    
    db.session.add(user)
    db.session.commit()
    
    log_audit_event(
        action='USER_REGISTERED',
        target_entity='User',
        target_id=user.id,
        details=f"Registered {role}: {user.email}",
        actor_id=user.id
    )
    
    return True, user


def authenticate_user(email, password):
    """
    Authenticates a user via email and password.
    Returns (success: bool, user_or_error: User|str)
    """
    email = email.strip().lower()
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        return False, "Invalid email address or password."
        
    if user.status == 'SUSPENDED':
        return False, "Your account has been suspended. Please contact administrator support."
        
    # Store essential user data in session
    # Store role-scoped session keys to support multi-tab concurrent role testing
    role_key = user.role.lower()
    session[f'{role_key}_user_id'] = user.id
    session[f'{role_key}_user_name'] = user.name
    session[f'{role_key}_email'] = user.email
    session[f'{role_key}_role'] = user.role
    if user.role == 'OWNER':
        session['owner_status'] = user.owner_status
        session['owner_role_status'] = user.owner_status

    # Set active portal default keys
    session['user_id'] = user.id
    session['user_name'] = user.name
    session['email'] = user.email
    session['role'] = user.role
    if user.role == 'OWNER':
        session['owner_status'] = user.owner_status

    log_audit_event(
        action='USER_LOGIN',
        target_entity='User',
        target_id=user.id,
        details=f"Successful login for {user.role}",
        actor_id=user.id
    )
    
    return True, user


def logout_user():
    """Clears active session role and logs audit event."""
    user_id = session.get('user_id')
    current_role = session.get('role', '').lower()
    if user_id:
        log_audit_event(
            action='USER_LOGOUT',
            target_entity='User',
            target_id=user_id,
            details=f"User {current_role.upper()} logged out",
            actor_id=user_id
        )
    if current_role:
        session.pop(f'{current_role}_user_id', None)
        session.pop(f'{current_role}_user_name', None)
        session.pop(f'{current_role}_email', None)
        session.pop(f'{current_role}_role', None)
        session.pop(f'{current_role}_status', None)

    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('email', None)
    session.pop('role', None)
    session.pop('owner_status', None)
