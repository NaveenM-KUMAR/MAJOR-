import pytest
from datetime import datetime, time, date, timedelta
from decimal import Decimal
from app import create_app, db
from app.models.user import User
from app.models.parking import ParkingSpace
from app.models.booking import Booking

@pytest.fixture
def app():
    """Create test application configured with SQLite in-memory database."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Test HTTP client."""
    return app.test_client()

@pytest.fixture
def test_data(app):
    """Populates basic testing entities."""
    with app.app_context():
        # Admin
        admin = User(name="Test Admin", email="admin@test.com", phone="1111111111", role="ADMIN")
        admin.set_password("pass123")

        # Owner
        owner = User(name="Test Owner", email="owner@test.com", phone="2222222222", role="OWNER", owner_status="APPROVED")
        owner.set_password("pass123")

        # Pending Owner
        pending_owner = User(name="Pending Owner", email="powner@test.com", phone="3333333333", role="OWNER", owner_status="PENDING")
        pending_owner.set_password("pass123")

        # Driver
        driver = User(name="Test Driver", email="driver@test.com", phone="4444444444", role="DRIVER")
        driver.set_password("pass123")

        db.session.add_all([admin, owner, pending_owner, driver])
        db.session.commit()

        # Parking Space (1 Slot)
        space = ParkingSpace(
            owner_id=owner.id,
            title="Test Driveway",
            description="Secure driveway",
            address="123 Test St",
            locality="Indiranagar",
            city="Bangalore",
            latitude=Decimal('12.9716'),
            longitude=Decimal('77.5946'),
            parking_type="Private Driveway",
            total_slots=1,
            price_per_hour=Decimal('30.00'),
            operating_start=time(6, 0),
            operating_end=time(22, 0),
            is_active=True,
            approval_status="APPROVED"
        )
        db.session.add(space)
        db.session.commit()

        return {
            'admin_id': admin.id,
            'owner_id': owner.id,
            'pending_owner_id': pending_owner.id,
            'driver_id': driver.id,
            'space_id': space.id
        }
