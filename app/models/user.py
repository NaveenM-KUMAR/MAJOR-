from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from app.utils.timezone import utcnow

# SQLAlchemy instance will be bound in app/__init__.py
from app import db

class User(db.Model):
    """User Model representing Drivers, Owners, and Admins."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Roles: 'DRIVER', 'OWNER', 'ADMIN'
    role = db.Column(db.String(20), nullable=False, default='DRIVER', index=True)
    
    # Account status: 'ACTIVE', 'SUSPENDED'
    status = db.Column(db.String(20), nullable=False, default='ACTIVE')
    
    # Owner Verification Workflow: 'PENDING', 'APPROVED', 'REJECTED', 'SUSPENDED'
    owner_status = db.Column(db.String(20), nullable=True, default=None, index=True)
    owner_id_proof = db.Column(db.String(255), nullable=True)
    owner_address = db.Column(db.String(255), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    upi_id = db.Column(db.String(100), nullable=True) # Default owner UPI ID
    
    profile_image = db.Column(db.String(255), default='default_avatar.png')
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    parking_spaces = db.relationship('ParkingSpace', backref='owner', lazy=True, cascade="all, delete-orphan")
    bookings = db.relationship('Booking', backref='driver', lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship('Review', backref='reviewer', lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', backref='recipient', lazy=True, cascade="all, delete-orphan", order_by="desc(Notification.created_at)")

    def set_password(self, password):
        """Hash and store user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify user password against hashed password."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'ADMIN'

    @property
    def is_owner(self):
        return self.role == 'OWNER'

    @property
    def is_driver(self):
        return self.role == 'DRIVER'

    @property
    def is_approved_owner(self):
        return self.role == 'OWNER' and self.owner_status == 'APPROVED' and self.status == 'ACTIVE'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'status': self.status,
            'owner_status': self.owner_status,
            'owner_address': self.owner_address,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

    def __repr__(self):
        return f"<User {self.id}: {self.email} ({self.role})>"
