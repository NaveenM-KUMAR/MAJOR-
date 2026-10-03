import math

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees).
    Returns distance in kilometers (km).
    """
    try:
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
        
        # Earth radius in kilometers
        R = 6371.0
        
        # Convert decimal degrees to radians
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = math.sin(dlat / 2.0) ** 2 + \
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
            math.sin(dlon / 2.0) ** 2
            
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        return round(distance, 2)
    except (ValueError, TypeError):
        return 9999.0

def filter_and_rank_by_distance(parking_spaces, target_lat, target_lng, max_radius_km=25.0):
    """
    Ranks a list of parking spaces by proximity to (target_lat, target_lng).
    Attaches a 'distance_km' attribute to each space item.
    """
    ranked_spaces = []
    
    for space in parking_spaces:
        dist = haversine_distance(target_lat, target_lng, space.latitude, space.longitude)
        if max_radius_km is None or dist <= max_radius_km:
            # Attach distance property dynamically
            space.distance_km = dist
            ranked_spaces.append((dist, space))
            
    # Sort by distance ascending
    ranked_spaces.sort(key=lambda x: x[0])
    return [space for _, space in ranked_spaces]
