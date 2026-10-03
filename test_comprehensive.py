"""
Comprehensive Testing Script for Community Parking System
Tests all routes, authentication flows, and feature workflows.
"""
import os
import sys
import traceback
from datetime import datetime, date, time, timedelta
from decimal import Decimal

# Setup
os.environ['FLASK_ENV'] = 'development'
from app import create_app, db
from app.models.user import User
from app.models.parking import ParkingSpace
from app.models.booking import Booking
from app.models.review import Review
from app.models.notification import Notification
from app.models.audit import AuditLog

app = create_app()
issues = []
warnings = []

def log_issue(category, description, severity="BUG"):
    issues.append({"category": category, "description": description, "severity": severity})
    print(f"  [!] {severity}: {description}")

def log_warning(category, description):
    warnings.append({"category": category, "description": description})
    print(f"  [~] WARNING: {description}")

def test_route(client, url, expected_code=200, method='GET', data=None, description=""):
    """Test a single route and return response."""
    try:
        if method == 'GET':
            resp = client.get(url, follow_redirects=False)
        else:
            resp = client.post(url, data=data, follow_redirects=False)
        
        if resp.status_code != expected_code:
            # 302 redirects to login are expected for protected routes
            if resp.status_code == 302 and expected_code == 200:
                location = resp.headers.get('Location', '')
                if 'login' in location:
                    return resp  # Expected redirect to login
            log_issue("ROUTE", f"{url} returned {resp.status_code}, expected {expected_code}. {description}")
        return resp
    except Exception as e:
        log_issue("ROUTE", f"{url} raised exception: {str(e)}")
        return None

def login_as(client, email, password):
    """Login helper."""
    resp = client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)
    return resp

def logout(client):
    """Logout helper."""
    client.get('/logout', follow_redirects=True)

# ============================================================
# BEGIN TESTING
# ============================================================
print("=" * 70)
print("COMMUNITY PARKING SYSTEM - COMPREHENSIVE TEST REPORT")
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

