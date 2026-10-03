import os
from datetime import datetime, timedelta
from flask import Flask, render_template, session, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from app.config import config_dict

db = SQLAlchemy()

def create_app(config_name=None):
    """
    Application Factory for Community Parking System.
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_dict.get(config_name, config_dict['default']))

    # Ensure uploads and instance folders exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, '..', 'instance'), exist_ok=True)

    # Initialize SQLAlchemy
    db.init_app(app)

    @app.before_request
    def resolve_scoped_role_session():
        """
        Enables seamless multi-tab concurrent role testing for viva demonstration:
        Isolates session identity based on the current portal URL prefix (/admin, /owner, /driver).
        Refreshing an Admin tab will not flip it to an Owner tab and vice-versa.
        """
        path = request.path
        target_role = None
        if path.startswith('/admin'):
            target_role = 'admin'
        elif path.startswith('/owner') or path.startswith('/api/owner') or path == '/api/analytics/owner':
            target_role = 'owner'
        elif path.startswith('/driver'):
            target_role = 'driver'

        if target_role and f'{target_role}_user_id' in session:
            session['user_id'] = session[f'{target_role}_user_id']
            session['role'] = session[f'{target_role}_role']
            session['user_name'] = session.get(f'{target_role}_user_name', '')
            session['email'] = session.get(f'{target_role}_email', '')
            if target_role == 'owner' and 'owner_role_status' in session:
                session['owner_status'] = session['owner_role_status']

    # Register Jinja context processors & filters
    @app.context_processor
    def inject_current_user():
        from app.models.user import User
        from app.models.notification import Notification
        from app.models.booking import Booking
        current_user = None
        unread_notifications = 0
        recent_notifications = []
        active_stay = None
        if 'user_id' in session:
            current_user = db.session.get(User, session['user_id'])
            if current_user:
                unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
                recent_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
                if current_user.role == 'DRIVER':
                    active_stay = Booking.query.filter_by(user_id=current_user.id, status='ACTIVE').first()
        return dict(
            current_user=current_user,
            unread_notifications=unread_notifications,
            recent_notifications=recent_notifications,
            active_stay=active_stay
        )

    @app.template_filter('currency')
    def format_currency(val):
        try:
            return f"₹{float(val):,.2f}"
        except (ValueError, TypeError):
            return "₹0.00"

    @app.template_filter('badge_status')
    def badge_status(status):
        badges = {
            'APPROVED': 'bg-success',
            'ACTIVE': 'bg-primary',
            'COMPLETED': 'bg-dark',
            'PENDING': 'bg-warning text-dark',
            'CANCELLED': 'bg-danger',
            'REJECTED': 'bg-secondary',
            'SUSPENDED': 'bg-danger'
        }
        return badges.get(status, 'bg-info')

    @app.template_filter('time_ago')
    def time_ago_filter(dt):
        if not dt:
            return '—'
        now = datetime.now()
        diff = now - dt
        seconds = diff.total_seconds()
        if seconds < 0:
            return dt.strftime('%I:%M %p')
        if seconds < 60:
            return 'Just now'
        minutes = int(seconds // 60)
        if minutes < 60:
            return f'{minutes}m ago'
        hours = int(minutes // 60)
        if hours < 24 and dt.date() == now.date():
            return f'{hours}h ago'
        if dt.date() == (now - timedelta(days=1)).date():
            return f'Yesterday, {dt.strftime("%I:%M %p")}'
        if dt.year == now.year:
            return dt.strftime('%b %d, %I:%M %p')
        return dt.strftime('%b %d, %Y, %I:%M %p')

    @app.template_filter('format_time')
    def format_time_filter(t, fmt='%I:%M %p'):
        if not t:
            return '—'
        try:
            return t.strftime(fmt)
        except Exception:
            return str(t)

    @app.template_filter('format_datetime')
    def format_datetime_filter(dt, fmt='%b %d, %Y • %I:%M %p'):
        if not dt:
            return '—'
        try:
            return dt.strftime(fmt)
        except Exception:
            return str(dt)

    @app.template_filter('format_date')
    def format_date_filter(d, fmt='%b %d, %Y'):
        if not d:
            return '—'
        try:
            return d.strftime(fmt)
        except Exception:
            return str(d)

    # Register Blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.driver_routes import driver_bp
    from app.routes.owner_routes import owner_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.api_routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(driver_bp, url_prefix='/driver')
    app.register_blueprint(owner_bp, url_prefix='/owner')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Error Handlers
    @app.errorhandler(400)
    def bad_request_error(e):
        return render_template('errors/400.html', error=e), 400

    @app.errorhandler(403)
    def forbidden_error(e):
        return render_template('errors/403.html', error=e), 403

    @app.errorhandler(404)
    def not_found_error(e):
        return render_template('errors/404.html', error=e), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html', error=e), 500

    with app.app_context():
        db.create_all()
        try:
            from app.models.parking import ParkingSpace
            if not ParkingSpace.query.first():
                from seed_data import seed_database
                seed_database(app)
        except Exception as e:
            app.logger.warning(f"Auto-seed check: {e}")

    return app
