from datetime import datetime, date, time
from app.utils.timezone import utcnow
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort
from app import db
from app.models.parking import ParkingSpace
from app.models.booking import Booking
from app.models.review import Review
from app.models.user import User
from app.utils.decorators import login_required, role_required
from app.utils.distance import filter_and_rank_by_distance, haversine_distance
from app.services.booking_service import (
    create_booking, update_booking_status, check_slot_availability,
    process_qr_check_in, process_qr_check_out, auto_cancel_no_shows,
    cancel_booking_by_driver
)
from app.services.prediction_service import predict_parking_availability
from app.services.qr_service import generate_qr_base64
from app.services.audit_service import log_audit_event

driver_bp = Blueprint('driver', __name__)

@driver_bp.route('/dashboard')
@login_required
@role_required('DRIVER', 'ADMIN')
def dashboard():
    """Driver Dashboard overview."""
    user_id = session['user_id']
    auto_cancel_no_shows()
    
    # Active / Checked-in booking
    active_booking = Booking.query.filter_by(user_id=user_id, status='ACTIVE').first()
    
    # Upcoming confirmed/pending bookings
    upcoming_bookings = Booking.query.filter(
        Booking.user_id == user_id,
        Booking.status.in_(['PENDING', 'APPROVED']),
        Booking.booking_date >= utcnow().date()
    ).order_by(Booking.booking_date.asc(), Booking.start_time.asc()).limit(3).all()
    
    # Recent completed bookings
    recent_completed = Booking.query.filter_by(
        user_id=user_id,
        status='COMPLETED'
    ).order_by(Booking.created_at.desc()).limit(3).all()

    # Nearby recommended spaces
    recommended_spaces = ParkingSpace.query.filter_by(
        is_active=True,
        approval_status='APPROVED'
    ).limit(4).all()

    # Pre-calculate predictions for recommended spaces
    space_predictions = {}
    for s in recommended_spaces:
        space_predictions[s.id] = predict_parking_availability(s.id)

    # Dynamic active localities from approved spaces
    popular_localities = [
        loc[0] for loc in db.session.query(ParkingSpace.locality)
        .filter(ParkingSpace.is_active == True, ParkingSpace.approval_status == 'APPROVED')
        .distinct().limit(8).all() if loc[0]
    ]

    return render_template(
        'driver/dashboard.html',
        active_booking=active_booking,
        upcoming_bookings=upcoming_bookings,
        recent_completed=recent_completed,
        recommended_spaces=recommended_spaces,
        space_predictions=space_predictions,
        popular_localities=popular_localities
    )


@driver_bp.route('/search')
def search():
    """Search parking spaces with location, vehicle type, price, and smart prediction."""
    auto_cancel_no_shows()
    query_locality = request.args.get('locality', '').strip()
    parking_type = request.args.get('parking_type', '')
    vehicle_type = request.args.get('vehicle_type', '')
    max_price = request.args.get('max_price', type=float)
    sort_by = request.args.get('sort_by', 'rating') # rating, price_asc, distance
    
    # User coordinates (if provided via browser geolocation)
    user_lat = request.args.get('lat', type=float)
    user_lng = request.args.get('lng', type=float)

    query = ParkingSpace.query.filter(
        ParkingSpace.is_active == True,
        ParkingSpace.approval_status == 'APPROVED'
    )

    if query_locality:
        query = query.filter(
            (ParkingSpace.locality.ilike(f"%{query_locality}%")) |
            (ParkingSpace.address.ilike(f"%{query_locality}%")) |
            (ParkingSpace.city.ilike(f"%{query_locality}%")) |
            (ParkingSpace.title.ilike(f"%{query_locality}%"))
        )

    if parking_type:
        query = query.filter(ParkingSpace.parking_type == parking_type)

    if vehicle_type:
        query = query.filter(ParkingSpace.vehicle_types.ilike(f"%{vehicle_type}%"))

    if max_price:
        query = query.filter(ParkingSpace.price_per_hour <= max_price)

    spaces = query.all()

    # Proximity sorting if GPS coords available
    if user_lat is not None and user_lng is not None:
        nearby_spaces = filter_and_rank_by_distance(spaces, user_lat, user_lng, max_radius_km=50.0)
        if nearby_spaces:
            spaces = nearby_spaces
        else:
            # If no space is within 50km, still show available spaces ranked by distance so the map is never empty
            spaces = filter_and_rank_by_distance(spaces, user_lat, user_lng, max_radius_km=None)
    else:
        # Default sort
        if sort_by == 'price_asc':
            spaces.sort(key=lambda s: s.price_per_hour)
        elif sort_by == 'price_desc':
            spaces.sort(key=lambda s: s.price_per_hour, reverse=True)
        else: # rating
            spaces.sort(key=lambda s: s.average_rating, reverse=True)

    # Attach smart prediction data for each space
    predictions = {s.id: predict_parking_availability(s.id) for s in spaces}

    return render_template(
        'driver/search.html',
        spaces=spaces,
        predictions=predictions,
        query_locality=query_locality,
        parking_type=parking_type,
        vehicle_type=vehicle_type,
        max_price=max_price,
        sort_by=sort_by,
        user_lat=user_lat,
        user_lng=user_lng
    )


