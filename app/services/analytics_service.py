from datetime import datetime, timedelta
from app.utils.timezone import utcnow
from sqlalchemy import func, distinct
from app import db
from app.models.user import User
from app.models.parking import ParkingSpace
from app.models.booking import Booking
from app.models.review import Review

def get_owner_revenue_analytics(owner_id):
    """
    Computes accurate revenue, utilization, and booking distribution for a parking owner.
    Only COMPLETED or active verified bookings contribute to revenue.
    """
    # Owner spaces
    spaces = ParkingSpace.query.filter_by(owner_id=owner_id).all()
    space_ids = [s.id for s in spaces]
    
    if not space_ids:
        return {
            'total_revenue': 0.0,
            'completed_bookings': 0,
            'active_bookings': 0,
            'pending_requests': 0,
            'total_spaces': 0,
            'average_order_value': 0.0,
            'utilization_rate': 0.0,
            'daily_revenue_labels': [],
            'daily_revenue_data': [],
            'space_performance': []
        }

    # Gross revenue from completed bookings
    total_rev_val = db.session.query(func.sum(Booking.total_price)).filter(
        Booking.parking_space_id.in_(space_ids),
        Booking.status == 'COMPLETED'
    ).scalar() or 0.0

    completed_count = Booking.query.filter(
        Booking.parking_space_id.in_(space_ids),
        Booking.status == 'COMPLETED'
    ).count()

    active_count = Booking.query.filter(
        Booking.parking_space_id.in_(space_ids),
        Booking.status == 'ACTIVE'
    ).count()

    pending_count = Booking.query.filter(
        Booking.parking_space_id.in_(space_ids),
        Booking.status == 'PENDING'
    ).count()

    avg_val = round(float(total_rev_val) / max(1, completed_count), 2)

    # 7-day revenue trend
    daily_labels = []
    daily_data = []
    today = utcnow().date()
    
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_str = d.strftime('%b %d')
        daily_labels.append(day_str)
        
        day_rev = db.session.query(func.sum(Booking.total_price)).filter(
            Booking.parking_space_id.in_(space_ids),
            Booking.booking_date == d,
            Booking.status == 'COMPLETED'
        ).scalar() or 0.0
        
        daily_data.append(float(day_rev))

    # Space by space performance breakdown
    space_perf = []
    total_capacity = sum(s.total_slots for s in spaces)
    
    for s in spaces:
        s_rev = db.session.query(func.sum(Booking.total_price)).filter(
            Booking.parking_space_id == s.id,
            Booking.status == 'COMPLETED'
        ).scalar() or 0.0
        
        s_bookings = Booking.query.filter(
            Booking.parking_space_id == s.id,
            Booking.status.in_(['APPROVED', 'ACTIVE', 'COMPLETED'])
        ).count()
        
        space_perf.append({
            'id': s.id,
            'title': s.title,
            'locality': s.locality,
            'revenue': float(s_rev),
            'bookings_count': s_bookings,
            'slots': s.total_slots,
            'rating': s.average_rating
        })

    # Overall utilization rate: active + approved / total available slots * 100
    utilization_rate = min(100.0, round((active_count / max(1, total_capacity)) * 100.0, 1))

    return {
        'total_revenue': float(total_rev_val),
        'completed_bookings': completed_count,
        'active_bookings': active_count,
        'pending_requests': pending_count,
        'total_spaces': len(spaces),
        'average_order_value': avg_val,
        'utilization_rate': utilization_rate,
        'daily_revenue_labels': daily_labels,
        'daily_revenue_data': daily_data,
        'space_performance': space_perf
    }


def get_admin_system_analytics():
    """
    Computes global system KPIs, high demand localities, emergency usage, and booking statistics.
    """
    total_users = User.query.filter_by(role='DRIVER').count()
    total_owners = User.query.filter_by(role='OWNER').count()
    pending_owners = User.query.filter_by(role='OWNER', owner_status='PENDING').count()
    approved_owners = User.query.filter_by(role='OWNER', owner_status='APPROVED').count()

    total_spaces = ParkingSpace.query.count()
    active_spaces = ParkingSpace.query.filter_by(is_active=True, approval_status='APPROVED').count()

    total_bookings = Booking.query.count()
    active_bookings = Booking.query.filter_by(status='ACTIVE').count()
    completed_bookings = Booking.query.filter_by(status='COMPLETED').count()
    cancelled_bookings = Booking.query.filter_by(status='CANCELLED').count()
    emergency_bookings = Booking.query.filter_by(is_emergency=True).count()

    total_gross_volume = db.session.query(func.sum(Booking.total_price)).filter(
        Booking.status == 'COMPLETED'
    ).scalar() or 0.0

    # Top high demand areas by booking count
    top_areas = db.session.query(
        ParkingSpace.locality,
        func.count(Booking.id).label('booking_count'),
        func.sum(Booking.total_price).label('area_revenue')
    ).join(Booking).group_by(ParkingSpace.locality).order_by(func.count(Booking.id).desc()).limit(5).all()

    area_labels = [a[0] for a in top_areas]
    area_counts = [a[1] for a in top_areas]

    # Weekly booking status distribution
    status_distribution = {
        'Completed': completed_bookings,
        'Active': active_bookings,
        'Pending': Booking.query.filter_by(status='PENDING').count(),
        'Approved': Booking.query.filter_by(status='APPROVED').count(),
        'Cancelled': cancelled_bookings
    }

    return {
        'total_users': total_users,
        'total_owners': total_owners,
        'pending_owners': pending_owners,
        'approved_owners': approved_owners,
        'total_spaces': total_spaces,
        'active_spaces': active_spaces,
        'total_bookings': total_bookings,
        'active_bookings': active_bookings,
        'completed_bookings': completed_bookings,
        'cancelled_bookings': cancelled_bookings,
        'emergency_bookings': emergency_bookings,
        'total_gross_volume': float(total_gross_volume),
        'top_areas': [{'locality': a[0], 'bookings': a[1], 'revenue': float(a[2] or 0)} for a in top_areas],
        'area_chart_labels': area_labels,
        'area_chart_data': area_counts,
        'status_distribution': status_distribution
    }
