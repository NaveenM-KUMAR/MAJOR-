from flask import request
from app import db
from app.models.audit import AuditLog

def log_audit_event(action, target_entity, target_id=None, details=None, actor_id=None):
    """
    Records an administrative or critical operational action in the audit trail.
    """
    try:
        ip_addr = request.remote_addr if request else '127.0.0.1'
    except Exception:
        ip_addr = '127.0.0.1'
        
    audit_entry = AuditLog(
        actor_id=actor_id,
        action=action,
        target_entity=target_entity,
        target_id=target_id,
        details=details,
        ip_address=ip_addr
    )
    db.session.add(audit_entry)
    db.session.commit()
    return audit_entry
