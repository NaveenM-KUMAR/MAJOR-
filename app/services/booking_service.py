from datetime import datetime, date, time, timezone, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_
from app import db

from app.utils.timezone import utcnow

def now_utc():
    return utcnow()

from app.models.booking import Booking
from app.models.parking import ParkingSpace
from app.models.user import User
from app.models.notification import Notification
from app.services.audit_service import log_audit_event

def check_slot_availability(parking_space_id, booking_date, start_time, end_time, exclude_booking_id=None):
    """
    CRITICAL ANTI-DOUBLE-BOOKING ENGINE:
    Validates whether the requested time slot [start_time, end_time] on booking_date
    has available capacity (< total_slots).
    Overlapping condition: (Existing_Start < Requested_End) AND (Existing_End > Requested_Start)
    Only considers bookings with status in ['PENDING', 'APPROVED', 'ACTIVE'].
    """
    # 1. Sweep and auto-cancel overdue no-shows first so freed slots are immediately available
    try:
        auto_cancel_no_shows()
    except Exception as e:
        pass
    parking = db.session.get(ParkingSpace, parking_space_id)
    if not parking or not parking.is_active or parking.approval_status != 'APPROVED':
        return False, "Parking space is inactive, suspended, or unapproved."

    # Verify requested time falls within operating hours
    if start_time < parking.operating_start or end_time > parking.operating_end:
        return False, f"Requested time is outside operating hours ({parking.operating_start.strftime('%H:%M')} to {parking.operating_end.strftime('%H:%M')})."

    # Query conflicting overlapping bookings
    query = Booking.query.filter(
        Booking.parking_space_id == parking_space_id,
        Booking.booking_date == booking_date,
        Booking.status.in_(['PENDING', 'APPROVED', 'ACTIVE']),
        Booking.start_time < end_time,
        Booking.end_time > start_time
    )

    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)

    conflicting_count = query.count()
    available_slots = parking.total_slots - conflicting_count

    if available_slots <= 0:
        return False, f"All {parking.total_slots} slot(s) for this parking space are booked during the selected time period."

    return True, f"{available_slots} slot(s) available."


def create_booking(user_id, parking_space_id, booking_date, start_time, end_time, vehicle_type, vehicle_plate, is_emergency=False, payment_method='UPI / Online', payment_transaction_id=None, payment_status='PAID'):
    """
    Creates a new reservation with transactional safety and double-booking checks.
    Integrates verified payment transaction details.
    """
    # Format and parse input dates/times if passed as strings
    if isinstance(booking_date, str):
        booking_date = datetime.strptime(booking_date, '%Y-%m-%d').date()
    if isinstance(start_time, str):
        start_time = datetime.strptime(start_time, '%H:%M').time()
    if isinstance(end_time, str):
        end_time = datetime.strptime(end_time, '%H:%M').time()

    if start_time >= end_time:
        return False, "End time must be after start time."

    parking = db.session.get(ParkingSpace, parking_space_id)
    if not parking:
        return False, "Parking space not found."

    user = db.session.get(User, user_id)
    if not user or user.status == 'SUSPENDED':
        return False, "User account is inactive or suspended."

    # Validate slot availability atomically
    is_avail, msg = check_slot_availability(parking_space_id, booking_date, start_time, end_time)
    if not is_avail:
        return False, msg

    # Calculate duration and price
    dt_start = datetime.combine(booking_date, start_time)
    dt_end = datetime.combine(booking_date, end_time)
    duration_hours = Decimal(str(round((dt_end - dt_start).total_seconds() / 3600.0, 2)))
    
    total_price = Decimal(str(parking.price_per_hour)) * duration_hours
    if total_price < Decimal('1.00'):
        total_price = Decimal(str(parking.price_per_hour))

    booking_ref = Booking.generate_reference()
    qr_token = Booking.generate_qr_token()

    if not payment_transaction_id:
        from app.services.payment_service import generate_transaction_id
        payment_transaction_id = generate_transaction_id(payment_method or 'UPI')

    # If emergency mode, pre-approve or request approval
    # Regular community bookings start as PENDING or APPROVED based on policy
    status = 'APPROVED' if is_emergency else 'PENDING'

    booking = Booking(
        booking_reference=booking_ref,
        user_id=user_id,
        parking_space_id=parking_space_id,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        duration_hours=duration_hours,
        vehicle_type=vehicle_type,
        vehicle_plate=vehicle_plate.upper().strip(),
        total_price=round(total_price, 2),
        payment_status=payment_status or 'PAID',
        payment_method=payment_method or 'UPI / Online',
        payment_transaction_id=payment_transaction_id,
        status=status,
        qr_token=qr_token,
        is_emergency=is_emergency
    )

    db.session.add(booking)
    
    # Notify Parking Owner
    owner_notif = Notification(
        user_id=parking.owner_id,
        title="New Booking Request" if not is_emergency else "Emergency Booking Created",
        message=f"Driver {user.name} booked {parking.title} for {booking_date} ({start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}).",
        link="/owner/bookings"
    )
    db.session.add(owner_notif)

    # If auto-approved (e.g. emergency), notify driver
    if status == 'APPROVED':
        driver_notif = Notification(
            user_id=user.id,
            title="Booking Confirmed!",
            message=f"Your booking {booking_ref} for {parking.title} is confirmed. View your QR ticket.",
            link=f"/driver/bookings"
        )
        db.session.add(driver_notif)

    db.session.commit()

    # Dispatch Email Notifications (Payment Receipt & Owner Alert)
    try:
        from app.services.email_service import send_booking_payment_receipt_email, send_owner_new_booking_alert_email
        send_booking_payment_receipt_email(booking, user, parking, parking.owner)
        send_owner_new_booking_alert_email(booking, parking.owner, parking, user)
    except Exception as e:
        print(f"Email notification warning: {e}")

    log_audit_event(
        action='BOOKING_CREATED',
        target_entity='Booking',
        target_id=booking.id,
        details=f"Reference: {booking_ref}, Space: {parking.title}, Emergency: {is_emergency}",
        actor_id=user_id
    )

    return True, booking


