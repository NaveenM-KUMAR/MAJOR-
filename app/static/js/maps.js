/**
 * Leaflet.js Interactive Map Initializer for Community Parking System
 * Featuring Real-Time GPS Tracking, OSRM Road Routing, and Direct Turn-by-Turn Navigation.
 */

window.currentUserCoords = null;
window.activeRoutePolyline = null;
window.activeRouteSummaryControl = null;

function createParkingMarkerIcon(space) {
    const priceText = space && space.price_per_hour ? `₹${Math.round(space.price_per_hour)}/hr` : 'P';
    return L.divIcon({
        className: 'custom-parking-marker',
        html: `
            <div class="parking-badge-pin" title="${space ? space.title : 'Parking Space'}">
                <div class="parking-badge-bubble">
                    <span class="parking-badge-p">P</span>
                    <span>${priceText}</span>
                </div>
                <div class="parking-badge-arrow"></div>
                <div class="parking-badge-shadow"></div>
            </div>
        `,
        iconSize: [84, 44],
        iconAnchor: [42, 44],
        popupAnchor: [0, -44]
    });
}

function createUserMarkerIcon() {
    return L.divIcon({
        className: 'custom-user-marker',
        html: `
            <div class="user-gps-pulse" title="Your GPS Location">
                <div class="pulse-ring"></div>
                <div class="dot"></div>
            </div>
        `,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
        popupAnchor: [0, -14]
    });
}

/**
 * Triggers Google Maps Native Turn-by-Turn GPS Navigation
 * Explicitly provides origin coordinates to prevent random/ISP misdirection,
 * and sets dir_action=navigate to immediately start real-time tracking.
 */
function createEmergencyMarkerIcon(space) {
    const priceText = space && space.price_per_hour ? `₹${Math.round(space.price_per_hour)}/hr` : 'P';
    return L.divIcon({
        className: 'custom-parking-marker',
        html: `
            <div class="parking-badge-pin" title="${space ? space.title : 'Emergency Parking'}">
                <div class="parking-badge-bubble" style="background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); border: 2px solid #ffffff; box-shadow: 0 4px 14px rgba(220, 38, 38, 0.5);">
                    <span class="parking-badge-p" style="color: #dc2626; font-weight: 900;">P</span>
                    <span>${priceText}</span>
                </div>
                <div class="parking-badge-arrow" style="border-top-color: #b91c1c;"></div>
                <div class="parking-badge-shadow"></div>
            </div>
        `,
        iconSize: [84, 44],
        iconAnchor: [42, 44],
        popupAnchor: [0, -44]
    });
}

/**
 * In-App Road GPS Navigation using Leaflet & OSRM
 * Prioritizes drawing real road route directly on the active Leaflet map.
 * DOES NOT redirect out to external services when an in-app map is present.
 */
function startTurnByTurnNavigation(destLat, destLng, spaceTitle, spaceId) {
    // If an emergency map is active on screen, draw route directly in Leaflet
    if (window.activeEmergencyMap) {
        if (typeof window.navigateOnMap === 'function') {
            window.navigateOnMap(destLat, destLng, spaceTitle, spaceId);
            return;
        }
    }
    // If search map is active on screen, draw route directly in Leaflet
    if (window.activeSearchMap) {
        if (typeof window.drawRouteToSpace === 'function') {
            window.drawRouteToSpace(destLat, destLng, spaceTitle);
            return;
        }
    }
    // If details map is active, draw route directly in Leaflet
    if (window.activeDetailsMap) {
        const origin = window.currentUserCoords || { lat: 12.9716, lng: 77.5946 };
        drawDrivingRoute(window.activeDetailsMap, origin.lat, origin.lng, destLat, destLng, spaceTitle, spaceId);
        return;
    }

    // Fallback if no Leaflet map is in the DOM
    const openNavUrl = (originLat, originLng) => {
        let navUrl;
        if (originLat && originLng) {
            navUrl = `https://www.google.com/maps/dir/?api=1&origin=${originLat},${originLng}&destination=${destLat},${destLng}&travelmode=driving&dir_action=navigate`;
        } else {
            navUrl = `https://www.google.com/maps/dir/?api=1&destination=${destLat},${destLng}&travelmode=driving&dir_action=navigate`;
        }
        window.open(navUrl, '_blank');
    };

    if (window.currentUserCoords && window.currentUserCoords.lat && window.currentUserCoords.lng) {
        openNavUrl(window.currentUserCoords.lat, window.currentUserCoords.lng);
        return;
    }
    openNavUrl(null, null);
}

/**
 * Draws Real-World Driving Road Polyline using Open-Standard OSRM API directly on Leaflet
 */
