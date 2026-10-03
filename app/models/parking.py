from datetime import datetime, time
from app.utils.timezone import utcnow
from app import db

class ParkingSpace(db.Model):
    """Parking Space Model for community and private listings."""
    __tablename__ = 'parking_spaces'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    locality = db.Column(db.String(100), nullable=False, index=True)
    city = db.Column(db.String(100), nullable=False, default='Bangalore')
    
    latitude = db.Column(db.Numeric(10, 8), nullable=False)
    longitude = db.Column(db.Numeric(11, 8), nullable=False)
    
    # Types: Residential, Commercial, Private Driveway, Open Lot, Covered Garage, Community Shared
    parking_type = db.Column(db.String(50), nullable=False, default='Private Driveway')
    
    # Comma-separated or list of vehicle types: Car, Two Wheeler, SUV, EV
    vehicle_types = db.Column(db.String(100), nullable=False, default='Car, Two Wheeler')
    
    total_slots = db.Column(db.Integer, nullable=False, default=1)
    price_per_hour = db.Column(db.Numeric(8, 2), nullable=False)
    price_per_day = db.Column(db.Numeric(8, 2), nullable=True)
    
    operating_start = db.Column(db.Time, nullable=False, default=time(6, 0))
    operating_end = db.Column(db.Time, nullable=False, default=time(22, 0))
    available_days = db.Column(db.String(100), nullable=False, default='Mon,Tue,Wed,Thu,Fri,Sat,Sun')
    
    rules = db.Column(db.Text, nullable=True)
    amenities = db.Column(db.String(255), default='CCTV, Security, Well Lit')
    image_url = db.Column(db.String(255), default='default_parking.jpg')
    
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    approval_status = db.Column(db.String(20), nullable=False, default='APPROVED') # APPROVED, PENDING, REJECTED
    
    # Owner Direct UPI Payment Configuration
    upi_id = db.Column(db.String(100), nullable=True) # e.g. owner@okhdfcbank or 9876543210@ybl
    upi_qr_image = db.Column(db.String(255), nullable=True) # Custom uploaded UPI QR code file

    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    images = db.relationship('ParkingImage', backref='parking_space', lazy=True, cascade="all, delete-orphan")
    bookings = db.relationship('Booking', backref='parking_space', lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship('Review', backref='parking_space', lazy=True, cascade="all, delete-orphan")

    @property
    def average_rating(self):
        valid_reviews = [r for r in self.reviews if not r.is_moderated]
        if not valid_reviews:
            return 0.0
        return round(sum(r.rating for r in valid_reviews) / len(valid_reviews), 1)

    @property
    def review_count(self):
        return len([r for r in self.reviews if not r.is_moderated])

    def to_dict(self):
        return {
            'id': self.id,
            'owner_id': self.owner_id,
            'owner_name': self.owner.name if self.owner else 'Unknown',
            'title': self.title,
            'description': self.description,
            'address': self.address,
            'locality': self.locality,
            'city': self.city,
            'latitude': float(self.latitude),
            'longitude': float(self.longitude),
            'parking_type': self.parking_type,
            'vehicle_types': self.vehicle_types,
            'total_slots': self.total_slots,
            'price_per_hour': float(self.price_per_hour),
            'price_per_day': float(self.price_per_day) if self.price_per_day else None,
            'operating_start': self.operating_start.strftime('%H:%M') if self.operating_start else '06:00',
            'operating_end': self.operating_end.strftime('%H:%M') if self.operating_end else '22:00',
            'available_days': self.available_days,
            'amenities': [a.strip() for a in self.amenities.split(',')] if self.amenities else [],
            'image_url': self.image_url,
            'is_active': self.is_active,
            'approval_status': self.approval_status,
            'upi_id': self.upi_id,
            'upi_qr_image': self.upi_qr_image,
            'average_rating': self.average_rating,
            'review_count': self.review_count
        }

    def __repr__(self):
        return f"<ParkingSpace {self.id}: {self.title} ({self.locality})>"


class ParkingImage(db.Model):
    """Gallery images for parking spaces."""
    __tablename__ = 'parking_images'

    id = db.Column(db.Integer, primary_key=True)
    parking_space_id = db.Column(db.Integer, db.ForeignKey('parking_spaces.id', ondelete='CASCADE'), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