@driver_bp.route('/emergency')
def emergency():
    """
    EMERGENCY PARKING MODE:
    Immediate 1-click GPS-assisted discovery prioritizing the closest available spaces.
    """
    user_lat = request.args.get('lat', type=float, default=12.9716) # Default Bangalore center if no GPS
    user_lng = request.args.get('lng', type=float, default=77.5946)

    # Fetch all active and approved spaces
    spaces = ParkingSpace.query.filter_by(
        is_active=True,
        approval_status='APPROVED'
    ).all()

    # Rank strictly by distance within 15 km
    nearby_spaces = filter_and_rank_by_distance(spaces, user_lat, user_lng, max_radius_km=15.0)
    if not nearby_spaces and spaces:
        # Fallback to closest available spaces ranked by distance so driver is never stranded
        nearby_spaces = filter_and_rank_by_distance(spaces, user_lat, user_lng, max_radius_km=None)

    # Calculate real-time predictions & immediate availability
    emergency_predictions = {}
    spaces_data = []
    for s in nearby_spaces:
        emergency_predictions[s.id] = predict_parking_availability(s.id)
        d = s.to_dict()
        d['distance_km'] = round(float(getattr(s, 'distance_km', 0.0)), 2)
        spaces_data.append(d)

    return render_template(
        'driver/emergency.html',
        spaces=nearby_spaces,
        spaces_json=spaces_data,
        predictions=emergency_predictions,
        user_lat=user_lat,
        user_lng=user_lng
    )


@driver_bp.route('/parking/<int:space_id>')
def details(space_id):
    """View full parking space details, rules, live prediction, and reviews."""
    space = ParkingSpace.query.get_or_404(space_id)
    prediction = predict_parking_availability(space.id)
    reviews = Review.query.filter_by(parking_space_id=space.id, is_moderated=False).order_by(Review.created_at.desc()).all()

    return render_template(
        'driver/details.html',
        space=space,
        prediction=prediction,
        reviews=reviews
    )


