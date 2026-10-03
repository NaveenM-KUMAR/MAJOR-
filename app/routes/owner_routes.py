from datetime import datetime, time
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort
from app import db
from app.models.user import User
from app.models.parking import ParkingSpace, ParkingImage
from app.models.booking import Booking
from app.models.review import Review
from app.utils.decorators import login_required, role_required, approved_owner_required
from app.utils.file_handler import save_uploaded_file
from app.services.booking_service import update_booking_status, process_qr_check_in, process_qr_check_out, auto_cancel_no_shows
from app.services.analytics_service import get_owner_revenue_analytics
from app.services.audit_service import log_audit_event
from app.services.qr_service import generate_space_qr_base64

owner_bp = Blueprint('owner', __name__)

@owner_bp.route('/approval-status')
@login_required
@role_required('OWNER')
def approval_status():
    """Displays owner account verification status."""
    user = db.session.get(User, session['user_id'])
    return render_template('owner/approval_status.html', user=user)


@owner_bp.route('/dashboard')
@login_required
@approved_owner_required
def dashboard():
    """Owner Management Dashboard overview."""
    auto_cancel_no_shows()
    owner_id = session['user_id']
    spaces = ParkingSpace.query.filter_by(owner_id=owner_id).all()
    space_ids = [s.id for s in spaces]

    # Pending booking requests
    pending_bookings = Booking.query.filter(
        Booking.parking_space_id.in_(space_ids),
        Booking.status == 'PENDING'
    ).order_by(Booking.created_at.desc()).all()

    # Active checked-in vehicles
    active_bookings = Booking.query.filter(
        Booking.parking_space_id.in_(space_ids),
        Booking.status == 'ACTIVE'
    ).all()

    # Analytics summary
    analytics = get_owner_revenue_analytics(owner_id)

    return render_template(
        'owner/dashboard.html',
        spaces=spaces,
        pending_bookings=pending_bookings,
        active_bookings=active_bookings,
        analytics=analytics
    )


@owner_bp.route('/spaces')
@login_required
@approved_owner_required
def manage_spaces():
    """List and manage all listed parking spaces."""
    owner_id = session['user_id']
    spaces = ParkingSpace.query.filter_by(owner_id=owner_id).all()
    return render_template('owner/manage_spaces.html', spaces=spaces)