function drawDrivingRoute(map, startLat, startLng, endLat, endLng, spaceTitle, spaceId) {
    if (!map) return;

    // Clear existing route if any
    clearActiveRoute();

    const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${startLng},${startLat};${endLng},${endLat}?overview=full&geometries=geojson&steps=true`;

    fetch(osrmUrl)
        .then(res => res.json())
        .then(data => {
            if (data.routes && data.routes.length > 0) {
                const route = data.routes[0];
                const coordinates = route.geometry.coordinates.map(coord => [coord[1], coord[0]]);
                const distanceKm = (route.distance / 1000).toFixed(1);
                const durationMin = Math.max(1, Math.round(route.duration / 60));

                // Outer glowing road casing
                const outerGlow = L.polyline(coordinates, {
                    color: '#1d4ed8',
                    weight: 9,
                    opacity: 0.35,
                    lineJoin: 'round',
                    lineCap: 'round'
                }).addTo(map);

                // Inner solid driving navigation line
                const innerLine = L.polyline(coordinates, {
                    color: '#2563eb',
                    weight: 5,
                    opacity: 0.95,
                    lineJoin: 'round',
                    lineCap: 'round'
                }).addTo(map);

                window.activeRouteLayers = [outerGlow, innerLine];
                window.activeRoutePolyline = innerLine;
                map.fitBounds(innerLine.getBounds(), { padding: [50, 50] });

                // Add in-app Navigation Route HUD on Leaflet map
                const infoCard = L.control({ position: 'topright' });
                infoCard.onAdd = function() {
                    const div = L.DomUtil.create('div', 'p-3 bg-white rounded-3 shadow-lg border');
                    div.style.maxWidth = '280px';
                    div.style.zIndex = '1000';
                    div.innerHTML = `
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <span class="badge bg-primary px-2 py-1"><i class="bi bi-compass-fill me-1"></i>In-App Live Route</span>
                            <button type="button" class="btn-close btn-sm" style="font-size:0.65rem;" onclick="clearActiveRoute()"></button>
                        </div>
                        <div class="fw-bold text-dark small mb-1">${spaceTitle || 'Destination Parking Spot'}</div>
                        <div class="d-flex justify-content-between text-muted small mb-3 p-2 bg-light rounded border">
                            <span><i class="bi bi-speedometer2 text-danger me-1"></i><strong>${distanceKm} km</strong></span>
                            <span><i class="bi bi-clock-history text-primary me-1"></i><strong>~${durationMin} mins</strong></span>
                        </div>
                        ${spaceId ? `
                            <a href="/driver/book/${spaceId}?emergency=1" class="btn btn-danger btn-sm w-100 py-2 rounded-pill fw-bold shadow-sm mb-2">
                                <i class="bi bi-lightning-charge-fill me-1"></i> Fast-Track Reserve Spot
                            </a>
                        ` : ''}
                        <button type="button" class="btn btn-outline-secondary btn-sm w-100 py-1 rounded-pill" onclick="clearActiveRoute()">
                            <i class="bi bi-x-circle me-1"></i> Clear Navigation
                        </button>
                    `;
                    return div;
                };
                infoCard.addTo(map);
                window.activeRouteSummaryControl = infoCard;
            }
        })
        .catch(err => {
            console.warn("OSRM Route fetch error (fallback to straight line):", err);
            const straightLine = L.polyline([[startLat, startLng], [endLat, endLng]], {
                color: '#2563eb',
                dashArray: '6, 8',
                weight: 4
            }).addTo(map);
            window.activeRouteLayers = [straightLine];
            window.activeRoutePolyline = straightLine;
            map.fitBounds(straightLine.getBounds(), { padding: [40, 40] });
        });
}

function clearActiveRoute() {
    const map = window.activeEmergencyMap || window.activeSearchMap || window.activeDetailsMap;
    if (window.activeRouteLayers && map) {
        window.activeRouteLayers.forEach(layer => map.removeLayer(layer));
        window.activeRouteLayers = null;
    }
    if (window.activeRoutePolyline && map) {
        map.removeLayer(window.activeRoutePolyline);
        window.activeRoutePolyline = null;
    }
    if (window.activeRouteSummaryControl && map) {
        map.removeControl(window.activeRouteSummaryControl);
        window.activeRouteSummaryControl = null;
    }
}

function initSearchMap(mapElementId, spaces, userLat = 12.9716, userLng = 77.5946) {
    const mapContainer = document.getElementById(mapElementId);
    if (!mapContainer) return;

    window.currentUserCoords = { lat: userLat, lng: userLng };

    const map = L.map(mapElementId).setView([userLat, userLng], 13);
    window.activeSearchMap = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    // Add user marker with animated GPS radar pulse
    let userMarker = null;
    if (userLat && userLng) {
        userMarker = L.marker([userLat, userLng], { icon: createUserMarkerIcon() }).addTo(map)
            .bindPopup("<strong class='text-primary'><i class='bi bi-geo-alt-fill me-1'></i>You Are Here</strong>").openPopup();
    }

    // Silently attempt live high-accuracy browser GPS to refine origin coordinate
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const liveLat = pos.coords.latitude;
                const liveLng = pos.coords.longitude;
                window.currentUserCoords = { lat: liveLat, lng: liveLng };
                if (userMarker) {
                    userMarker.setLatLng([liveLat, liveLng]);
                }
            },
            () => {},
            { enableHighAccuracy: true, timeout: 4000 }
        );
    }

    const bounds = [];
    if (userLat && userLng) {
        bounds.push([userLat, userLng]);
    }

    window.parkingMarkers = {};

    // Add Distinct Emerald Green Parking Space Pins
    if (Array.isArray(spaces)) {
        spaces.forEach(space => {
            if (space.latitude && space.longitude) {
                const lat = parseFloat(space.latitude);
                const lng = parseFloat(space.longitude);
                if (!isNaN(lat) && !isNaN(lng)) {
                    const marker = L.marker([lat, lng], { icon: createParkingMarkerIcon(space) }).addTo(map);
                    bounds.push([lat, lng]);
                    window.parkingMarkers[space.id] = marker;

                    const safeTitle = (space.title || '').replace(/'/g, "\\'");
                    const popupContent = `
                        <div style="min-width: 220px;">
                            <div class="badge bg-success-subtle text-success border border-success mb-1" style="font-size:0.7rem;">
                                <i class="bi bi-shield-check me-1"></i>Verified Spot
                            </div>
                            <h6 style="margin-bottom: 4px; font-weight: 700; color: #0f172a;">${space.title}</h6>
                            <p style="margin-bottom: 6px; font-size: 0.85rem; color: #64748b;">
                                <i class="bi bi-geo-alt-fill text-danger me-1"></i>${space.locality}
                            </p>
                            <div style="font-size: 0.95rem; font-weight: 800; color: #059669; margin-bottom: 8px;">
                                ₹${space.price_per_hour}/hr
                            </div>
                            <div class="d-flex flex-column gap-1">
                                <div class="d-flex gap-1">
                                    <button type="button" onclick="startTurnByTurnNavigation(${lat}, ${lng}, '${safeTitle}')" class="btn btn-success btn-sm text-white flex-grow-1" style="padding: 4px 8px; font-size: 0.8rem; font-weight: 700;" title="Start Real-Time GPS Tracking">
                                        <i class="bi bi-cursor-fill me-1"></i> Start Nav
                                    </button>
                                    <button type="button" onclick="drawRouteToSpace(${lat}, ${lng}, '${safeTitle}')" class="btn btn-outline-primary btn-sm" style="padding: 4px 8px; font-size: 0.8rem;" title="Show Route on Map">
                                        <i class="bi bi-sign-turn-right-fill"></i> Route
                                    </button>
                                </div>
                                <a href="/driver/parking/${space.id}" class="btn btn-outline-secondary btn-sm" style="padding: 3px 8px; font-size: 0.78rem;">
                                    View Details & Book
                                </a>
                            </div>
                        </div>
                    `;
                    marker.bindPopup(popupContent);
                }
            }
        });
    }

    window.drawRouteToSpace = function(destLat, destLng, spaceTitle) {
        if (window.currentUserCoords) {
            drawDrivingRoute(map, window.currentUserCoords.lat, window.currentUserCoords.lng, destLat, destLng, spaceTitle);
        } else {
            startTurnByTurnNavigation(destLat, destLng, spaceTitle);
        }
    };

    window.focusSpaceMarker = function(spaceId) {
        if (window.parkingMarkers && window.parkingMarkers[spaceId] && window.activeSearchMap) {
            const marker = window.parkingMarkers[spaceId];
            window.activeSearchMap.setView(marker.getLatLng(), 16);
            marker.openPopup();
            const mapEl = document.getElementById('searchMap');
            if (mapEl && window.innerWidth < 992) {
                mapEl.scrollIntoView({ behavior: 'smooth' });
            }
        }
    };

    // Add Floating Map Legend Control
    const legend = L.control({ position: 'bottomleft' });
    legend.onAdd = function() {
        const div = L.DomUtil.create('div', 'map-legend-card');
        div.innerHTML = `
            <div class="d-flex align-items-center gap-2 mb-1">
                <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background:#2563eb; border:2px solid #fff; box-shadow:0 0 4px rgba(0,0,0,0.3);"></span>
                <span class="text-dark small fw-bold">Your Location</span>
            </div>
            <div class="d-flex align-items-center gap-2">
                <span style="display:inline-flex; align-items:center; justify-content:center; width:16px; height:16px; border-radius:50%; background:#10b981; color:#fff; font-size:10px; font-weight:900;">P</span>
                <span class="text-dark small fw-bold">Available Parking (P)</span>
            </div>
        `;
        return div;
    };
    legend.addTo(map);

    // Automatically zoom and center map to show all markers
    if (bounds.length > 1) {
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
    } else if (bounds.length === 1) {
        map.setView(bounds[0], 14);
    }
}

function initDetailsMap(mapElementId, lat, lng, title, address) {
    const mapContainer = document.getElementById(mapElementId);
    if (!mapContainer || !lat || !lng) return;

    const map = L.map(mapElementId).setView([lat, lng], 15);
    window.activeDetailsMap = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    const marker = L.marker([lat, lng], { icon: createParkingMarkerIcon({ title: title, price_per_hour: null }) }).addTo(map);
    const safeTitle = (title || '').replace(/'/g, "\\'");
    marker.bindPopup(`
        <strong>${title}</strong><br>
        <small class="text-muted">${address}</small><br>
        <button type="button" onclick="startTurnByTurnNavigation(${lat}, ${lng}, '${safeTitle}')" class="btn btn-success btn-sm text-white w-100 mt-2 py-1 fw-bold">
            <i class="bi bi-cursor-fill me-1"></i> Start Real-Time GPS Tracking
        </button>
    `).openPopup();

    // Check user location to plot route to space
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const userLat = pos.coords.latitude;
                const userLng = pos.coords.longitude;
                window.currentUserCoords = { lat: userLat, lng: userLng };
                L.marker([userLat, userLng], { icon: createUserMarkerIcon() }).addTo(map)
                    .bindPopup("<strong class='text-primary'><i class='bi bi-geo-alt-fill me-1'></i>You Are Here</strong>");
                drawDrivingRoute(map, userLat, userLng, lat, lng, title);
            },
            () => {},
            { enableHighAccuracy: true, timeout: 5000 }
        );
    }
}

/**
 * Initializes the Emergency Parking Leaflet Map
 * Renders user GPS marker, Google Maps-style parking pins, and in-app navigation routes.
 * DOES NOT redirect out of the application to Google Maps.
 */
function initEmergencyMap(mapElementId, spaces, userLat = 12.9716, userLng = 77.5946) {
    const mapContainer = document.getElementById(mapElementId);
    if (!mapContainer) return;

    window.currentUserCoords = { lat: userLat, lng: userLng };

    const map = L.map(mapElementId).setView([userLat, userLng], 14);
    window.activeEmergencyMap = map;
    window.activeSearchMap = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors | Community Parking GPS',
        maxZoom: 19
    }).addTo(map);

    // User GPS location marker with radar pulse
    let userMarker = null;
    if (userLat && userLng) {
        userMarker = L.marker([userLat, userLng], { icon: createUserMarkerIcon() }).addTo(map)
            .bindPopup("<strong class='text-primary'><i class='bi bi-crosshair me-1'></i>You Are Here</strong>").openPopup();
    }

    // Attempt live browser GPS refinement
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const liveLat = pos.coords.latitude;
                const liveLng = pos.coords.longitude;
                window.currentUserCoords = { lat: liveLat, lng: liveLng };
                if (userMarker) {
                    userMarker.setLatLng([liveLat, liveLng]);
                }
            },
            () => {},
            { enableHighAccuracy: true, timeout: 5000 }
        );
    }

    const bounds = [];
    if (userLat && userLng) {
        bounds.push([userLat, userLng]);
    }

    window.emergencyMarkers = {};

    // Plot Emergency Parking Pins on Leaflet Map
    if (Array.isArray(spaces)) {
        spaces.forEach(space => {
            if (space.latitude && space.longitude) {
                const lat = parseFloat(space.latitude);
                const lng = parseFloat(space.longitude);
                if (!isNaN(lat) && !isNaN(lng)) {
                    const marker = L.marker([lat, lng], { icon: createEmergencyMarkerIcon(space) }).addTo(map);
                    bounds.push([lat, lng]);
                    window.emergencyMarkers[space.id] = marker;

                    const safeTitle = (space.title || '').replace(/'/g, "\\'");
                    const distDisplay = space.distance_km !== undefined ? `${space.distance_km} km away` : 'Nearby';
                    const popupContent = `
                        <div style="min-width: 230px; font-family: inherit;">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <span class="badge bg-danger-subtle text-danger border border-danger fw-bold" style="font-size:0.7rem;">
                                    <i class="bi bi-lightning-charge-fill me-1"></i>EMERGENCY BAY
                                </span>
                                <span class="badge bg-light text-dark border small">${distDisplay}</span>
                            </div>
                            <h6 style="margin: 4px 0; font-weight: 700; color: #0f172a;">${space.title}</h6>
                            <p style="margin-bottom: 6px; font-size: 0.82rem; color: #64748b;">
                                <i class="bi bi-geo-alt-fill text-danger me-1"></i>${space.locality || space.address}
                            </p>
                            <div style="font-size: 0.95rem; font-weight: 800; color: #dc2626; margin-bottom: 8px;">
                                ₹${space.price_per_hour}/hr &bull; <span class="text-success" style="font-size:0.8rem; font-weight:700;">${space.total_slots} slots open</span>
                            </div>
                            <div class="d-flex gap-1">
                                <button type="button" onclick="navigateOnEmergencyMap(${lat}, ${lng}, '${safeTitle}', ${space.id})" class="btn btn-danger btn-sm text-white flex-grow-1 fw-bold" style="padding: 5px 8px; font-size: 0.82rem;">
                                    <i class="bi bi-sign-turn-right-fill me-1"></i> Navigate on Map
                                </button>
                                <a href="/driver/book/${space.id}?emergency=1" class="btn btn-outline-dark btn-sm fw-semibold" style="padding: 5px 8px; font-size: 0.82rem;">
                                    Reserve
                                </a>
                            </div>
                        </div>
                    `;
                    marker.bindPopup(popupContent);
                }
            }
        });
    }

    // In-app navigation function: draws driving polyline and opens HUD directly on Leaflet
    window.navigateOnEmergencyMap = function(destLat, destLng, spaceTitle, spaceId) {
        const origin = window.currentUserCoords || { lat: userLat, lng: userLng };
        drawDrivingRoute(map, origin.lat, origin.lng, destLat, destLng, spaceTitle, spaceId);

        // Pan to fit the route on mobile and desktop
        const mapEl = document.getElementById(mapElementId);
        if (mapEl && window.innerWidth < 992) {
            mapEl.scrollIntoView({ behavior: 'smooth' });
        }
    };

    window.focusEmergencyMarker = function(spaceId) {
        if (window.emergencyMarkers && window.emergencyMarkers[spaceId]) {
            const marker = window.emergencyMarkers[spaceId];
            map.setView(marker.getLatLng(), 16);
            marker.openPopup();
            const mapEl = document.getElementById(mapElementId);
            if (mapEl && window.innerWidth < 992) {
                mapEl.scrollIntoView({ behavior: 'smooth' });
            }
        }
    };

    // Add Recenter Control
    const recenterCtrl = L.control({ position: 'topleft' });
    recenterCtrl.onAdd = function() {
        const btn = L.DomUtil.create('button', 'btn btn-light btn-sm shadow-sm border fw-bold');
        btn.innerHTML = '<i class="bi bi-crosshair2 text-danger"></i> My Location';
        btn.title = 'Recenter on My Location';
        btn.style.marginTop = '10px';
        btn.onclick = function(e) {
            e.preventDefault();
            const coords = window.currentUserCoords || { lat: userLat, lng: userLng };
            map.setView([coords.lat, coords.lng], 15);
            if (userMarker) userMarker.openPopup();
        };
        return btn;
    };
    recenterCtrl.addTo(map);

    // Add Map Legend
    const legend = L.control({ position: 'bottomleft' });
    legend.onAdd = function() {
        const div = L.DomUtil.create('div', 'map-legend-card');
        div.innerHTML = `
            <div class="d-flex align-items-center gap-2 mb-1">
                <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background:#2563eb; border:2px solid #fff; box-shadow:0 0 4px rgba(0,0,0,0.3);"></span>
                <span class="text-dark small fw-bold">Your Location</span>
            </div>
            <div class="d-flex align-items-center gap-2">
                <span style="display:inline-flex; align-items:center; justify-content:center; width:18px; height:18px; border-radius:50%; background:#dc2626; color:#fff; font-size:10px; font-weight:900;">P</span>
                <span class="text-dark small fw-bold">Emergency Parking Bay</span>
            </div>
        `;
        return div;
    };
    legend.addTo(map);

    // Fit map bounds to show all emergency markers
    if (bounds.length > 1) {
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
    } else if (bounds.length === 1) {
        map.setView(bounds[0], 14);
    }
}
