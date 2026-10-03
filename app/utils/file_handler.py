import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

def allowed_file(filename):
    """Check if file has an allowed extension."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config['ALLOWED_EXTENSIONS']

def save_uploaded_file(file_storage, folder_name='uploads', custom_prefix='space'):
    """
    Saves an uploaded file securely with a randomized unique name.
    Returns the relative path / filename stored.
    """
    if not file_storage or file_storage.filename == '':
        return None
        
    if not allowed_file(file_storage.filename):
        raise ValueError("Unsupported file extension. Allowed: PNG, JPG, JPEG, WEBP, GIF")
        
    original_filename = secure_filename(file_storage.filename)
    ext = original_filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{custom_prefix}_{uuid.uuid4().hex[:10]}.{ext}"
    
    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, unique_filename)
    file_storage.save(file_path)
    
    return unique_filename