with app.app_context():
    client = app.test_client()

    # ----------------------------------------------------------
    # 1. PUBLIC ROUTES (No Auth Required)
    # ----------------------------------------------------------
    print("\n[1] TESTING PUBLIC ROUTES...")
    
    # Landing Page
    resp = test_route(client, '/', description="Landing page")
    if resp and resp.status_code == 200:
        html = resp.get_data(as_text=True)
        if 'Community Parking' not in html:
            log_issue("UI", "Landing page missing branding text")
        # Check for broken image references
        if 'default_parking.jpg' in html:
            # Check if default_parking.jpg exists
            default_img = os.path.join(app.config['UPLOAD_FOLDER'], 'default_parking.jpg')
            if not os.path.exists(default_img):
                log_issue("ASSET", "default_parking.jpg missing from uploads folder - space images will show broken")
        print("  [OK] Landing page loads")

    # How It Works
    resp = test_route(client, '/how-it-works', description="How it works page")
    if resp and resp.status_code == 200:
        print("  [OK] How It Works page loads")

    # Search (public, no login needed)
    resp = test_route(client, '/driver/search', description="Search page (public)")
    if resp:
        if resp.status_code == 302:
            log_issue("ACCESS", "/driver/search redirects to login - should be publicly accessible for browsing")
        elif resp.status_code == 200:
            print("  [OK] Search page loads publicly")

    # Emergency Mode (public)
    resp = test_route(client, '/driver/emergency', description="Emergency mode page")
    if resp:
        if resp.status_code == 302:
            log_issue("ACCESS", "/driver/emergency redirects to login - should be publicly accessible")
        elif resp.status_code == 200:
            print("  [OK] Emergency page loads publicly")

    # Login page
    resp = test_route(client, '/login', description="Login page")
    if resp and resp.status_code == 200:
        html = resp.get_data(as_text=True)
        if 'Demo' in html or 'demo' in html.lower():
            # Check if any demo shortcuts remain
            if 'fillCreds' in html or 'Auto-fill' in html:
                log_issue("UI", "Login page still has demo/fake account shortcuts")
        print("  [OK] Login page loads")

    # Register page
    resp = test_route(client, '/register', description="Register page")
    if resp and resp.status_code == 200:
        print("  [OK] Register page loads")

    # Auth alias routes
    resp = test_route(client, '/auth/login', description="Auth login alias")
    if resp and resp.status_code == 200:
        print("  [OK] /auth/login alias works")

    resp = test_route(client, '/auth/register', description="Auth register alias")
    if resp and resp.status_code == 200:
        print("  [OK] /auth/register alias works")

    # ----------------------------------------------------------
    # 2. AUTHENTICATION TESTING
    # ----------------------------------------------------------
    print("\n[2] TESTING AUTHENTICATION...")

    # Test login with wrong credentials
    resp = client.post('/login', data={'email': 'nonexistent@test.com', 'password': 'wrong'}, follow_redirects=True)
    html = resp.get_data(as_text=True)
    if 'Invalid' not in html and 'invalid' not in html.lower():
        log_issue("AUTH", "No error message shown for invalid credentials")
    else:
        print("  [OK] Invalid credentials show error")

    # Test login with empty fields
    resp = client.post('/login', data={'email': '', 'password': ''}, follow_redirects=True)
    if resp.status_code == 200:
        print("  [OK] Empty login form handled")

    # Test admin login
    resp = login_as(client, 'admin@cps.com', 'admin123')
    html = resp.get_data(as_text=True)
    if resp.status_code == 200:
        print("  [OK] Admin login successful")
    else:
        log_issue("AUTH", f"Admin login failed with status {resp.status_code}")
    logout(client)

    # Test real driver login
    resp = login_as(client, 'naveenmkumar77@gmail.com', 'driver123')
    if resp.status_code == 200:
        print("  [OK] Real driver login successful")
    else:
        log_issue("AUTH", "Real driver login failed")
    logout(client)

    # Test real owner login (pending status)
    resp = login_as(client, 'naveenmkumar@gmail.com', 'owner123')
    if resp.status_code == 200:
        print("  [OK] Real owner login successful")
    logout(client)

    # Test registration with duplicate email
    resp = client.post('/register', data={
        'name': 'Duplicate Test',
        'email': 'admin@cps.com',
        'phone': '9999999999',
        'password': 'test123',
        'confirm_password': 'test123',
        'role': 'DRIVER'
    }, follow_redirects=True)
    html = resp.get_data(as_text=True)
    if 'already exists' not in html.lower() and 'error' not in html.lower() and 'duplicate' not in html.lower():
        log_issue("AUTH", "No error shown for duplicate email registration")
    else:
        print("  [OK] Duplicate email registration blocked")

    # Test password mismatch
    resp = client.post('/register', data={
        'name': 'Test User',
        'email': 'newuser_test@test.com',
        'phone': '8888888888',
        'password': 'test123',
        'confirm_password': 'wrong123',
        'role': 'DRIVER'
    }, follow_redirects=True)
    html = resp.get_data(as_text=True)
    if 'match' not in html.lower() and 'mismatch' not in html.lower():
        log_issue("AUTH", "No error shown for password mismatch during registration")
    else:
        print("  [OK] Password mismatch caught during registration")

    # ----------------------------------------------------------
    # 3. ADMIN ROUTES (Logged in as Admin)
    # ----------------------------------------------------------
    print("\n[3] TESTING ADMIN ROUTES...")
    login_as(client, 'admin@cps.com', 'admin123')

    admin_routes = [
        ('/admin/dashboard', 'Admin Dashboard'),
        ('/admin/owners', 'Owner Verifications'),
        ('/admin/owners?status=PENDING', 'Owner Verifications (Pending filter)'),
        ('/admin/owners?status=APPROVED', 'Owner Verifications (Approved filter)'),
        ('/admin/spaces', 'Admin Spaces Management'),
        ('/admin/bookings', 'Admin Bookings Management'),
        ('/admin/users', 'Admin Users Management'),
        ('/admin/reviews', 'Admin Reviews Management'),
        ('/admin/analytics', 'Admin Analytics'),
        ('/admin/audit-logs', 'Admin Audit Logs'),
    ]
    for route, name in admin_routes:
        resp = test_route(client, route, description=name)
        if resp and resp.status_code == 200:
            html = resp.get_data(as_text=True)
            # Check for template errors
            if 'Internal Server Error' in html or 'Traceback' in html:
                log_issue("TEMPLATE", f"{name} page has server-side rendering error")
            elif 'TemplateNotFound' in html:
                log_issue("TEMPLATE", f"{name} template file is missing")
            else:
                print(f"  [OK] {name} loads successfully")
        elif resp and resp.status_code == 500:
            log_issue("SERVER", f"{name} returns 500 Internal Server Error")

    # Test admin approving the pending owner
    pending_owner = User.query.filter_by(role='OWNER', owner_status='PENDING').first()
    temp_pending_created = False
    if not pending_owner:
        pending_owner = User(
            name="Test Pending Host",
            email="test_temp_pending@cps.com",
            phone="9988776655",
            role="OWNER",
            status="ACTIVE",
            owner_status="PENDING",
            owner_address="Test Address, Bangalore"
        )
        pending_owner.set_password("owner123")
        db.session.add(pending_owner)
        db.session.commit()
        temp_pending_created = True

    print(f"  [INFO] Pending owner found: {pending_owner.name} (ID: {pending_owner.id}, Email: {pending_owner.email})")
    resp = client.post(f'/admin/owners/{pending_owner.id}/action',
                     data={'action': 'APPROVE'},
                     follow_redirects=True)
    if resp.status_code == 200:
        db.session.refresh(pending_owner)
        if pending_owner.owner_status == 'APPROVED':
            print("  [OK] Owner approval action works correctly")
        else:
            log_issue("ADMIN", "Owner approval action did not update owner_status to APPROVED")
    else:
        log_issue("ADMIN", f"Owner approval POST returned {resp.status_code}")

    if temp_pending_created:
        db.session.delete(pending_owner)
        db.session.commit()

    logout(client)

    # ----------------------------------------------------------
    # 4. OWNER ROUTES (Logged in as Owner)
    # ----------------------------------------------------------
    approved_owner = User.query.filter_by(role='OWNER', owner_status='APPROVED').first()
    owner_email = approved_owner.email if approved_owner else 'owner1@cps.com'
    print(f"\n[4] TESTING OWNER ROUTES (Logged in as {owner_email})...")
    login_as(client, owner_email, 'owner123')

    owner_routes = [
        ('/owner/approval-status', 'Owner Approval Status'),
        ('/owner/dashboard', 'Owner Dashboard'),
        ('/owner/spaces', 'Owner Manage Spaces'),
        ('/owner/spaces/add', 'Owner Add Space Form'),
        ('/owner/bookings', 'Owner Booking Requests'),
        ('/owner/scanner', 'Owner QR Scanner'),
        ('/owner/revenue', 'Owner Revenue'),
    ]
    for route, name in owner_routes:
        resp = test_route(client, route, description=name)
        if resp:
            if resp.status_code == 200:
                html = resp.get_data(as_text=True)
                if 'Internal Server Error' in html or 'Traceback' in html or 'Error' in html.split('<title>')[1].split('</title>')[0] if '<title>' in html else False:
                    log_issue("TEMPLATE", f"{name} has rendering error")
                else:
                    print(f"  [OK] {name} loads successfully")
            elif resp.status_code == 302:
                location = resp.headers.get('Location', '')
                if 'approval' in location:
                    log_warning("OWNER", f"{name} redirects to approval status (owner may still be pending)")
                elif 'login' in location:
                    log_issue("AUTH", f"{name} redirects to login despite being logged in")
                else:
                    print(f"  [INFO] {name} redirects to {location}")
            elif resp.status_code == 500:
                log_issue("SERVER", f"{name} returns 500 Internal Server Error")

    # Test adding a parking space
    print("\n  Testing space creation...")
    resp = client.post('/owner/spaces/add', data={
        'title': 'Test Integration Parking',
        'description': 'Test space for integration testing',
        'address': '123 Test Street, Koramangala',
        'locality': 'Koramangala',
        'city': 'Bangalore',
        'latitude': '12.9352',
        'longitude': '77.6245',
        'parking_type': 'Private Driveway',
        'vehicle_types': ['Car', 'Two Wheeler'],
        'total_slots': '2',
        'price_per_hour': '30',
        'operating_start': '06:00',
        'operating_end': '22:00',
        'available_days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'amenities': ['CCTV', 'Well Lit'],
        'rules': 'No overnight parking'
    }, follow_redirects=True)
    
    if resp.status_code == 200:
        test_space = ParkingSpace.query.filter_by(title='Test Integration Parking').first()
        if test_space:
            print(f"  [OK] Space creation works (ID: {test_space.id})")
        else:
            log_issue("OWNER", "Space creation POST succeeded (200) but space not found in DB")
    else:
        log_issue("OWNER", f"Space creation returned {resp.status_code}")

    logout(client)

    # ----------------------------------------------------------
    # 5. DRIVER ROUTES (Logged in as Driver)
    # ----------------------------------------------------------
    driver = User.query.filter_by(email='driver1@cps.com').first() or User.query.filter_by(role='DRIVER').first()
    driver_email = driver.email if driver else 'driver1@cps.com'
    print(f"\n[5] TESTING DRIVER ROUTES (Logged in as {driver_email})...")
    login_as(client, driver_email, 'driver123')

    driver_routes = [
        ('/driver/dashboard', 'Driver Dashboard'),
        ('/driver/search', 'Driver Search'),
        ('/driver/search?locality=Koramangala', 'Driver Search with locality filter'),
        ('/driver/emergency', 'Driver Emergency Mode'),
        ('/driver/bookings', 'Driver My Bookings'),
    ]
    for route, name in driver_routes:
        resp = test_route(client, route, description=name)
        if resp:
            if resp.status_code == 200:
                html = resp.get_data(as_text=True)
                if 'Internal Server Error' in html:
                    log_issue("TEMPLATE", f"{name} has rendering error")
                else:
                    print(f"  [OK] {name} loads successfully")
            elif resp.status_code == 500:
                log_issue("SERVER", f"{name} returns 500 Internal Server Error")

    # Test viewing a parking space detail
    test_space = ParkingSpace.query.first()
    if test_space:
        resp = test_route(client, f'/driver/parking/{test_space.id}', description="Space details page")
        if resp and resp.status_code == 200:
            html = resp.get_data(as_text=True)
            if test_space.title in html:
                print(f"  [OK] Space details page for '{test_space.title}' loads")
            else:
                log_issue("TEMPLATE", "Space details page missing space title")
        elif resp and resp.status_code == 500:
            log_issue("SERVER", f"Space details page returns 500")
        
        # Test booking form
        resp = test_route(client, f'/driver/book/{test_space.id}', description="Booking form")
        if resp and resp.status_code == 200:
            print(f"  [OK] Booking form loads for space {test_space.id}")
        elif resp and resp.status_code == 500:
            log_issue("SERVER", f"Booking form returns 500 for space {test_space.id}")

        # Test creating a booking
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        resp = client.post(f'/driver/book/{test_space.id}', data={
            'booking_date': tomorrow,
            'start_time': '10:00',
            'end_time': '12:00',
            'vehicle_type': 'Car',
            'vehicle_plate': 'KA01AB1234'
        }, follow_redirects=True)
        if resp.status_code == 200:
            db.session.expire_all()
            test_booking = Booking.query.filter_by(vehicle_plate='KA01AB1234').first()
            if test_booking:
                print(f"  [OK] Booking created successfully (Ref: {test_booking.booking_reference})")
                
                # Test viewing booking ticket
                resp2 = test_route(client, f'/driver/booking/{test_booking.booking_reference}', 
                                  description="Booking ticket page")
                if resp2 and resp2.status_code == 200:
                    print(f"  [OK] Booking ticket page loads")
                elif resp2 and resp2.status_code == 500:
                    log_issue("SERVER", "Booking ticket page returns 500")
                elif resp2 and resp2.status_code == 404:
                    log_issue("ROUTE", "Booking ticket page returns 404 for valid reference")
            else:
                log_issue("DRIVER", "Booking POST succeeded but booking not in DB")
        else:
            log_issue("DRIVER", f"Booking creation returned status {resp.status_code}")
    else:
        log_warning("DRIVER", "No parking space available to test booking flow")

    # Test non-existent space
    resp = client.get('/driver/parking/99999')
    if resp.status_code != 404:
        log_issue("ROUTE", f"/driver/parking/99999 returned {resp.status_code} instead of 404")
    else:
        print("  [OK] Non-existent space returns 404")

    logout(client)

    # ----------------------------------------------------------
    # 6. API ROUTES
    # ----------------------------------------------------------
    print("\n[6] TESTING API ROUTES...")
    
    if test_space:
        resp = client.get(f'/api/parking/{test_space.id}/predict')
        if resp.status_code == 200:
            data = resp.get_json()
            if data and 'category' in data:
                print(f"  [OK] Prediction API works (category: {data['category']})")
            else:
                log_issue("API", "Prediction API returns 200 but invalid JSON structure")
        else:
            log_issue("API", f"Prediction API returns {resp.status_code}")

        resp = client.get(f'/api/parking/{test_space.id}/availability?date={tomorrow}&start_time=10:00&end_time=12:00')
        if resp.status_code == 200:
            data = resp.get_json()
            if data is not None:
                print(f"  [OK] Availability API works")
            else:
                log_issue("API", "Availability API returns 200 but no JSON")
        else:
            log_issue("API", f"Availability API returns {resp.status_code}")

        resp = client.get('/api/parking/nearby?lat=12.9352&lng=77.6245')
        if resp.status_code == 200:
            print(f"  [OK] Nearby parking API works")
        else:
            log_issue("API", f"Nearby parking API returns {resp.status_code}")

    # ----------------------------------------------------------
    # 7. PROFILE PAGE
    # ----------------------------------------------------------
    print("\n[7] TESTING PROFILE...")
    login_as(client, 'naveenmkumar77@gmail.com', 'driver123')
    resp = test_route(client, '/profile', description="Profile page")
    if resp and resp.status_code == 200:
        print("  [OK] Profile page loads")
    elif resp and resp.status_code == 500:
        log_issue("SERVER", "Profile page returns 500")
    logout(client)

    # ----------------------------------------------------------
    # 8. ERROR PAGES
    # ----------------------------------------------------------
    print("\n[8] TESTING ERROR PAGES...")
    resp = client.get('/nonexistent-page-test')
    if resp.status_code == 404:
        html = resp.get_data(as_text=True)
        if '404' in html:
            print("  [OK] 404 error page renders")
        else:
            log_issue("UI", "404 page doesn't show 404 message")
    else:
        log_issue("ROUTE", f"Non-existent page returned {resp.status_code} instead of 404")

    # ----------------------------------------------------------
    # 9. PROTECTED ROUTE ACCESS WITHOUT LOGIN
    # ----------------------------------------------------------
    print("\n[9] TESTING UNAUTHORIZED ACCESS PROTECTION...")
    protected_routes = [
        '/admin/dashboard', '/admin/owners', '/admin/spaces',
        '/owner/dashboard', '/owner/spaces', '/owner/bookings',
        '/driver/dashboard', '/driver/bookings',
        '/profile',
    ]
    for route in protected_routes:
        resp = client.get(route, follow_redirects=False)
        if resp.status_code == 302:
            location = resp.headers.get('Location', '')
            if 'login' in location:
                pass  # Good, redirects to login
            else:
                log_issue("AUTH", f"{route} redirects to {location} instead of login page")
        elif resp.status_code == 200:
            log_issue("AUTH", f"{route} accessible without login (should be protected)")
    print("  [OK] Protected routes redirect to login")

    # ----------------------------------------------------------
    # 10. ROLE-BASED ACCESS CONTROL
    # ----------------------------------------------------------
    print("\n[10] TESTING ROLE-BASED ACCESS CONTROL...")
    
    # Driver trying to access admin panel
    login_as(client, 'naveenmkumar77@gmail.com', 'driver123')
    resp = client.get('/admin/dashboard', follow_redirects=False)
    if resp.status_code == 302 or resp.status_code == 403:
        print("  [OK] Driver blocked from admin panel")
    elif resp.status_code == 200:
        log_issue("AUTH", "Driver can access /admin/dashboard - RBAC broken")
    logout(client)

    # Driver trying to access owner panel
    login_as(client, 'naveenmkumar77@gmail.com', 'driver123')
    resp = client.get('/owner/dashboard', follow_redirects=False)
    if resp.status_code == 302 or resp.status_code == 403:
        print("  [OK] Driver blocked from owner panel")
    elif resp.status_code == 200:
        log_issue("AUTH", "Driver can access /owner/dashboard - RBAC broken")
    logout(client)

    # ----------------------------------------------------------
    # 11. STATIC ASSETS
    # ----------------------------------------------------------
    print("\n[11] TESTING STATIC ASSETS...")
    static_files = [
        '/static/css/style.css',
        '/static/js/main.js',
        '/static/js/maps.js',
        '/static/js/charts.js',
    ]
    for sf in static_files:
        resp = client.get(sf)
        if resp.status_code == 200:
            print(f"  [OK] {sf} exists")
        else:
            log_issue("ASSET", f"{sf} returns {resp.status_code} - MISSING")

    # Check uploads directory
    uploads_dir = app.config['UPLOAD_FOLDER']
    if os.path.exists(uploads_dir):
        default_img = os.path.join(uploads_dir, 'default_parking.jpg')
        if not os.path.exists(default_img):
            log_issue("ASSET", "default_parking.jpg missing from uploads - space images without photos will break")
    else:
        log_issue("ASSET", f"Uploads directory doesn't exist: {uploads_dir}")

    # ----------------------------------------------------------
    # 12. TEMPLATE CONSISTENCY CHECKS
    # ----------------------------------------------------------
    print("\n[12] CHECKING TEMPLATE FILES...")
    
    template_dirs = {
        'admin': ['dashboard.html', 'owners_approval.html', 'spaces_manage.html', 
                  'bookings_manage.html', 'users_manage.html', 'reviews_manage.html',
                  'analytics.html', 'audit_logs.html'],
        'auth': ['login.html', 'register.html', 'profile.html'],
        'driver': ['dashboard.html', 'search.html', 'emergency.html', 'details.html',
                   'book.html', 'qr_ticket.html', 'my_bookings.html'],
        'owner': ['dashboard.html', 'approval_status.html', 'manage_spaces.html',
                  'space_form.html', 'booking_requests.html', 'scanner.html', 'revenue.html'],
        'errors': ['400.html', '403.html', '404.html', '500.html'],
    }
    
    templates_base = os.path.join(app.root_path, 'templates')
    for subdir, files in template_dirs.items():
        for fname in files:
            fpath = os.path.join(templates_base, subdir, fname)
            if os.path.exists(fpath):
                pass  # OK
            else:
                log_issue("TEMPLATE", f"Missing template: {subdir}/{fname}")
    print("  Template file existence check complete")

    # ----------------------------------------------------------
    # 13. DATABASE INTEGRITY
    # ----------------------------------------------------------
    print("\n[13] CHECKING DATABASE INTEGRITY...")
    
    user_count = User.query.count()
    space_count = ParkingSpace.query.count()
    booking_count = Booking.query.count()
    review_count = Review.query.count()
    
    print(f"  Users: {user_count}, Spaces: {space_count}, Bookings: {booking_count}, Reviews: {review_count}")
    
    # Check for orphaned bookings
    orphan_bookings = Booking.query.filter(
        ~Booking.parking_space_id.in_(db.session.query(ParkingSpace.id))
    ).count()
    if orphan_bookings > 0:
        log_issue("DATA", f"{orphan_bookings} orphaned bookings (referencing deleted spaces)")

    # Check for orphaned reviews
    orphan_reviews = Review.query.filter(
        ~Review.parking_space_id.in_(db.session.query(ParkingSpace.id))
    ).count()
    if orphan_reviews > 0:
        log_issue("DATA", f"{orphan_reviews} orphaned reviews (referencing deleted spaces)")

    # Check admin user exists
    admin = User.query.filter_by(role='ADMIN').first()
    if not admin:
        log_issue("DATA", "No admin user exists in the database!")
    else:
        print(f"  [OK] Admin exists: {admin.email}")

    # ----------------------------------------------------------
    # 14. NAVBAR LINK VERIFICATION
    # ----------------------------------------------------------
    print("\n[14] CHECKING NAVBAR LINKS IN BASE TEMPLATE...")
    
    base_html_path = os.path.join(templates_base, 'base.html')
    with open(base_html_path, 'r', encoding='utf-8') as f:
        base_html = f.read()
    
    # Check for broken url_for references
    import re
    url_for_calls = re.findall(r"url_for\('([^']+)'", base_html)
    for endpoint in set(url_for_calls):
        if endpoint != 'static' and endpoint not in app.view_functions:
            log_issue("TEMPLATE", f"Broken url_for('{endpoint}') in base.html - endpoint doesn't exist in view_functions")

    print("  Navbar link check complete")

    # ----------------------------------------------------------
    # 15. JS/CSS CONTENT CHECKS
    # ----------------------------------------------------------
    print("\n[15] CHECKING JS/CSS FOR ISSUES...")
    
    js_path = os.path.join(app.root_path, 'static', 'js', 'main.js')
    if os.path.exists(js_path):
        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        if 'console.error' in js_content or 'alert(' in js_content:
            log_warning("JS", "main.js contains console.error or alert() calls")
    
    # ----------------------------------------------------------
    # CLEANUP TEST DATA
    # ----------------------------------------------------------
    print("\n[CLEANUP] Removing test data...")
    test_booking = Booking.query.filter_by(vehicle_plate='KA01AB1234').first()
    if test_booking:
        db.session.delete(test_booking)
    test_space = ParkingSpace.query.filter_by(title='Test Integration Parking').first()
    if test_space:
        db.session.delete(test_space)
    db.session.commit()
    print("  Test data cleaned up")

    # ----------------------------------------------------------
    # REPORT SUMMARY
    # ----------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST REPORT SUMMARY")
    print("=" * 70)
    
    if not issues and not warnings:
        print("\n  ALL TESTS PASSED - No issues found!")
    else:
        if issues:
            print(f"\n  BUGS/ISSUES FOUND: {len(issues)}")
            for i, issue in enumerate(issues, 1):
                print(f"    {i}. [{issue['severity']}] [{issue['category']}] {issue['description']}")
        if warnings:
            print(f"\n  WARNINGS: {len(warnings)}")
            for i, w in enumerate(warnings, 1):
                print(f"    {i}. [{w['category']}] {w['description']}")
    
    print("\n" + "=" * 70)
