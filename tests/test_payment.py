import pytest
from app import create_app, db
from app.models.user import User
from app.models.parking import ParkingSpace
from app.models.booking import Booking
from app.services.payment_service import generate_upi_payment_details, generate_transaction_id, verify_payment_transaction
from app.services.booking_service import create_booking
from app.utils.timezone import utcnow
from datetime import time
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

def test_upi_qr_generation():
    """Verifies that dynamic UPI URI and QR code are correctly generated."""
    details = generate_upi_payment_details(amount=70.0, booking_ref="CPS-2026-TEST01")
    assert "upi://pay?" in details['upi_uri']
    assert "am=70.00" in details['upi_uri']
    assert "cu=INR" in details['upi_uri']
    assert details['qr_base64'].startswith("data:image/png;base64,")
    assert details['amount'] == "70.00"
    assert 'provider_links' in details
    assert 'phonepe' in details['provider_links']
    assert 'gpay' in details['provider_links']

def test_owner_direct_upi_providers():
    """Verifies that space owner custom UPI ID and name route directly with multi-provider links."""
    owner_vpa = "owner.sharma@okaxis"
    owner_name = "Sharma Parking Space"
    details = generate_upi_payment_details(
        amount=120.0,
        booking_ref="CPS-REF-88",
        payee_vpa=owner_vpa,
        payee_name=owner_name,
        provider="phonepe"
    )
    assert f"pa={owner_vpa}" in details['upi_uri']
    assert details['payee_vpa'] == owner_vpa
    assert details['payee_name'] == owner_name
    assert details['provider_links']['phonepe'].startswith("phonepe://pay?")
    assert details['provider_links']['gpay'].startswith("tez://upi/pay?")
    assert details['provider_links']['paytm'].startswith("paytmmp://pay?")
    assert details['provider_links']['bhim'].startswith("bhim://pay?")

def test_transaction_id_generation():
    """Verifies unique transaction reference formatting."""
    txn_upi = generate_transaction_id("UPI")
    txn_card = generate_transaction_id("CARD")
    txn_nb = generate_transaction_id("NETBANKING")

    assert txn_upi.startswith("TXN-UPI-")
    assert txn_card.startswith("TXN-CARD-")
    assert txn_nb.startswith("TXN-NB-")
    assert len(txn_upi) > 15

def test_payment_verification_helper():
    """Verifies payment transaction validation."""
    res = verify_payment_transaction("UPI / Google Pay", 80.0)
    assert res['success'] is True
    assert res['status'] == 'PAID'
    assert res['method'] == 'UPI / Google Pay'
    assert res['transaction_id'].startswith("TXN-UPI-")

def test_booking_creation_with_verified_payment(app_instance):
    """Verifies that create_booking stores payment status and transaction ID correctly."""
    with app_instance.app_context():
        owner = User(name="Owner Park", email="opark@test.com", phone="9112233445", role="OWNER", owner_status="APPROVED")
        owner.set_password("pass123")
        driver = User(name="Driver Pay", email="dpay@test.com", phone="9112233446", role="DRIVER")
        driver.set_password("pass123")
        db.session.add_all([owner, driver])
        db.session.commit()

        space = ParkingSpace(
            owner_id=owner.id,
            title="Payment Test Bay",
            description="Secure bay with automated payment support.",
            address="100ft Road",
            locality="Indiranagar",
            city="Bangalore",
            latitude=Decimal("12.9784"),
            longitude=Decimal("77.6408"),
            total_slots=2,
            price_per_hour=Decimal("50.00"),
            operating_start=time(6, 0),
            operating_end=time(23, 0),
            is_active=True,
            approval_status="APPROVED"
        )
        db.session.add(space)
        db.session.commit()

        success, booking = create_booking(
            user_id=driver.id,
            parking_space_id=space.id,
            booking_date=utcnow().date(),
            start_time=time(14, 0),
            end_time=time(16, 0),
            vehicle_type="Car",
            vehicle_plate="KA03AB9999",
            payment_method="UPI / Google Pay",
            payment_transaction_id="TXN-UPI-2026-TESTVERIFY",
            payment_status="PAID"
        )

        assert success is True
        assert booking.payment_status == "PAID"
        assert booking.payment_method == "UPI / Google Pay"
        assert booking.payment_transaction_id == "TXN-UPI-2026-TESTVERIFY"
        assert float(booking.total_price) == 100.0
