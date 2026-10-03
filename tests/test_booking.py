from datetime import date, time, timedelta, datetime
from app.utils.timezone import utcnow
from app.models.booking import Booking
from app.services.booking_service import create_booking, check_slot_availability, update_booking_status

def test_booking_creation_and_double_booking_prevention(app, test_data):
    with app.app_context():
        b_date = utcnow().date() + timedelta(days=1)
        s_time = time(10, 0)
        e_time = time(12, 0)

        # 1. Create first valid booking (space has 1 slot)
        success, booking1 = create_booking(
            user_id=test_data['driver_id'],
            parking_space_id=test_data['space_id'],
            booking_date=b_date,
            start_time=s_time,
            end_time=e_time,
            vehicle_type="Car",
            vehicle_plate="KA01AA1111"
        )
        assert success is True
        assert booking1.status == "PENDING"
        assert booking1.total_price == 60.00 # 2 hours * 30

        # 2. Attempt overlapping booking for same slot (10:30 to 11:30)
        overlap_s = time(10, 30)
        overlap_e = time(11, 30)
        
        avail, msg = check_slot_availability(test_data['space_id'], b_date, overlap_s, overlap_e)
        assert avail is False
        assert "booked" in msg

        # Attempt create_booking directly
        success2, err2 = create_booking(
            user_id=test_data['driver_id'],
            parking_space_id=test_data['space_id'],
            booking_date=b_date,
            start_time=overlap_s,
            end_time=overlap_e,
            vehicle_type="Car",
            vehicle_plate="KA01AA2222"
        )
        assert success2 is False

def test_booking_state_lifecycle(app, test_data):
    with app.app_context():
        b_date = utcnow().date() + timedelta(days=2)
        success, booking = create_booking(
            user_id=test_data['driver_id'],
            parking_space_id=test_data['space_id'],
            booking_date=b_date,
            start_time=time(14, 0),
            end_time=time(16, 0),
            vehicle_type="Car",
            vehicle_plate="KA02BB2222"
        )
        assert booking.status == "PENDING"

        # Owner approves
        success, _ = update_booking_status(booking.id, "APPROVED", test_data['owner_id'])
        assert success is True
        assert booking.status == "APPROVED"

        # Check-in (APPROVED -> ACTIVE)
        success, _ = update_booking_status(booking.id, "ACTIVE", test_data['owner_id'])
        assert success is True
        assert booking.status == "ACTIVE"

        # Check-out (ACTIVE -> COMPLETED)
        success, _ = update_booking_status(booking.id, "COMPLETED", test_data['owner_id'])
        assert success is True
        assert booking.status == "COMPLETED"

        # Invalid transition (COMPLETED -> PENDING should fail)
        invalid_success, invalid_msg = update_booking_status(booking.id, "PENDING", test_data['owner_id'])
        assert invalid_success is False