@driver_bp.route('/book/<int:space_id>', methods=['GET', 'POST'])
@login_required
def book(space_id):
    """Booking page with instant slot availability check, interactive payment, and reservation submission."""
    space = db.session.get(ParkingSpace, space_id)
    if not space:
        abort(404)
    is_emergency = request.args.get('emergency', '0') == '1'
    prediction = predict_parking_availability(space.id)

    from app.services.payment_service import generate_upi_payment_details
    owner = space.owner
    payee_vpa = space.upi_id or (owner.upi_id if owner else None) or "communityparking@cps"
    payee_name = (owner.name if owner and owner.name else None) or space.title[:25]
    initial_upi = generate_upi_payment_details(space.price_per_hour, payee_vpa=payee_vpa, payee_name=payee_name)

    if request.method == 'POST':
        booking_date_str = request.form.get('booking_date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        vehicle_type = request.form.get('vehicle_type', 'Car')
        vehicle_plate = request.form.get('vehicle_plate', '').strip()
        payment_method = request.form.get('payment_method', 'UPI / Google Pay')
        payment_transaction_id = request.form.get('payment_transaction_id')
        payment_status = request.form.get('payment_status', 'PAID')

        if not booking_date_str or not start_time_str or not end_time_str or not vehicle_plate:
            flash('Please complete all booking fields including vehicle registration number.', 'warning')
            return render_template('driver/book.html', space=space, prediction=prediction, is_emergency=is_emergency, upi_data=initial_upi)

        try:
            b_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
            s_time = datetime.strptime(start_time_str, '%H:%M').time()
            e_time = datetime.strptime(end_time_str, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format.', 'danger')
            return render_template('driver/book.html', space=space, prediction=prediction, is_emergency=is_emergency, upi_data=initial_upi)

        if b_date < utcnow().date():
            flash('Booking date cannot be in the past.', 'danger')
            return render_template('driver/book.html', space=space, prediction=prediction, is_emergency=is_emergency, upi_data=initial_upi)

        success, result_or_err = create_booking(
            user_id=session['user_id'],
            parking_space_id=space.id,
            booking_date=b_date,
            start_time=s_time,
            end_time=e_time,
            vehicle_type=vehicle_type,
            vehicle_plate=vehicle_plate,
            is_emergency=is_emergency,
            payment_method=payment_method,
            payment_transaction_id=payment_transaction_id,
            payment_status=payment_status
        )

        if not success:
            flash(f"Booking Error: {result_or_err}", 'danger')
            return render_template('driver/book.html', space=space, prediction=prediction, is_emergency=is_emergency, upi_data=initial_upi)

        booking = result_or_err
        flash('Booking and payment confirmed successfully!', 'success')
        return redirect(url_for('driver.booking_ticket', booking_ref=booking.booking_reference))

    return render_template('driver/book.html', space=space, prediction=prediction, is_emergency=is_emergency, upi_data=initial_upi)


@driver_bp.route('/api/payment/upi-qr')
@login_required
def api_get_upi_qr():
    """Generates dynamic UPI QR code for exact fee calculation and selected provider."""
    space_id = request.args.get('space_id', type=int)
    amount = request.args.get('amount', type=float, default=20.0)
    provider = request.args.get('provider', default='generic')
    
    payee_vpa = "communityparking@cps"
    payee_name = "Community Parking System"
    custom_qr_url = None
    
    if space_id:
        space = db.session.get(ParkingSpace, space_id)
        if space:
            owner = space.owner
            payee_vpa = space.upi_id or (owner.upi_id if owner else None) or payee_vpa
            payee_name = (owner.name if owner and owner.name else None) or space.title[:25]
            if space.upi_qr_image:
                custom_qr_url = url_for('static', filename='uploads/' + space.upi_qr_image)

    from app.services.payment_service import generate_upi_payment_details
    details = generate_upi_payment_details(
        amount=amount,
        payee_vpa=payee_vpa,
        payee_name=payee_name,
        provider=provider
    )
    if custom_qr_url:
        details['custom_qr_url'] = custom_qr_url
    return jsonify(details)



@driver_bp.route('/booking/<string:booking_ref>')
@login_required
def booking_ticket(booking_ref):
    """View digital booking receipt with QR Check-In Ticket and GPS directions."""
    booking = Booking.query.filter_by(booking_reference=booking_ref).first_or_404()
    
    # Ensure current user owns this booking or is admin/owner
    if booking.user_id != session['user_id'] and session.get('role') != 'ADMIN' and booking.parking_space.owner_id != session['user_id']:
        flash('Unauthorized to view this booking ticket.', 'danger')
        return redirect(url_for('driver.my_bookings'))

    # Generate QR Code image base64
    qr_image = generate_qr_base64(booking.qr_token)

    return render_template('driver/qr_ticket.html', booking=booking, qr_image=qr_image)


@driver_bp.route('/bookings')
@login_required
def my_bookings():
    """Driver's comprehensive booking history & status management."""
    user_id = session['user_id']
    auto_cancel_no_shows()
    bookings = Booking.query.filter_by(user_id=user_id).order_by(Booking.created_at.desc()).all()

    active_bookings = [b for b in bookings if b.status == 'ACTIVE']
    upcoming_bookings = [b for b in bookings if b.status in ['PENDING', 'APPROVED']]
    completed_bookings = [b for b in bookings if b.status == 'COMPLETED']
    cancelled_bookings = [b for b in bookings if b.status in ['CANCELLED', 'REJECTED']]

    return render_template(
        'driver/my_bookings.html',
        active_bookings=active_bookings,
        upcoming_bookings=upcoming_bookings,
        completed_bookings=completed_bookings,
        cancelled_bookings=cancelled_bookings
    )


@driver_bp.route('/booking/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    """Cancels a pending or approved booking before check-in."""
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id'] and session.get('role') != 'ADMIN':
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('driver.my_bookings'))

    reason = request.form.get('cancellation_reason', 'Cancelled by driver').strip()
    if not reason:
        reason = 'Cancelled by driver'

    success, msg = cancel_booking_by_driver(booking_id, session['user_id'], reason=reason)

    if success:
        flash(f"Booking {booking.booking_reference} cancelled successfully. The bay has been released and any prepaid fee has been refunded.", 'success')
    else:
        flash(msg, 'danger')

    return redirect(url_for('driver.my_bookings'))


@driver_bp.route('/review/<int:booking_id>', methods=['POST'])
@login_required
def submit_review(booking_id):
    """Submits 1-5 star review and feedback for a completed booking session."""
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id']:
        flash('Unauthorized to review this booking.', 'danger')
        return redirect(url_for('driver.my_bookings'))

    if booking.status != 'COMPLETED':
        flash('Reviews can only be submitted for completed parking sessions.', 'warning')
        return redirect(url_for('driver.my_bookings'))

    if booking.review:
        flash('You have already submitted a review for this booking session.', 'info')
        return redirect(url_for('driver.my_bookings'))

    rating = request.form.get('rating', type=int)
    comment = request.form.get('comment', '').strip()

    if not rating or rating < 1 or rating > 5 or not comment:
        flash('Please provide a rating (1 to 5 stars) and a written comment.', 'warning')
        return redirect(url_for('driver.my_bookings'))

    review = Review(
        booking_id=booking.id,
        parking_space_id=booking.parking_space_id,
        user_id=session['user_id'],
        rating=rating,
        comment=comment
    )
    db.session.add(review)
    db.session.commit()

    log_audit_event(
        action='REVIEW_SUBMITTED',
        target_entity='Review',
        target_id=review.id,
        details=f"Rating: {rating}/5 for Space {booking.parking_space.title}",
        actor_id=session['user_id']
    )

    flash('Thank you! Your review and rating have been posted.', 'success')
    return redirect(url_for('driver.my_bookings'))


@driver_bp.route('/space-scan/<int:space_id>', methods=['GET', 'POST'])
@login_required
def space_scan(space_id):
    """
    Self-Service Wall QR Scan Terminal for Drivers.
    Triggered when a driver scans the physical QR sticker mounted at the parking space.
    - If user has an ACTIVE booking: executes or prompts Check-Out.
    - If user has an APPROVED or PENDING booking: executes or prompts Check-In.
    - If user recently completed a booking: displays completed receipt and prevents repeated loops.
    - If user has no active/approved booking: prompts with space details and 1-click Instant Reservation.
    """
    space = db.session.get(ParkingSpace, space_id)
    if not space:
        abort(404)
    user_id = session['user_id']
    auto_execute = request.args.get('auto', '').lower() in ['1', 'true', 'yes']

    # Check for confirmed status query param (?status=checked_in or ?status=checked_out)
    # This ensures that refreshing the browser tab preserves the confirmation receipt and NEVER re-triggers auto-actions!
    status_param = request.args.get('status', '').lower()
    ref_param = request.args.get('ref', '')

    if status_param == 'checked_in':
        target_bkg = None
        if ref_param:
            target_bkg = Booking.query.filter_by(booking_reference=ref_param, user_id=user_id).first()
        if not target_bkg:
            target_bkg = Booking.query.filter_by(parking_space_id=space.id, user_id=user_id, status='ACTIVE').first()
        if target_bkg:
            return render_template('driver/space_scan_result.html', space=space, booking=target_bkg, mode='CHECKED_IN')

    if status_param == 'checked_out':
        target_bkg = None
        if ref_param:
            target_bkg = Booking.query.filter_by(booking_reference=ref_param, user_id=user_id).first()
        if not target_bkg:
            target_bkg = Booking.query.filter_by(parking_space_id=space.id, user_id=user_id, status='COMPLETED').order_by(Booking.check_out_time.desc()).first()
        if target_bkg:
            return render_template('driver/space_scan_result.html', space=space, booking=target_bkg, mode='CHECKED_OUT')

    # 1. Check if driver currently has an ACTIVE stay here -> Ready for Check-Out
    active_booking = Booking.query.filter_by(
        parking_space_id=space.id,
        user_id=user_id,
        status='ACTIVE'
    ).first()

    # 2. Check if driver has an APPROVED reservation ready to enter -> Ready for Check-In
    approved_booking = Booking.query.filter_by(
        parking_space_id=space.id,
        user_id=user_id,
        status='APPROVED'
    ).order_by(Booking.booking_date.asc(), Booking.start_time.asc()).first()

    # 3. If no approved booking and no active booking, check if driver has a PENDING booking for this space
    if not approved_booking and not active_booking:
        pending_booking = Booking.query.filter_by(
            parking_space_id=space.id,
            user_id=user_id,
            status='PENDING'
        ).order_by(Booking.booking_date.asc(), Booking.start_time.asc()).first()
        if pending_booking:
            # Driver has arrived on-site with a valid booking: auto-approve for self check-in
            pending_booking.status = 'APPROVED'
            db.session.commit()
            approved_booking = pending_booking

    # 4. Check for recently completed booking (to prevent unexpected "reserve again" loop right after checkout)
    recent_completed = None
    if not active_booking and not approved_booking:
        recent_completed = Booking.query.filter_by(
            parking_space_id=space.id,
            user_id=user_id,
            status='COMPLETED'
        ).order_by(Booking.check_out_time.desc()).first()

    # Determine action: via POST form submission OR direct camera scan with auto=1
    action = request.form.get('action') if request.method == 'POST' else None
    if auto_execute and not action:
        if active_booking:
            action = 'CHECK_OUT'
        elif approved_booking:
            action = 'CHECK_IN'

    if action == 'CHECK_IN' and approved_booking:
        success, res = process_qr_check_in(approved_booking.qr_token, space.owner_id)
        if success:
            flash(f"Check-In Confirmed! Welcome to {space.title}. Your arrival has been recorded.", 'success')
            return redirect(url_for('driver.space_scan', space_id=space.id, status='checked_in', ref=res.booking_reference))
        else:
            flash(f"Check-In Error: {res}", 'danger')
            return redirect(url_for('driver.space_scan', space_id=space.id))

    elif action == 'CHECK_OUT' and active_booking:
        success, res = process_qr_check_out(active_booking.qr_token, space.owner_id)
        if success:
            flash(f"Check-Out Complete! Total fee: ₹{res.total_price}. Thank you for parking responsibly!", 'success')
            return redirect(url_for('driver.space_scan', space_id=space.id, status='checked_out', ref=res.booking_reference))
        else:
            flash(f"Check-Out Error: {res}", 'danger')
            return redirect(url_for('driver.space_scan', space_id=space.id))

    # GET request evaluation (without auto action or when auto didn't match an active/approved state)
    if active_booking:
        mode = 'ACTIVE' # prompt check-out
        booking = active_booking
    elif approved_booking:
        mode = 'APPROVED' # prompt check-in
        booking = approved_booking
    elif recent_completed:
        mode = 'CHECKED_OUT' # show existing completed checkout state & receipt
        booking = recent_completed
    else:
        mode = 'NO_BOOKING' # prompt walk-up reservation
        booking = None

    return render_template('driver/space_scan_result.html', space=space, booking=booking, mode=mode)


@driver_bp.route('/scanner', methods=['GET', 'POST'])
@login_required
def scanner():
    """
    Driver mobile scanner interface: allows camera scanning of the wall QR code
    or typing the Space ID directly.
    """
    if request.method == 'POST':
        space_id = request.form.get('space_id', type=int)
        if space_id:
            return redirect(url_for('driver.space_scan', space_id=space_id))
        flash('Please provide a valid Space ID from the wall signboard.', 'warning')

    return render_template('driver/scanner.html')

