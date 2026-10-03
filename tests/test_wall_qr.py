import pytest
from app import create_app, db
from app.models.user import User
from app.models.parking import ParkingSpace
from app.models.booking import Booking
from app.services.qr_service import generate_space_qr_base64
from app.utils.timezone import utcnow
from datetime import time, timedelta
from decimal import Decimal

@pytest.fixture
def app_instance():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app_instance):
    return app_instance.test_client()

def test_space_qr_generation():
    """Verifies that space signboard QR image generates correctly as a Base64 data URI."""
    qr_data = generate_space_qr_base64(space_id=42, scan_url="http://testserver/driver/space-scan/42")
    assert qr_data.startswith("data:image/png;base64,")
    assert len(qr_data) > 100

def test_owner_print_space_sign(client, app_instance):
    """Verifies owner can access printable parking signboard."""
    with app_instance.app_context():
        owner = User(name="Host Test", email="host@test.com", phone="9998887771", role="OWNER", owner_status="APPROVED")
        owner.set_password("pass123")
        db.session.add(owner)
        db.session.commit()

        space = ParkingSpace(
            owner_id=owner.id,
            title="Driveway Bay A",
            description="Safe and secure residential driveway parking bay.",
            address="12 MG Road",
            locality="Central",
            city="Bangalore",
            latitude=Decimal("12.9716"),
            longitude=Decimal("77.5946"),
            total_slots=2,
            price_per_hour=Decimal("30.00"),
            operating_start=time(6, 0),
            operating_end=time(22, 0),
            is_active=True,
            approval_status="APPROVED"
        )
        db.session.add(space)
        db.session.commit()
        space_id = space.id
        owner_id = owner.id

    with client.session_transaction() as sess:
        sess['user_id'] = owner_id
        sess['role'] = 'OWNER'

    resp = client.get(f"/owner/spaces/{space_id}/print-sign")
    assert resp.status_code == 200
    assert b"Reserved Smart Parking" in resp.data
    assert b"data:image/png;base64," in resp.data
    assert b"Driveway Bay A" in resp.data

def test_driver_self_check_in_out_lifecycle(client, app_instance):
    """
    Tests complete self-service driver lifecycle:
    1. Scan space without booking -> Prompts reservation
    2. Has APPROVED booking -> Executes Self Check-In -> Becomes ACTIVE
    3. Has ACTIVE booking -> Executes Self Check-Out -> Becomes COMPLETED
    """
    with app_instance.app_context():
        owner = User(name="Space Host", email="host2@test.com", phone="9998887772", role="OWNER", owner_status="APPROVED")
        owner.set_password("pass123")
        driver = User(name="Driver Dave", email="dave@test.com", phone="9998887773", role="DRIVER")
        driver.set_password("pass123")
        db.session.add_all([owner, driver])
        db.session.commit()

        space = ParkingSpace(
            owner_id=owner.id,
            title="Koramangala Bay 1",
            description="Private covered residential parking bay.",
            address="5th Block",
            locality="Koramangala",
            city="Bangalore",
            latitude=Decimal("12.9352"),
            longitude=Decimal("77.6245"),
            total_slots=1,
            price_per_hour=Decimal("40.00"),
            operating_start=time(6, 0),
            operating_end=time(23, 0),
            is_active=True,
            approval_status="APPROVED"
        )
        db.session.add(space)
        db.session.commit()
        space_id = space.id
        driver_id = driver.id

    with client.session_transaction() as sess:
        sess['user_id'] = driver_id
        sess['role'] = 'DRIVER'

    # Step 1: Scan with no prior booking
    resp1 = client.get(f"/driver/space-scan/{space_id}")
    assert resp1.status_code == 200
    assert b"No Active Reservation Found" in resp1.data
    assert b"Reserve &amp; Park Right Now" in resp1.data or b"Reserve & Park Right Now" in resp1.data

    # Step 2: Create an APPROVED booking
    with app_instance.app_context():
        booking = Booking(
            booking_reference=Booking.generate_reference(),
            user_id=driver_id,
            parking_space_id=space_id,
            booking_date=utcnow().date(),
            start_time=time(10, 0),
            end_time=time(12, 0),
            duration_hours=Decimal('2.0'),
            vehicle_type='Car',
            vehicle_plate='KA01MJ9999',
            total_price=Decimal('80.00'),
            status='APPROVED',
            qr_token=Booking.generate_qr_token()
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id

    # Step 3: GET scan terminal -> Sees Check-In prompt
    resp2 = client.get(f"/driver/space-scan/{space_id}")
    assert resp2.status_code == 200
    assert b"Ready to Check-In" in resp2.data

    # Step 4: POST Check-In (follows redirect to ?status=checked_in)
    resp3 = client.post(f"/driver/space-scan/{space_id}", data={'action': 'CHECK_IN'}, follow_redirects=True)
    assert resp3.status_code == 200
    assert b"You&#39;re Checked In!" in resp3.data or b"You're Checked In!" in resp3.data

    # REFRESH TEST 1: Refreshing the tab after check-in must preserve the check-in confirmation page!
    refreshed_checkin = client.get(resp3.request.path + "?" + resp3.request.query_string.decode('utf-8'))
    assert refreshed_checkin.status_code == 200
    assert b"You&#39;re Checked In!" in refreshed_checkin.data or b"You're Checked In!" in refreshed_checkin.data

    with app_instance.app_context():
        updated_b = db.session.get(Booking, booking_id)
        assert updated_b.status == 'ACTIVE'
        assert updated_b.check_in_time is not None

    # Step 5: Fresh visit to scan terminal (without status param) -> Sees Check-Out prompt
    resp4 = client.get(f"/driver/space-scan/{space_id}")
    assert resp4.status_code == 200
    assert b"Ready to Check-Out?" in resp4.data

    # Step 6: POST Check-Out (follows redirect to ?status=checked_out)
    resp5 = client.post(f"/driver/space-scan/{space_id}", data={'action': 'CHECK_OUT'}, follow_redirects=True)
    assert resp5.status_code == 200
    assert b"Check-Out Complete!" in resp5.data or b"Exit Confirmed!" in resp5.data

    # REFRESH TEST 2: Refreshing the tab after check-out must preserve the checkout confirmation receipt!
    refreshed_checkout = client.get(resp5.request.path + "?" + resp5.request.query_string.decode('utf-8'))
    assert refreshed_checkout.status_code == 200
    assert b"Exit Confirmed!" in refreshed_checkout.data or b"Check-Out Complete!" in refreshed_checkout.data

    with app_instance.app_context():
        final_b = db.session.get(Booking, booking_id)
        assert final_b.status == 'COMPLETED'
        assert final_b.check_out_time is not None
