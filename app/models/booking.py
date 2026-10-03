import uuid
from datetime import datetime, date, time
from app.utils.timezone import utcnow
from app import db

class Booking(db.Model):
    """Booking Model managing reservation state, tokens, and check-in/out."""
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    booking_reference = db.Column(db.String(30), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    parking_space_id = db.Column(db.Integer, db.ForeignKey('parking_spaces.id', ondelete='CASCADE'), nullable=False)
    
    booking_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    duration_hours = db.Column(db.Numeric(5, 2), nullable=False)
    
    vehicle_type = db.Column(db.String(50), nullable=False)
    vehicle_plate = db.Column(db.String(30), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Payment status tracking (PAID, PENDING, REFUNDED)
    payment_status = db.Column(db.String(20), nullable=False, default='PAID', index=True)
    payment_method = db.Column(db.String(50), nullable=False, default='UPI / Online')
    payment_transaction_id = db.Column(db.String(100), nullable=True, index=True)
    
    # State transitions: PENDING -> APPROVED -> ACTIVE (Checked-In) -> COMPLETED (Checked-Out)
    # Exceptions: CANCELLED, REJECTED
    status = db.Column(db.String(20), nullable=False, default='PENDING', index=True)
    
    # Unique cryptographic check-in/out verification token
    qr_token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    check_in_time = db.Column(db.DateTime, nullable=True)
    check_out_time = db.Column(db.DateTime, nullable=True)
    cancellation_reason = db.Column(db.Text, nullable=True)
    is_emergency = db.Column(db.Boolean, nullable=False, default=False)
    
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    review = db.relationship('Review', backref='booking', uselist=False, cascade="all, delete-orphan")

    @staticmethod
    def generate_reference():
        """Generates a clean human-readable reference e.g., CPS-2026-A8F2K."""
        random_code = uuid.uuid4().hex[:6].upper()
        return f"CPS-{utcnow().year}-{random_code}"

    @staticmethod
    def generate_qr_token():
        """Generates a secure QR payload token."""
        return f"CPS-QR-{uuid.uuid4().hex}"

    def can_check_in(self):
        """Validates if current booking can be checked in."""
        return self.status == 'APPROVED' and self.check_in_time is None

    def can_check_out(self):
        """Validates if current booking can be checked out."""
        return self.status == 'ACTIVE' and self.check_in_time is not None and self.check_out_time is None

    def can_cancel(self):
        """Only PENDING or APPROVED bookings before check-in can be cancelled."""
        return self.status in ['PENDING', 'APPROVED'] and self.check_in_time is None

    def to_dict(self):
        return {
            'id': self.id,
            'booking_reference': self.booking_reference,
            'user_id': self.user_id,
            'driver_name': self.driver.name if self.driver else 'N/A',
            'driver_phone': self.driver.phone if self.driver else 'N/A',
            'parking_space_id': self.parking_space_id,
            'parking_title': self.parking_space.title if self.parking_space else 'N/A',
            'parking_address': self.parking_space.address if self.parking_space else 'N/A',
            'booking_date': self.booking_date.strftime('%Y-%m-%d') if self.booking_date else '',
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else '',
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else '',
            'duration_hours': float(self.duration_hours),
            'vehicle_type': self.vehicle_type,
            'vehicle_plate': self.vehicle_plate,
            'total_price': float(self.total_price),
            'payment_status': self.payment_status,
            'payment_method': self.payment_method,
            'payment_transaction_id': self.payment_transaction_id,
            'status': self.status,
            'qr_token': self.qr_token,
            'check_in_time': self.check_in_time.strftime('%Y-%m-%d %H:%M:%S') if self.check_in_time else None,
            'check_out_time': self.check_out_time.strftime('%Y-%m-%d %H:%M:%S') if self.check_out_time else None,
            'is_emergency': self.is_emergency,
            'has_review': self.review is not None
        }

    def __repr__(self):
        return f"<Booking {self.booking_reference} ({self.status})>"
