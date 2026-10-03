from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models.user import User
from app.models.parking import ParkingSpace
from app.models.booking import Booking
from app.models.review import Review
from app.models.audit import AuditLog
from app.models.notification import Notification
from app.utils.decorators import login_required, role_required
from app.services.analytics_service import get_admin_system_analytics
from app.services.audit_service import log_audit_event

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@login_required
@role_required('ADMIN')
def ensure_admin():
    """Guards all /admin routes strictly for ADMIN role."""
    pass


@admin_bp.route('/dashboard')
def dashboard():
    """Admin Master Command Center."""
    analytics = get_admin_system_analytics()
    
    # Recent pending owner applications
    pending_owners = User.query.filter_by(role='OWNER', owner_status='PENDING').limit(5).all()
    
    # Recent audit events
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()

    return render_template(
        'admin/dashboard.html',
        analytics=analytics,
        pending_owners=pending_owners,
        recent_logs=recent_logs
    )


@admin_bp.route('/owners')
def owners_approval():
    """Manage Property Owner verification queue and accounts."""
    status_filter = request.args.get('status', 'ALL')
    query = User.query.filter_by(role='OWNER')
    
    if status_filter != 'ALL':
        query = query.filter_by(owner_status=status_filter)
        
    owners = query.order_by(User.created_at.desc()).all()
    return render_template('admin/owners_approval.html', owners=owners, status_filter=status_filter)


@admin_bp.route('/owners/<int:user_id>/action', methods=['POST'])
def handle_owner_action(user_id):
    """Processes Approve, Reject, or Suspend actions for property owners."""
    owner = User.query.filter_by(id=user_id, role='OWNER').first_or_404()
    action = request.form.get('action') # APPROVE, REJECT, SUSPEND, ACTIVATE
    reason = request.form.get('reason', '').strip()

    if action == 'APPROVE':
        owner.owner_status = 'APPROVED'
        owner.status = 'ACTIVE'
        owner.rejection_reason = None
        notif_msg = "Congratulations! Your Property Owner application has been approved. You can now list parking spaces."
        flash(f"Owner {owner.name} approved successfully.", 'success')
    elif action == 'REJECT':
        owner.owner_status = 'REJECTED'
        owner.rejection_reason = reason or "Verification criteria not met"
        notif_msg = f"Your Property Owner application was rejected. Reason: {owner.rejection_reason}"
        flash(f"Owner {owner.name} application rejected.", 'info')
    elif action == 'SUSPEND':
        owner.owner_status = 'SUSPENDED'
        owner.status = 'SUSPENDED'
        notif_msg = "Your owner account has been suspended by administration."
        flash(f"Owner {owner.name} suspended.", 'warning')
    elif action == 'ACTIVATE':
        owner.owner_status = 'APPROVED'
        owner.status = 'ACTIVE'
        notif_msg = "Your owner account has been reactivated."
        flash(f"Owner {owner.name} reactivated.", 'success')

    # Send In-App Notification to owner
    notif = Notification(
        user_id=owner.id,
        title=f"Account Status Update: {action}",
        message=notif_msg,
        link="/owner/approval-status"
    )
    db.session.add(notif)
    db.session.commit()

    # Dispatch Email Notification
    try:
        from app.services.email_service import send_owner_approval_email, send_owner_rejection_email
        if action in ['APPROVE', 'ACTIVATE']:
            send_owner_approval_email(owner)
        elif action == 'REJECT':
            send_owner_rejection_email(owner, reason)
    except Exception as e:
        print(f"Email dispatch warning: {e}")

    log_audit_event(
        action=f"OWNER_{action}",
        target_entity='User',
        target_id=owner.id,
        details=f"Admin {action} on owner {owner.email}. Reason: {reason}",
        actor_id=session['user_id']
    )

    return redirect(url_for('admin.owners_approval'))


@admin_bp.route('/spaces')
def spaces_manage():
    """Admin moderation for all parking listings."""
    spaces = ParkingSpace.query.order_by(ParkingSpace.created_at.desc()).all()
    return render_template('admin/spaces_manage.html', spaces=spaces)


@admin_bp.route('/spaces/<int:space_id>/toggle', methods=['POST'])
def toggle_space(space_id):
    """Admin toggles active state of parking space."""
    space = ParkingSpace.query.get_or_404(space_id)
    space.is_active = not space.is_active
    db.session.commit()

    log_audit_event(
        action='ADMIN_TOGGLE_SPACE',
        target_entity='ParkingSpace',
        target_id=space.id,
        details=f"Status changed to {'Active' if space.is_active else 'Inactive'}",
        actor_id=session['user_id']
    )
    flash(f"Parking space '{space.title}' status updated.", 'info')
    return redirect(url_for('admin.spaces_manage'))


@admin_bp.route('/bookings')
def bookings_manage():
    """Admin view of all platform bookings with status filter."""
    status_filter = request.args.get('status', 'ALL')
    query = Booking.query
    
    if status_filter != 'ALL':
        query = query.filter_by(status=status_filter)
        
    bookings = query.order_by(Booking.created_at.desc()).all()
    return render_template('admin/bookings_manage.html', bookings=bookings, status_filter=status_filter)


@admin_bp.route('/users')
def users_manage():
    """Platform user and driver management."""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users_manage.html', users=users)


@admin_bp.route('/users/<int:user_id>/toggle-suspend', methods=['POST'])
def toggle_user_suspension(user_id):
    """Admin suspends or reactivates a user account."""
    user = User.query.get_or_404(user_id)
    if user.id == session['user_id']:
        flash('Cannot suspend your own admin account.', 'danger')
        return redirect(url_for('admin.users_manage'))

    user.status = 'SUSPENDED' if user.status == 'ACTIVE' else 'ACTIVE'
    db.session.commit()

    log_audit_event(
        action='USER_SUSPENSION_TOGGLED',
        target_entity='User',
        target_id=user.id,
        details=f"User {user.email} is now {user.status}",
        actor_id=session['user_id']
    )
    flash(f"User {user.email} status is now {user.status}.", 'info')
    return redirect(url_for('admin.users_manage'))


@admin_bp.route('/reviews')
def reviews_manage():
    """Review and rating moderation console."""
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template('admin/reviews_manage.html', reviews=reviews)


@admin_bp.route('/reviews/<int:review_id>/moderate', methods=['POST'])
def moderate_review(review_id):
    """Flags or hides an inappropriate review."""
    review = Review.query.get_or_404(review_id)
    review.is_moderated = not review.is_moderated
    db.session.commit()

    log_audit_event(
        action='REVIEW_MODERATED',
        target_entity='Review',
        target_id=review.id,
        details=f"Review {'hidden' if review.is_moderated else 'restored'}",
        actor_id=session['user_id']
    )
    flash(f"Review status updated.", 'info')
    return redirect(url_for('admin.reviews_manage'))


@admin_bp.route('/analytics')
def analytics():
    """Deep-dive system analytics and demand reports."""
    stats = get_admin_system_analytics()
    return render_template('admin/analytics.html', stats=stats)


@admin_bp.route('/audit-logs')
def audit_logs():
    """Audit log trail for security and viva traceability."""
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    return render_template('admin/audit_logs.html', logs=logs)
