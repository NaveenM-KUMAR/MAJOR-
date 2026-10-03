import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
os.makedirs(INSTANCE_DIR, exist_ok=True)
SQLITE_DB_PATH = os.path.join(INSTANCE_DIR, 'community_parking.db')

def get_database_uri():
    """
    Checks if MySQL connection is live. If MySQL is unreachable,
    cleanly falls back to local SQLite so the system is 100% executable anytime.
    """
    db_url = os.environ.get('DATABASE_URL')
    if db_url and not db_url.startswith('mysql'):
        return db_url
        
    mysql_user = os.environ.get('MYSQL_USER', 'root')
    configured_pwd = os.environ.get('MYSQL_PASSWORD', '12345678')
    mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
    try:
        mysql_port = int(os.environ.get('MYSQL_PORT', 3306))
    except (ValueError, TypeError):
        mysql_port = 3306
    mysql_db = os.environ.get('MYSQL_DATABASE', 'community_parking_db')

    # Passwords to attempt: explicit env var, then XAMPP default (''), then fallback
    passwords_to_try = [configured_pwd]
    if '' not in passwords_to_try:
        passwords_to_try.append('')
    if 'root' not in passwords_to_try:
        passwords_to_try.append('root')

    for pwd in passwords_to_try:
        try:
            conn = pymysql.connect(
                host=mysql_host,
                user=mysql_user,
                password=pwd,
                port=mysql_port,
                connect_timeout=2
            )
            cur = conn.cursor()
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{mysql_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()
            conn.close()
            return f"mysql+pymysql://{mysql_user}:{pwd}@{mysql_host}:{mysql_port}/{mysql_db}"
        except Exception:
            continue

    # Graceful SQLite fallback for local developer machines & offline testing
    return f"sqlite:///{SQLITE_DB_PATH}"

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'cps-dev-secret-key-super-secure-2026')
    
    # Uploads settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
    
    # Email settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'Community Parking System <noreply@cps.com>')

    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True
    }

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

config_dict = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
