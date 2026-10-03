from app.routes.auth_routes import auth_bp
from app.routes.driver_routes import driver_bp
from app.routes.owner_routes import owner_bp
from app.routes.admin_routes import admin_bp
from app.routes.api_routes import api_bp

__all__ = ['auth_bp', 'driver_bp', 'owner_bp', 'admin_bp', 'api_bp']
