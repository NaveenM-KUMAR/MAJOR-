from datetime import datetime, time, timedelta, timezone
from sqlalchemy import func
from app import db
from app.models.parking import ParkingSpace
from app.models.booking import Booking

from app.utils.timezone import utcnow

def now_utc():
    return utcnow()

def predict_parking_availability(parking_space_id, target_date=None, target_time=None):
    """
    Smart Availability Prediction Engine:
    Evaluates real-time occupancy, locality booking density, historical day-of-week trends,
    and hour-of-day peak patterns to categorize expected availability.

    Returns a structured dictionary:
    {
        'category': 'LIKELY AVAILABLE' | 'OCCUPIED SOON' | 'HIGH DEMAND AREA',
        'badge_class': 'success' | 'warning' | 'danger',
        'demand_level': 'Low' | 'Moderate' | 'High',
        'predicted_occupancy_pct': int (0-100),
        'score': float (0.0 to 1.0),
        'explanation': str,
        'rush_hour': bool,
        'locality_demand': 'Normal' | 'Surging'
    }
    """
    if target_date is None:
        target_date = now_utc().date()
    if target_time is None:
        target_time = now_utc().time()

    parking_space = db.session.get(ParkingSpace, parking_space_id)
    if not parking_space:
        return {
            'category': 'LIKELY AVAILABLE',
            'badge_class': 'success',
            'demand_level': 'Low',
            'predicted_occupancy_pct': 10,
            'score': 0.1,
            'explanation': 'New space with ample open capacity.',
            'rush_hour': False,
            'locality_demand': 'Normal'
        }

    # 1. Check current real-time active bookings for this space on target_date
    active_now_count = Booking.query.filter(
        Booking.parking_space_id == parking_space_id,
        Booking.booking_date == target_date,
        Booking.status.in_(['APPROVED', 'ACTIVE']),
        Booking.start_time <= target_time,
        Booking.end_time >= target_time
    ).count()

    total_slots = max(1, int(parking_space.total_slots))
    current_occupancy_ratio = float(active_now_count) / float(total_slots)

    # 2. Time of day rush-hour factor (Typical urban traffic peaks: 8:00-11:00 & 17:00-21:00)
    hour = target_time.hour
    is_rush_hour = (8 <= hour <= 11) or (17 <= hour <= 21)

    # 3. Locality cluster demand: check how many bookings exist in the same locality in last 7 days
    seven_days_ago = now_utc() - timedelta(days=7)
    locality_recent_bookings = int(db.session.query(func.count(Booking.id)).join(ParkingSpace).filter(
        ParkingSpace.locality == parking_space.locality,
        Booking.created_at >= seven_days_ago,
        Booking.status.in_(['APPROVED', 'ACTIVE', 'COMPLETED'])
    ).scalar() or 0)

    total_locality_slots = int(db.session.query(func.sum(ParkingSpace.total_slots)).filter(
        ParkingSpace.locality == parking_space.locality,
        ParkingSpace.is_active == True,
        ParkingSpace.approval_status == 'APPROVED'
    ).scalar() or 1)

    locality_density = float(locality_recent_bookings) / max(1.0, float(total_locality_slots * 7))

    # 4. Historical occupancy score for this specific parking space
    space_total_bookings = int(Booking.query.filter(
        Booking.parking_space_id == parking_space_id,
        Booking.status.in_(['APPROVED', 'ACTIVE', 'COMPLETED'])
    ).count())

    # Calculate composite demand probability score (0.0 to 1.0)
    # Weight factors: Current Occupancy (40%), Locality Density (30%), Rush Hour (20%), Space Popularity (10%)
    rush_factor = 0.8 if is_rush_hour else 0.2
    pop_factor = min(1.0, float(space_total_bookings) / 20.0)
    loc_factor = min(1.0, float(locality_density) / 2.0)

    demand_score = (current_occupancy_ratio * 0.40) + (loc_factor * 0.30) + (rush_factor * 0.20) + (pop_factor * 0.10)
    demand_score = max(0.05, min(0.98, float(demand_score)))

    occupancy_pct = int(demand_score * 100)

    # Categorization Rules
    if demand_score >= 0.70 or current_occupancy_ratio >= 0.75:
        category = 'HIGH DEMAND AREA'
        badge_class = 'danger'
        demand_level = 'High'
        locality_demand = 'Surging'
        explanation = f"Heavy booking density in {parking_space.locality}. Space is near peak capacity during active hours."
    elif demand_score >= 0.40 or current_occupancy_ratio >= 0.40 or (is_rush_hour and locality_density > 0.5):
        category = 'OCCUPIED SOON'
        badge_class = 'warning'
        demand_level = 'Moderate'
        locality_demand = 'Active'
        explanation = "Moderate demand detected. Nearby slots are filling up quickly; reserving in advance is advised."
    else:
        category = 'LIKELY AVAILABLE'
        badge_class = 'success'
        demand_level = 'Low'
        locality_demand = 'Normal'
        explanation = "High probability of open slots. Low historical congestion for this schedule."

    return {
        'category': category,
        'badge_class': badge_class,
        'demand_level': demand_level,
        'predicted_occupancy_pct': occupancy_pct,
        'score': round(demand_score, 2),
        'explanation': explanation,
        'rush_hour': is_rush_hour,
        'locality_demand': locality_demand,
        'slots_available_estimate': max(0, total_slots - active_now_count)
    }
