from datetime import datetime

def utcnow():
    """Returns current real-world local datetime without tzinfo for accurate display across all sections."""
    return datetime.now().replace(microsecond=0)