@owner_bp.route('/spaces/add', methods=['GET', 'POST'])
@login_required
@approved_owner_required
def add_space():
    """Add a new community or private parking space."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        address = request.form.get('address', '').strip()
        locality = request.form.get('locality', '').strip()
        city = request.form.get('city', 'Bangalore').strip()
        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)
        
        parking_type = request.form.get('parking_type', 'Private Driveway')
        vehicle_types = request.form.getlist('vehicle_types')
        vehicle_types_str = ", ".join(vehicle_types) if vehicle_types else 'Car, Two Wheeler'
        
        total_slots = request.form.get('total_slots', type=int, default=1)
        price_per_hour = request.form.get('price_per_hour', type=float, default=20.0)
        price_per_day = request.form.get('price_per_day', type=float)
        
        operating_start_str = request.form.get('operating_start', '06:00')
        operating_end_str = request.form.get('operating_end', '22:00')
        
        available_days = request.form.getlist('available_days')
        available_days_str = ",".join(available_days) if available_days else 'Mon,Tue,Wed,Thu,Fri,Sat,Sun'
        
        rules = request.form.get('rules', '').strip()
        amenities = request.form.getlist('amenities')
        amenities_str = ", ".join(amenities) if amenities else 'CCTV, Well Lit'

        image_file = request.files.get('image')
        image_url = 'default_parking.jpg'

        if image_file and image_file.filename:
            try:
                image_url = save_uploaded_file(image_file, custom_prefix='space')
            except Exception as e:
                flash(f"Image upload warning: {e}", 'warning')

        upi_id = request.form.get('upi_id', '').strip()
        upi_qr_file = request.files.get('upi_qr_image')
        upi_qr_filename = None
        if upi_qr_file and upi_qr_file.filename:
            try:
                upi_qr_filename = save_uploaded_file(upi_qr_file, custom_prefix='upi_qr')
            except Exception as e:
                flash(f"UPI QR upload warning: {e}", 'warning')

        # Fallback to owner user's default UPI ID if not entered for this specific space
        user = db.session.get(User, session['user_id'])
        if not upi_id and user and user.upi_id:
            upi_id = user.upi_id
        elif upi_id and user and not user.upi_id:
            user.upi_id = upi_id

        try:
            op_start = datetime.strptime(operating_start_str, '%H:%M').time()
            op_end = datetime.strptime(operating_end_str, '%H:%M').time()
        except ValueError:
            op_start = time(6, 0)
            op_end = time(22, 0)

        space = ParkingSpace(
            owner_id=session['user_id'],
            title=title,
            description=description,
            address=address,
            locality=locality,
            city=city,
            latitude=Decimal(str(latitude or 12.9716)),
            longitude=Decimal(str(longitude or 77.5946)),
            parking_type=parking_type,
            vehicle_types=vehicle_types_str,
            total_slots=max(1, total_slots),
            price_per_hour=Decimal(str(price_per_hour)),
            price_per_day=Decimal(str(price_per_day)) if price_per_day else None,
            operating_start=op_start,
            operating_end=op_end,
            available_days=available_days_str,
            rules=rules,
            amenities=amenities_str,
            image_url=image_url,
            upi_id=upi_id or None,
            upi_qr_image=upi_qr_filename,
            is_active=True,
            approval_status='APPROVED'
        )

        db.session.add(space)
        db.session.commit()

        log_audit_event(
            action='PARKING_SPACE_CREATED',
            target_entity='ParkingSpace',
            target_id=space.id,
            details=f"Created space: {space.title} ({space.locality})",
            actor_id=session['user_id']
        )

        flash('Parking space listed successfully!', 'success')
        return redirect(url_for('owner.manage_spaces'))

    return render_template('owner/space_form.html', space=None, title='Add Parking Space')


@owner_bp.route('/spaces/<int:space_id>/edit', methods=['GET', 'POST'])
@login_required
@approved_owner_required
def edit_space(space_id):
    """Edit existing parking space listing."""
    space = ParkingSpace.query.filter_by(id=space_id, owner_id=session['user_id']).first_or_404()

    if request.method == 'POST':
        space.title = request.form.get('title', space.title).strip()
        space.description = request.form.get('description', space.description).strip()
        space.address = request.form.get('address', space.address).strip()
        space.locality = request.form.get('locality', space.locality).strip()
        space.city = request.form.get('city', space.city).strip()
        
        lat = request.form.get('latitude', type=float)
        lng = request.form.get('longitude', type=float)
        if lat and lng:
            space.latitude = Decimal(str(lat))
            space.longitude = Decimal(str(lng))
            
        space.parking_type = request.form.get('parking_type', space.parking_type)
        
        v_types = request.form.getlist('vehicle_types')
        if v_types:
            space.vehicle_types = ", ".join(v_types)
            
        space.total_slots = max(1, request.form.get('total_slots', type=int, default=space.total_slots))
        space.price_per_hour = Decimal(str(request.form.get('price_per_hour', float(space.price_per_hour))))
        
        price_day = request.form.get('price_per_day', type=float)
        space.price_per_day = Decimal(str(price_day)) if price_day else None
        
        space.rules = request.form.get('rules', space.rules).strip()
        
        avail_days = request.form.getlist('available_days')
        if avail_days:
            space.available_days = ",".join(avail_days)
            
        op_start_str = request.form.get('operating_start')
        op_end_str = request.form.get('operating_end')
        if op_start_str and op_end_str:
            try:
                space.operating_start = datetime.strptime(op_start_str, '%H:%M').time()
                space.operating_end = datetime.strptime(op_end_str, '%H:%M').time()
            except ValueError:
                pass

        amenities = request.form.getlist('amenities')
        if amenities:
            space.amenities = ", ".join(amenities)

        image_file = request.files.get('image')
        if image_file and image_file.filename:
            try:
                space.image_url = save_uploaded_file(image_file, custom_prefix='space')
            except Exception as e:
                flash(f"Image upload warning: {e}", 'warning')

        new_upi = request.form.get('upi_id', '').strip()
        space.upi_id = new_upi or space.upi_id or None

        upi_qr_file = request.files.get('upi_qr_image')
        if upi_qr_file and upi_qr_file.filename:
            try:
                space.upi_qr_image = save_uploaded_file(upi_qr_file, custom_prefix='upi_qr')
            except Exception as e:
                flash(f"UPI QR upload warning: {e}", 'warning')

        db.session.commit()
        flash('Parking space details updated successfully!', 'success')
        return redirect(url_for('owner.manage_spaces'))

    return render_template('owner/space_form.html', space=space, title='Edit Parking Space')


@owner_bp.route('/spaces/<int:space_id>/toggle-status', methods=['POST'])
@login_required
@approved_owner_required
def toggle_space_status(space_id):
    """Activates or deactivates a parking listing."""
    space = ParkingSpace.query.filter_by(id=space_id, owner_id=session['user_id']).first_or_404()
    space.is_active = not space.is_active
    db.session.commit()
    
    state_str = "activated" if space.is_active else "deactivated"
    flash(f"Parking space '{space.title}' {state_str}.", 'info')
    return redirect(url_for('owner.manage_spaces'))


@owner_bp.route('/bookings')
@login_required
@approved_owner_required
def booking_requests():
    """View and manage booking requests across owner spaces."""
    auto_cancel_no_shows()
    owner_id = session['user_id']
    spaces = ParkingSpace.query.filter_by(owner_id=owner_id).all()
    space_ids = [s.id for s in spaces]

    bookings = Booking.query.filter(
        Booking.parking_space_id.in_(space_ids)
    ).order_by(Booking.created_at.desc()).all()

    pending_bookings = [b for b in bookings if b.status == 'PENDING']
    approved_bookings = [b for b in bookings if b.status == 'APPROVED']
    active_bookings = [b for b in bookings if b.status == 'ACTIVE']
    completed_bookings = [b for b in bookings if b.status == 'COMPLETED']
    history_bookings = [b for b in bookings if b.status in ['COMPLETED', 'CANCELLED', 'REJECTED']]

    return render_template(
        'owner/booking_requests.html',
        pending_bookings=pending_bookings,
        approved_bookings=approved_bookings,
        active_bookings=active_bookings,
        history_bookings=history_bookings
    )


@owner_bp.route('/bookings/<int:booking_id>/approve', methods=['POST'])
@login_required
@approved_owner_required
def approve_booking(booking_id):
    """Approves a pending booking request."""
    booking = Booking.query.get_or_404(booking_id)
    if booking.parking_space.owner_id != session['user_id']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('owner.booking_requests'))

    success, msg = update_booking_status(booking_id, 'APPROVED', session['user_id'])
    if success:
        flash(f"Booking {booking.booking_reference} approved! Driver can now check in.", 'success')
    else:
        flash(msg, 'danger')

    return redirect(url_for('owner.booking_requests'))


@owner_bp.route('/bookings/<int:booking_id>/reject', methods=['POST'])
@login_required
@approved_owner_required
def reject_booking(booking_id):
    """Rejects a pending booking request."""
    booking = Booking.query.get_or_404(booking_id)
    if booking.parking_space.owner_id != session['user_id']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('owner.booking_requests'))

    reason = request.form.get('reason', 'Space unavailable for requested hours')
    success, msg = update_booking_status(booking_id, 'REJECTED', session['user_id'], rejection_reason=reason)
    
    if success:
        flash(f"Booking {booking.booking_reference} rejected.", 'info')
    else:
        flash(msg, 'danger')

    return redirect(url_for('owner.booking_requests'))


@owner_bp.route('/bookings/<int:booking_id>/release-no-show', methods=['POST'])
@login_required
@approved_owner_required
def release_no_show(booking_id):
    """Allows a property owner to manually release a bay if the driver failed to show within 30 minutes."""
    booking = Booking.query.get_or_404(booking_id)
    if booking.parking_space.owner_id != session['user_id'] and session.get('role') != 'ADMIN':
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('owner.booking_requests'))

    if booking.status not in ['PENDING', 'APPROVED'] or booking.check_in_time is not None:
        flash(f"Cannot release bay: Booking is currently {booking.status}.", 'warning')
        return redirect(url_for('owner.booking_requests'))

    success, msg = update_booking_status(
        booking_id,
        'CANCELLED',
        session['user_id'],
        rejection_reason="Host released bay due to driver no-show past 30-minute grace window."
    )
    if success:
        flash(f"Bay released! Booking {booking.booking_reference} has been cancelled and the slot is now open for new drivers.", 'success')
    else:
        flash(msg, 'danger')

    return redirect(url_for('owner.booking_requests'))


@owner_bp.route('/scanner', methods=['GET', 'POST'])
@login_required
@approved_owner_required
def scanner():
    """QR Code Scanner and manual token check-in/check-out terminal."""
    if request.method == 'POST':
        token = request.form.get('qr_token', '').strip()
        action_type = request.form.get('action_type', 'CHECK_IN') # CHECK_IN or CHECK_OUT

        if not token:
            flash('Please provide or scan a valid booking QR token.', 'warning')
            return render_template('owner/scanner.html')

        if action_type == 'CHECK_IN':
            success, result_or_err = process_qr_check_in(token, session['user_id'])
            if success:
                flash(f"Check-In Successful! Vehicle: {result_or_err.vehicle_plate} (Booking Ref: {result_or_err.booking_reference})", 'success')
            else:
                flash(f"Check-In Failed: {result_or_err}", 'danger')
        else: # CHECK_OUT
            success, result_or_err = process_qr_check_out(token, session['user_id'])
            if success:
                flash(f"Check-Out Complete! Total fee: ₹{result_or_err.total_price} (Booking Ref: {result_or_err.booking_reference})", 'success')
            else:
                flash(f"Check-Out Failed: {result_or_err}", 'danger')

        return redirect(url_for('owner.scanner'))

    return render_template('owner/scanner.html')


@owner_bp.route('/revenue')
@login_required
@approved_owner_required
def revenue():
    """Dedicated Owner Revenue & Utilization Analytics Dashboard."""
    owner_id = session['user_id']
    analytics = get_owner_revenue_analytics(owner_id)
    return render_template('owner/revenue.html', analytics=analytics)


@owner_bp.route('/spaces/<int:space_id>/print-sign')
@login_required
def print_space_sign(space_id):
    """
    Renders high-resolution printable Wall Signboard & Gate QR Sticker for the space.
    Homeowners can print this directly to mount on their garage/gate wall for driver self-service.
    """
    space = db.session.get(ParkingSpace, space_id)
    if not space:
        abort(404)
    # Check permissions: owner or admin
    if space.owner_id != session['user_id'] and session.get('role') != 'ADMIN':
        flash('Unauthorized to access sign for this space.', 'danger')
        return redirect(url_for('owner.manage_spaces'))

    scan_url = url_for('driver.space_scan', space_id=space.id, _external=True)
    qr_image = generate_space_qr_base64(space.id, scan_url=scan_url)

    return render_template('owner/space_sign.html', space=space, qr_image=qr_image, scan_url=scan_url)

