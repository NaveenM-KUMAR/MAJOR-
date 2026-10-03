import pytest
from datetime import date, time, timedelta
from app.models.parking import ParkingSpace
from app.models.booking import Booking
from app.utils.distance import haversine_distance, filter_and_rank_by_distance
from app.services.booking_service import create_booking

def test_haversine_distance_calculation():
    # Distance between Koramangala (12.9352, 77.6245) and Indiranagar (12.9784, 77.6408) is ~5.1 km
    dist = haversine_distance(12.9352, 77.6245, 12.9784, 77.6408)
    assert 4.0 <= dist <= 6.5

def test_emergency_ranking_by_proximity(app, test_data):
    with app.app_context():
        spaces = ParkingSpace.query.all()
        # Test target coordinates near space
        ranked = filter_and_rank_by_distance(spaces, 12.9716, 77.5946, max_radius_km=10.0)
        assert len(ranked) >= 1
        assert ranked[0].distance_km is not None

def test_emergency_route_public_access(client, test_data):
    """Emergency route should be publicly accessible without requiring prior login."""
    resp = client.get('/driver/emergency')
    assert resp.status_code == 200
    assert b"EMERGENCY PARKING PRIORITY MODE" in resp.data
    assert b"Refresh My GPS" in resp.data

def test_emergency_booking_instant_auto_approval(app, client, test_data):
    """Emergency bookings must be instantly AUTO-APPROVED so drivers are not left waiting."""
    with app.app_context():
        space = ParkingSpace.query.first()
        from app.models.user import User
        driver = User.query.filter_by(role='DRIVER').first()

        tomorrow = date.today() + timedelta(days=1)
        success, booking = create_booking(
            user_id=driver.id,
            parking_space_id=space.id,
            booking_date=tomorrow,
            start_time=time(10, 0),
            end_time=time(12, 0),
            vehicle_type="Car",
            vehicle_plate="KA05EM9999",
            is_emergency=True,
            payment_method="UPI / Online",
            payment_transaction_id="TXN-EMERGENCY-TEST"
        )
        assert success is True
        assert booking.is_emergency is True
        # Must be automatically APPROVED
        assert booking.status == "APPROVED"
        assert booking.qr_token.startswith("CPS-QR-")

def test_emergency_ticket_view(client, test_data):
    """Driver can view their emergency QR ticket with priority indicators."""
    # Login as driver
    client.post('/auth/login', data={'email': 'driver@test.com', 'password': 'pass123'})
    with client.application.app_context():
        space = ParkingSpace.query.first()
        from app.models.user import User
        driver = User.query.filter_by(role='DRIVER').first()
        tomorrow = date.today() + timedelta(days=1)
        success, booking = create_booking(
            user_id=driver.id,
            parking_space_id=space.id,
            booking_date=tomorrow,
            start_time=time(14, 0),
            end_time=time(16, 0),
            vehicle_type="Car",
            vehicle_plate="KA05EM8888",
            is_emergency=True
        )
        booking_ref = booking.booking_reference

    ticket_resp = client.get(f'/driver/booking/{booking_ref}')
    assert ticket_resp.status_code == 200
    assert b"EMERGENCY" in ticket_resp.data
    assert booking_ref.encode() in ticket_resp.data
