from datetime import date, time, timedelta, datetime
from app.utils.timezone import utcnow
from app import db
from app.models.booking import Booking
from app.models.notification import Notification
from app.services.booking_service import (
    create_booking,
    check_slot_availability,
    update_booking_status,
    cancel_booking_by_driver,
    auto_cancel_no_shows
)

def test_driver_manual_cancellation_and_slot_release(app, test_data):
    """Test that a driver can cancel a booking before check-in, receiving a refund and freeing the slot."""
    with app.app_context():
        b_date = utcnow().date() + timedelta(days=2)
        s_time = time(11, 0)
        e_time = time(13, 0)

        # 1. Driver reserves the single slot
        success, booking = create_booking(
            user_id=test_data['driver_id'],
            parking_space_id=test_data['space_id'],
            booking_date=b_date,
            start_time=s_time,
            end_time=e_time,
            vehicle_type="Car",
            vehicle_plate="KA05AA1234"
        )
        assert success is True
        assert booking.status == "PENDING"
        assert booking.payment_status == "PAID"

        # Slot is now taken
        avail, _ = check_slot_availability(test_data['space_id'], b_date, s_time, e_time)
        assert avail is False

        # 2. Driver cancels the booking
        c_success, msg = cancel_booking_by_driver(
            booking_id=booking.id,
            user_id=test_data['driver_id'],
            reason="Plans changed / No longer needed"
        )
        assert c_success is True
        assert "cancelled" in msg.lower()

        # Check booking status in DB
        db.session.refresh(booking)
        assert booking.status == "CANCELLED"
        assert booking.payment_status == "REFUNDED"
        assert "Plans changed" in booking.cancellation_reason

        # 3. Verify slot is immediately available for another driver
        avail_after, _ = check_slot_availability(test_data['space_id'], b_date, s_time, e_time)
        assert avail_after is True

        # Another driver books the now-released slot
        success2, booking2 = create_booking(
            user_id=test_data['driver_id'],
            parking_space_id=test_data['space_id'],
            booking_date=b_date,
            start_time=s_time,
            end_time=e_time,
            vehicle_type="Car",
            vehicle_plate="KA05ZZ9999"
        )
        assert success2 is True
        assert booking2.status == "PENDING"


def test_cannot_cancel_active_checked_in_booking(app, test_data):
    """Test that a driver cannot cancel a session once already checked in (ACTIVE)."""
    with app.app_context():
        b_date = utcnow().date() + timedelta(days=1)
        success, booking = create_booking(
            user_id=test_data['driver_id'],
            parking_space_id=test_data['space_id'],
            booking_date=b_date,
            start_time=time(14, 0),
            end_time=time(16, 0),
            vehicle_type="Car",
            vehicle_plate="KA05AA5555"
        )
        assert success is True
        booking.status = "ACTIVE"
        booking.check_in_time = utcnow()
        db.session.commit()

        c_success, msg = cancel_booking_by_driver(
            booking_id=booking.id,
            user_id=test_data['driver_id'],
            reason="Trying to cancel after parked"
        )
        assert c_success is False
        assert "cannot cancel" in msg.lower() and "active" in msg.lower()


def test_auto_cancel_no_show_after_30_minutes(app, test_data, monkeypatch):
    """Test that reservations past scheduled start + 30m grace period are auto-cancelled and refunded."""
    with app.app_context():
        test_date = date(2026, 9, 8)
        sched_start = time(10, 0)
        sched_end = time(12, 0)

        # Mock current time to 10:45 AM (45 minutes past start -> past 30-min grace deadline)
        simulated_now = datetime.combine(test_date, time(10, 45))
        import app.services.booking_service as bs
        monkeypatch.setattr(bs, "now_utc", lambda: simulated_now)

        success, booking = create_booking(
            user_id=test_data['driver_id'],
            parking_space_id=test_data['space_id'],
            booking_date=test_date,
            start_time=sched_start,
            end_time=sched_end,
            vehicle_type="Car",
            vehicle_plate="KA01NS0001"
        )
        assert success is True
        # Owner approved the booking
        booking.status = "APPROVED"
        db.session.commit()

        # Slot should initially be blocked
        # Note: calling check_slot_availability automatically invokes auto_cancel_no_shows()
        cancelled_count = auto_cancel_no_shows()
        assert cancelled_count >= 1

        db.session.refresh(booking)
        assert booking.status == "CANCELLED"
        assert booking.payment_status == "REFUNDED"
        assert "30-minute grace window" in booking.cancellation_reason

        # Notifications were sent to driver and host
        driver_notifs = Notification.query.filter_by(user_id=test_data['driver_id']).all()
        assert any("Auto-Cancelled" in n.title for n in driver_notifs)

        owner_notifs = Notification.query.filter_by(user_id=test_data['owner_id']).all()
        assert any("Auto-Released" in n.title for n in owner_notifs)


def test_booking_within_grace_period_not_cancelled(app, test_data, monkeypatch):
    """Test that a reservation only 10 minutes past start time is NOT cancelled yet."""
    with app.app_context():
        test_date = date(2026, 9, 8)
        sched_start = time(10, 0)
        sched_end = time(12, 0)

        # Mock current time to 10:10 AM (10 minutes past start -> within 30-min grace window)
        simulated_now = datetime.combine(test_date, time(10, 10))
        import app.services.booking_service as bs
        monkeypatch.setattr(bs, "now_utc", lambda: simulated_now)

        success, booking = create_booking(
            user_id=test_data['driver_id'],
            parking_space_id=test_data['space_id'],
            booking_date=test_date,
            start_time=sched_start,
            end_time=sched_end,
            vehicle_type="Car",
            vehicle_plate="KA01ONTIME"
        )
        assert success is True
        booking.status = "APPROVED"
        db.session.commit()

        auto_cancel_no_shows()

        db.session.refresh(booking)
        assert booking.status == "APPROVED"
        assert booking.payment_status == "PAID"


def test_owner_release_no_show_endpoint(app, client, test_data):
    """Test that a host can use the release-no-show route to release an overdue bay."""
    with app.app_context():
        b_date = utcnow().date()
        success, booking = create_booking(
            user_id=test_data['driver_id'],
            parking_space_id=test_data['space_id'],
            booking_date=b_date,
            start_time=time(8, 0),
            end_time=time(10, 0),
            vehicle_type="Car",
            vehicle_plate="KA09HOST01"
        )
        assert success is True
        booking.status = "APPROVED"
        db.session.commit()
        b_id = booking.id

    # Log in as Owner
    with client.session_transaction() as sess:
        sess['user_id'] = test_data['owner_id']
        sess['role'] = 'OWNER'

    # Post to release-no-show
    res = client.post(f"/owner/bookings/{b_id}/release-no-show", follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        b = db.session.get(Booking, b_id)
        assert b.status == "CANCELLED"
        assert b.payment_status == "REFUNDED"
        assert "no-show" in b.cancellation_reason.lower()
