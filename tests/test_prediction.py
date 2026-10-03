from datetime import datetime, time, timedelta
from app.services.prediction_service import predict_parking_availability

def test_smart_prediction_baseline(app, test_data):
    with app.app_context():
        # Space has 0 active bookings
        pred = predict_parking_availability(test_data['space_id'], target_time=time(14, 0))
        assert pred is not None
        assert pred['category'] in ['LIKELY AVAILABLE', 'OCCUPIED SOON', 'HIGH DEMAND AREA']
        assert 'predicted_occupancy_pct' in pred
        assert 'explanation' in pred
        assert 'score' in pred