def update_booking_status(booking_id, new_status, actor_user_id, rejection_reason=None):
    """
    Transitions a booking between valid states:
    PENDING -> APPROVED or REJECTED
    APPROVED -> ACTIVE (Check-In) or CANCELLED
    ACTIVE -> COMPLETED (Check-Out)
    """
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return False, "Booking not found."

    valid_transitions = {
        'PENDING': ['APPROVED', 'REJECTED', 'CANCELLED'],
        'APPROVED': ['ACTIVE', 'CANCELLED'],
        'ACTIVE': ['COMPLETED'],
        'REJECTED': [],
        'CANCELLED': [],
        'COMPLETED': []
    }

    if new_status not in valid_transitions.get(booking.status, []):
        return False, f"Invalid status transition from {booking.status} to {new_status}."

    old_status = booking.status
    booking.status = new_status

    if new_status in ['REJECTED', 'CANCELLED'] and rejection_reason:
        booking.cancellation_reason = rejection_reason

    # Process refund status on cancellation
    if new_status == 'CANCELLED':
        booking.payment_status = 'REFUNDED'
        # Also notify property owner that slot has been released
        owner_notif = Notification(
            user_id=booking.parking_space.owner_id,
            title="Slot Released: Booking Cancelled",
            message=f"Booking {booking.booking_reference} for {booking.parking_space.title} has been cancelled ({rejection_reason or 'Cancelled by user'}). Your parking bay is now open and bookable by other drivers.",
            link="/owner/bookings"
        )
        db.session.add(owner_notif)

    # Notify driver of status change
    notif_msg = f"Your booking {booking.booking_reference} for {booking.parking_space.title} is now {new_status}."
    if rejection_reason:
        notif_msg += f" Reason: {rejection_reason}"
    if new_status == 'CANCELLED':
        notif_msg += f" Any paid fee (₹{booking.total_price}) has been refunded."

    driver_notif = Notification(
        user_id=booking.user_id,
        title=f"Booking Status: {new_status}",
        message=notif_msg,
        link="/driver/my_bookings"
    )
    db.session.add(driver_notif)

    db.session.commit()

    log_audit_event(
        action=f"BOOKING_{new_status}",
        target_entity='Booking',
        target_id=booking.id,
        details=f"Transitioned from {old_status} to {new_status}. Reason: {rejection_reason}",
        actor_id=actor_user_id
    )

    return True, f"Booking status updated to {new_status}."


