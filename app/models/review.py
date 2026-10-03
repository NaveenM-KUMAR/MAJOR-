from datetime import datetime
from app.utils.timezone import utcnow
from app import db

class Review(db.Model):
    """Review & Rating model for completed parking sessions."""
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'), unique=True, nullable=False)
    parking_space_id = db.Column(db.Integer, db.ForeignKey('parking_spaces.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    rating = db.Column(db.Integer, nullable=False) # 1 to 5
    comment = db.Column(db.Text, nullable=False)
    is_moderated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'parking_space_id': self.parking_space_id,
            'user_id': self.user_id,
            'user_name': self.reviewer.name if self.reviewer else 'Verified Driver',
            'rating': self.rating,
            'comment': self.comment,
            'is_moderated': self.is_moderated,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else ''
        }

    def __repr__(self):
        return f"<Review {self.id}: {self.rating} stars for Space {self.parking_space_id}>"
