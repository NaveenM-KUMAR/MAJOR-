from datetime import datetime, time, date, timedelta
from app.utils.timezone import utcnow
from app.models.booking import Booking
from app.services.booking_service import create_booking, update_booking_status, process_qr_check_in, process_qr_check_out
from app.services.qr_service import generate_qr_base64

def test_qr_generation_and_checkin_checkout(app, test_data):
    with app.app_context():
        # Create booking and approve
        b_date = utcnow().date()
        success, booking = create_booking(
            user_id=test_data['driver_id'],
            parking_space_id=test_data['space_id'],
            booking_date=b_date,
            start_time=time(9, 0),
            end_time=time(11, 0),
            vehicle_type="Car",
            vehicle_plate="KA03CC3333"
        )
        update_booking_status(booking.id, "APPROVED", test_data['owner_id'])
        
        # Test QR generation
        qr_data_uri = generate_qr_base64(booking.qr_token)
        assert qr_data_uri.startswith("data:image/png;base64,")

        # Process QR check-in
        checkin_success, checked_in_booking = process_qr_check_in(booking.qr_token, test_data['owner_id'])
        assert checkin_success is True
        assert checked_in_booking.status == "ACTIVE"
        assert checked_in_booking.check_in_time is not None

        # Duplicate check-in should fail
        dup_success, dup_err = process_qr_check_in(booking.qr_token, test_data['owner_id'])
        assert dup_success is False
        assert "already been checked in" in dup_err

        # Process QR check-out
        checkout_success, completed_booking = process_qr_check_out(booking.qr_token, test_data['owner_id'])
        assert checkout_success is True
        assert completed_booking.status == "COMPLETED"
        assert completed_booking.check_out_time is not None
