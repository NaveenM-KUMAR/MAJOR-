from datetime import datetime
from app.utils.timezone import utcnow
from app import db

class AuditLog(db.Model):
    """System Audit Logs for critical operations and security traceability."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    target_entity = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, index=True)

    # Relationship to user who triggered action
    actor = db.relationship('User', foreign_keys=[actor_id], backref='audit_actions')

    def to_dict(self):
        return {
            'id': self.id,
            'actor_id': self.actor_id,
            'actor_name': self.actor.name if self.actor else 'System / Anonymous',
            'action': self.action,
            'target_entity': self.target_entity,
            'target_id': self.target_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }

    def __repr__(self):
        return f"<AuditLog {self.id}: {self.action} on {self.target_entity}:{self.target_id}>"
