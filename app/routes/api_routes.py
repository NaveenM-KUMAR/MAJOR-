from datetime import datetime
from flask import Blueprint, request, jsonify, session
from app.models.parking import ParkingSpace
from app.models.booking import Booking
from app.utils.distance import filter_and_rank_by_distance
from app.services.booking_service import check_slot_availability, process_qr_check_in, process_qr_check_out, auto_cancel_no_shows
from app.services.prediction_service import predict_parking_availability
from app.services.analytics_service import get_owner_revenue_analytics, get_admin_system_analytics

api_bp = Blueprint('api', __name__)

@api_bp.route('/parking/nearby')
def api_nearby_parking():
    """Returns ranked nearby parking spaces in JSON format for map rendering."""
    auto_cancel_no_shows()
    lat = request.args.get('lat', type=float, default=12.9716)
    lng = request.args.get('lng', type=float, default=77.5946)
    radius = request.args.get('radius', type=float, default=25.0)

    spaces = ParkingSpace.query.filter_by(is_active=True, approval_status='APPROVED').all()
    ranked_spaces = filter_and_rank_by_distance(spaces, lat, lng, max_radius_km=radius)

    results = []
    for s in ranked_spaces:
        item = s.to_dict()
        item['distance_km'] = getattr(s, 'distance_km', None)
        item['prediction'] = predict_parking_availability(s.id)
        results.append(item)

    return jsonify({'success': True, 'count': len(results), 'spaces': results})


@api_bp.route('/parking/<int:space_id>/availability')
def api_check_availability(space_id):
    """
    Live asynchronous availability check for a given date/time range.
    Called via AJAX on the booking form as user adjusts hours.
    """
    date_str = request.args.get('date')
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')

    if not date_str or not start_time_str or not end_time_str:
        return jsonify({'success': False, 'message': 'Missing date or time parameters.'}), 400

    try:
        b_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        s_time = datetime.strptime(start_time_str, '%H:%M').time()
        e_time = datetime.strptime(end_time_str, '%H:%M').time()
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date/time format.'}), 400

    if s_time >= e_time:
        return jsonify({'success': False, 'message': 'End time must be after start time.'}), 400

    is_avail, msg = check_slot_availability(space_id, b_date, s_time, e_time)
    prediction = predict_parking_availability(space_id, b_date, s_time)

    return jsonify({
        'success': True,
        'available': is_avail,
        'message': msg,
        'prediction': prediction
    })


@api_bp.route('/parking/<int:space_id>/predict')
def api_predict_availability(space_id):
    """Returns explainable Smart Availability Prediction."""
    prediction = predict_parking_availability(space_id)
    response_data = {'success': True, 'prediction': prediction}
    if isinstance(prediction, dict):
        response_data.update(prediction)
    return jsonify(response_data)


@api_bp.route('/scanner/verify', methods=['POST'])
def api_verify_qr():
    """Asynchronous endpoint for QR token scanning and verification."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = request.get_json() or {}
    token = data.get('qr_token', '').strip()
    action_type = data.get('action_type', 'CHECK_IN')

    if not token:
        return jsonify({'success': False, 'message': 'Token missing'}), 400

    if action_type == 'CHECK_IN':
        success, res = process_qr_check_in(token, session['user_id'])
    else:
        success, res = process_qr_check_out(token, session['user_id'])

    if success:
        return jsonify({
            'success': True,
            'message': f"{'Check-In' if action_type == 'CHECK_IN' else 'Check-Out'} successful!",
            'booking': res.to_dict()
        })
    else:
        return jsonify({'success': False, 'message': str(res)}), 400


@api_bp.route('/analytics/owner')
def api_owner_analytics():
    """JSON analytics for dynamic Chart.js rendering."""
    if 'user_id' not in session or session.get('role') != 'OWNER':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = get_owner_revenue_analytics(session['user_id'])
    return jsonify({'success': True, 'analytics': data})