def auto_cancel_no_shows():
    """
    CRITICAL 30-MINUTE GRACE WINDOW ENGINE:
    Inspects all PENDING or APPROVED bookings that have not checked in.
    If the current time is more than 30 minutes past the scheduled start time,
    the reservation is automatically cancelled for NO-SHOW.
    This immediately releases the parking slot back to the community pool.
    """
    current_dt = now_utc()
    today_date = current_dt.date()

    candidates = Booking.query.filter(
        Booking.status.in_(['PENDING', 'APPROVED']),
        Booking.check_in_time.is_(None),
        Booking.booking_date <= today_date
    ).all()

    cancelled_count = 0
    for b in candidates:
        sched_dt = datetime.combine(b.booking_date, b.start_time)
        grace_deadline = sched_dt + timedelta(minutes=30)

        # Past the 30-minute grace window:
        if current_dt > grace_deadline:
            b.status = 'CANCELLED'
            b.cancellation_reason = 'Auto-cancelled: Driver did not check in within the 30-minute grace window.'
            b.payment_status = 'REFUNDED'

            # Notify Driver
            driver_notif = Notification(
                user_id=b.user_id,
                title="Reservation Auto-Cancelled (No-Show)",
                message=f"Your reservation {b.booking_reference} for {b.parking_space.title} was cancelled because check-in was not completed within 30 minutes of {b.start_time.strftime('%I:%M %p')}. The bay has been released.",
                link="/driver/my_bookings"
            )
            # Notify House Owner
            owner_notif = Notification(
                user_id=b.parking_space.owner_id,
                title="Bay Auto-Released (Driver No-Show)",
                message=f"Driver for booking {b.booking_reference} at {b.parking_space.title} did not check in within 30 minutes of scheduled arrival. The slot was auto-released and is now available for other drivers.",
                link="/owner/bookings"
            )
            db.session.add_all([driver_notif, owner_notif])

            log_audit_event(
                action='BOOKING_AUTO_CANCEL_NO_SHOW',
                target_entity='Booking',
                target_id=b.id,
                details=f"Auto-cancelled past 30-minute grace window. Scheduled: {b.start_time}, Deadline: {grace_deadline.strftime('%H:%M')}",
                actor_id=b.parking_space.owner_id
            )
            cancelled_count += 1

    if cancelled_count > 0:
        db.session.commit()

    return cancelled_count


def cancel_booking_by_driver(booking_id, user_id, reason="Cancelled by driver"):
    """
    Cancels an upcoming reservation on behalf of the driver before check-in.
    Frees the slot immediately, marks refund, and notifies the host.
    """
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return False, "Booking not found."
    if booking.user_id != user_id:
        return False, "Unauthorized: You do not own this booking."
    if not booking.can_cancel():
        return False, f"Cannot cancel: Booking is currently {booking.status}."

    success, msg = update_booking_status(booking_id, 'CANCELLED', user_id, rejection_reason=reason)
    return success, msg


def process_qr_check_in(qr_token, owner_or_admin_id):
    """
    Executes driver check-in when owner or admin scans QR code / inputs token.
    Validates token, ensures booking is APPROVED, and sets status to ACTIVE.
    """
    booking = Booking.query.filter_by(qr_token=qr_token).first()
    if not booking:
        return False, "Invalid QR code token. Booking not found."

    if booking.status == 'ACTIVE':
        return False, "This booking has already been checked in."
    if booking.status == 'COMPLETED':
        return False, "This booking has already completed and checked out."
    if booking.status in ['CANCELLED', 'REJECTED']:
        return False, f"Cannot check in: Booking was {booking.status}."
    if booking.status != 'APPROVED':
        return False, f"Booking must be in APPROVED status to check in (Current status: {booking.status})."

    # Set check in time and state
    booking.status = 'ACTIVE'
    booking.check_in_time = now_utc()

    # Notify driver
    notif = Notification(
        user_id=booking.user_id,
        title="Check-In Successful",
        message=f"You have checked in at {booking.parking_space.title}. Enjoy your parking session!",
        link="/driver/bookings"
    )
    db.session.add(notif)
    db.session.commit()

    log_audit_event(
        action='QR_CHECK_IN',
        target_entity='Booking',
        target_id=booking.id,
        details=f"Driver check-in verified for {booking.booking_reference}",
        actor_id=owner_or_admin_id
    )

    return True, booking


def process_qr_check_out(qr_token, owner_or_admin_id):
    """
    Executes driver check-out.
    Validates token, ensures booking was ACTIVE, calculates final duration, and marks COMPLETED.
    """
    booking = Booking.query.filter_by(qr_token=qr_token).first()
    if not booking:
        return False, "Invalid QR code token. Booking not found."

    if booking.status != 'ACTIVE' or not booking.check_in_time:
        return False, "Cannot check out: Booking has not been checked in."

    booking.status = 'COMPLETED'
    booking.check_out_time = now_utc()

    # Driver notification inviting review
    notif = Notification(
        user_id=booking.user_id,
        title="Session Completed — Rate Your Experience",
        message=f"Thank you for using Community Parking! Please rate your stay at {booking.parking_space.title}.",
        link="/driver/bookings"
    )
    db.session.add(notif)
    db.session.commit()

    log_audit_event(
        action='QR_CHECK_OUT',
        target_entity='Booking',
        target_id=booking.id,
        details=f"Driver check-out verified for {booking.booking_reference}. Session completed.",
        actor_id=owner_or_admin_id
    )

    return True, booking
