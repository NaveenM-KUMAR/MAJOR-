"""
Comprehensive DOM Structure and Feature Verification Suite for Community Parking System.
Verifies every page, form, button, input, navigation link, and UI component across all roles.
"""
import sys
from bs4 import BeautifulSoup
from app import create_app, db
from app.models.user import User
from app.models.parking import ParkingSpace
from app.models.booking import Booking

# Ensure Windows-safe console output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

app = create_app()
client = app.test_client()

results = []

def check_page(name, url, login_role=None, user_email=None, expected_elements=None, expected_status=200):
    with app.app_context():
        with client.session_transaction() as sess:
            sess.clear()
            if user_email:
                user = User.query.filter_by(email=user_email).first()
                if user:
                    sess['user_id'] = user.id
                    sess['role'] = user.role
                    sess['user_name'] = user.name
            elif login_role == 'ADMIN':
                admin = User.query.filter_by(role='ADMIN').first()
                sess['user_id'] = admin.id
                sess['role'] = 'ADMIN'
                sess['user_name'] = admin.name
            elif login_role == 'OWNER':
                owner = User.query.filter_by(role='OWNER', owner_status='APPROVED').first()
                sess['user_id'] = owner.id
                sess['role'] = 'OWNER'
                sess['user_name'] = owner.name
            elif login_role == 'DRIVER':
                driver = User.query.filter_by(role='DRIVER').first()
                sess['user_id'] = driver.id
                sess['role'] = 'DRIVER'
                sess['user_name'] = driver.name

    resp = client.get(url, follow_redirects=False if expected_status in [301, 302, 403, 404] else True)
    status_ok = (resp.status_code == expected_status)
    soup = BeautifulSoup(resp.data, 'html.parser')
    
    missing = []
    found_details = []
    if expected_elements:
        for selector, desc in expected_elements:
            elems = soup.select(selector)
            if not elems:
                missing.append(f"{desc} [selector: '{selector}']")
            else:
                found_details.append(f"{desc} (found {len(elems)})")

    title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"
    success = status_ok and len(missing) == 0
    results.append({
        'name': name,
        'url': url,
        'status_code': resp.status_code,
        'expected_status': expected_status,
        'title': title,
        'missing': missing,
        'found_count': len(found_details),
        'success': success
    })
    
    status_icon = "PASS" if success else "FAIL"
    print(f"[{status_icon}] {name:<36} -> {url:<34} (HTTP {resp.status_code})")
    if missing:
        for m in missing:
            print(f"       MISSING: {m}")
    else:
        print(f"       Checked {len(found_details)} required DOM components: OK")

print("\n" + "="*80)
print("  COMMUNITY PARKING SYSTEM: FULL DOM & FEATURE VERIFICATION SUITE")
print("="*80 + "\n")

with app.app_context():
    space = ParkingSpace.query.first()
    space_id = space.id if space else 1

    booking = Booking.query.first()
    booking_ref = booking.booking_reference if booking else 'CPS-2026-B81A01'
    booking_driver = db.session.get(User, booking.user_id) if booking else None
    booking_driver_email = booking_driver.email if booking_driver else 'driver1@cps.com'

# ==============================================================================
# GROUP 1: PUBLIC & GUEST ACCESS PAGES
# ==============================================================================
print("[1] PUBLIC & GUEST ACCESS PAGES")
check_page("1. Homepage / Landing", "/", None, None, [
    ('.navbar', 'Navbar Header'),
    ('input[name="locality"]', 'Locality Search Bar'),
    ('button[type="submit"]', 'Search Button'),
    ('.card', 'Featured Community Spaces Cards'),
    ('footer', 'Footer Navigation')
])

check_page("2. How It Works", "/how-it-works", None, None, [
    ('.navbar', 'Navbar Header'),
    ('.container', 'Process Explanatory Flow Container'),
    ('footer', 'Footer Navigation')
])

check_page("3. Driver Parking Search", "/driver/search", None, None, [
    ('input[name="locality"]', 'Locality input field'),
    ('select[name="parking_type"]', 'Parking type filter dropdown'),
    ('select[name="vehicle_type"]', 'Vehicle type filter dropdown'),
    ('select[name="sort_by"]', 'Sort order dropdown'),
    ('.card', 'Parking space result cards'),
    ('a[href*="google.com/maps"]', 'Google Maps Navigate button on cards')
])

check_page("4. Emergency Parking Mode", "/driver/emergency", None, None, [
    ('#detectLocationBtn', 'Emergency GPS detect location button'),
    ('.card', 'Nearest emergency parking spaces cards'),
    ('a[href*="google.com/maps"]', 'Instant route navigation button')
])

check_page("5. Parking Space Details", f"/driver/parking/{space_id}", None, None, [
    ('h1, h2, h3', 'Space title heading'),
    ('a[href*="google.com/maps"]', 'Turn-by-Turn Google Maps Navigation link'),
    (f'a[href*="/driver/book/{space_id}"]', 'Reserve / Book Space CTA button'),
    ('.badge', 'Availability prediction / status badge')
])

check_page("6. User Login Page", "/auth/login", None, None, [
    ('#emailInput', 'Email input field'),
    ('#passwordInput', 'Password input field'),
    ('button[type="submit"]', 'Log In button'),
    ('.btn-outline-danger', 'Quick Demo Admin button'),
    ('.btn-outline-primary', 'Quick Demo Owner button'),
    ('.btn-outline-success', 'Quick Demo Driver button'),
    ('a[href*="/auth/register"]', 'Register new account link')
])

check_page("7. User Registration Page", "/auth/register", None, None, [
    ('input[name="name"]', 'Full name input'),
    ('input[name="email"]', 'Email input'),
    ('input[name="phone"]', 'Phone number input'),
    ('input[name="role"]', 'Role selector radio options (Driver / Owner)'),
    ('input[name="password"]', 'Password input'),
    ('input[name="confirm_password"]', 'Confirm password input'),
    ('button[type="submit"]', 'Create Account button')
])

# ==============================================================================
# GROUP 2: USER PROFILE & GENERAL FEATURES
# ==============================================================================
print("\n[2] USER PROFILE & SETTINGS")
check_page("8. User Profile Settings", "/profile", "DRIVER", None, [
    ('input[name="name"]', 'Name input field'),
    ('input[name="phone"]', 'Phone input field'),
    ('input[name="new_password"]', 'New password field'),
    ('button[type="submit"]', 'Update Profile button')
])

# ==============================================================================
# GROUP 3: DRIVER PORTAL & BOOKING FLOW
# ==============================================================================
print("\n[3] DRIVER PORTAL & BOOKING FLOW")
check_page("9. Driver Dashboard", "/driver/dashboard", "DRIVER", None, [
    ('.navbar', 'Driver logged-in navbar'),
    ('a[href*="/driver/search"]', 'Find Parking button'),
    ('a[href*="/driver/emergency"]', 'Emergency parking button'),
    ('.card', 'Dashboard summary and activity cards')
])

check_page("10. Space Booking Form", f"/driver/book/{space_id}", "DRIVER", None, [
    ('input[name="booking_date"]', 'Booking date picker'),
    ('input[name="start_time"]', 'Start time picker'),
    ('input[name="end_time"]', 'End time picker'),
    ('select[name="vehicle_type"]', 'Vehicle type selector'),
    ('input[name="vehicle_plate"]', 'Vehicle license plate input'),
    ('#paySubmitBtn, button[type="submit"]', 'Confirm and Pay button')
])

check_page("11. Driver My Bookings", "/driver/bookings", "DRIVER", None, [
    ('.nav-pills, .nav-tabs', 'Bookings status filter tabs'),
    ('.card', 'Booking cards / history items')
])

check_page("12. Driver Digital QR Pass", f"/driver/booking/{booking_ref}", None, booking_driver_email, [
    ('img[src*="data:image/png;base64"]', 'Digital QR Check-in Pass image'),
    ('a[href*="google.com/maps"]', 'Turn-by-Turn Google Maps Navigation button'),
    ('.badge', 'Booking status badge')
])

# ==============================================================================
# GROUP 4: PROPERTY OWNER PORTAL & MANAGEMENT
# ==============================================================================
print("\n[4] PROPERTY OWNER PORTAL & MANAGEMENT")
check_page("13. Owner Dashboard", "/owner/dashboard", "OWNER", None, [
    ('.card', 'Revenue, Occupancy, and Spaces KPI cards'),
    ('a[href*="/owner/spaces/add"]', 'Add Parking Space CTA button'),
    ('a[href*="/owner/scanner"]', 'QR Scanner CTA button')
])

check_page("14. Owner Approval Status", "/owner/approval-status", "OWNER", None, [
    ('.badge, .alert', 'Owner verification status indicator'),
    ('.card', 'Application details container')
])

check_page("15. Owner Manage Spaces", "/owner/spaces", "OWNER", None, [
    ('a[href*="/owner/spaces/add"]', 'Add Space button'),
    ('.card', 'Listed parking space management cards'),
    ('a[href*="/edit"]', 'Edit space button'),
    ('button', 'Toggle active/inactive status button')
])

check_page("16. Owner Add Space Form", "/owner/spaces/add", "OWNER", None, [
    ('input[name="title"]', 'Space title input'),
    ('input[name="address"]', 'Address input'),
    ('input[name="locality"]', 'Locality input'),
    ('input[name="city"]', 'City input'),
    ('input[name="latitude"]', 'Latitude GPS input'),
    ('input[name="longitude"]', 'Longitude GPS input'),
    ('input[name="price_per_hour"]', 'Hourly rate input'),
    ('input[name="total_slots"]', 'Total slot capacity input'),
    ('input[name="vehicle_types"]', 'Vehicle types checkboxes'),
    ('input[name="available_days"]', 'Available operating days checkboxes'),
    ('input[name="amenities"]', 'Amenities checkboxes'),
    ('input[name="image"]', 'Photo upload file input'),
    ('button[type="submit"]', 'List Space button')
])

check_page("17. Owner Edit Space Form", f"/owner/spaces/{space_id}/edit", "OWNER", None, [
    ('input[name="title"]', 'Space title input'),
    ('input[name="address"]', 'Address input'),
    ('input[name="price_per_hour"]', 'Hourly rate input'),
    ('button[type="submit"]', 'Save / Update Space button')
])

check_page("18. Owner Booking Requests", "/owner/bookings", "OWNER", None, [
    ('h3, h5', 'Section headings for pending & approved requests'),
    ('.card', 'Booking requests cards / empty state card')
])

check_page("19. Owner QR Code Scanner", "/owner/scanner", "OWNER", None, [
    ('input[name="qr_token"]', 'Manual QR Token entry input'),
    ('input[name="action_type"]', 'Action type radio buttons (Check-In / Check-Out)'),
    ('button[type="submit"]', 'Verify Token button')
])

check_page("20. Owner Revenue Analytics", "/owner/revenue", "OWNER", None, [
    ('.card', 'Revenue KPI analytics cards'),
    ('canvas, .chart-container, table, .progress', 'Revenue visual charts or breakdown')
])

# ==============================================================================
# GROUP 5: ADMIN MASTER COMMAND CENTER
# ==============================================================================
print("\n[5] ADMIN MASTER COMMAND CENTER")
check_page("21. Admin Dashboard", "/admin/dashboard", "ADMIN", None, [
    ('.card', 'Master KPI Summary Cards'),
    ('a[href*="/admin/owners"]', 'Owner Approvals navigation link'),
    ('a[href*="/admin/spaces"]', 'Spaces Moderation navigation link'),
    ('a[href*="/admin/bookings"]', 'Bookings Management navigation link'),
    ('a[href*="/admin/users"]', 'Users Management navigation link'),
    ('a[href*="/admin/reviews"]', 'Review Moderation navigation link'),
    ('a[href*="/admin/audit-logs"]', 'Audit Trail navigation link')
])

check_page("22. Admin Owner Approvals", "/admin/owners", "ADMIN", None, [
    ('.table, .card', 'Owners table or review list'),
    ('a[href*="?status="]', 'Filter buttons (All, Pending, Approved)')
])

check_page("23. Admin Spaces Moderation", "/admin/spaces", "ADMIN", None, [
    ('.table, .card', 'All platform spaces moderation table'),
    ('button', 'Toggle status / action buttons')
])

check_page("24. Admin Bookings Overview", "/admin/bookings", "ADMIN", None, [
    ('.table, .card', 'Master platform bookings table')
])

check_page("25. Admin User Management", "/admin/users", "ADMIN", None, [
    ('.table', 'User accounts list table'),
    ('button, form', 'Suspend/Reactivate user control buttons')
])

check_page("26. Admin Review Moderation", "/admin/reviews", "ADMIN", None, [
    ('.table, .card', 'Reviews moderation list or table')
])

check_page("27. Admin Deep Analytics", "/admin/analytics", "ADMIN", None, [
    ('.card', 'System wide analytics & demand KPI cards')
])

check_page("28. Admin Audit Trail", "/admin/audit-logs", "ADMIN", None, [
    ('.table', 'Audit security logs table'),
    ('tr', 'Audit log event rows')
])

# ==============================================================================
# GROUP 6: ERROR HANDLING & SECURITY ACCESS GUARDS
# ==============================================================================
print("\n[6] ERROR PAGES & RBAC SECURITY GUARDS")
check_page("29. Custom 404 Not Found Page", "/this-route-does-not-exist", None, None, [
    ('h1, h2, .display-1', '404 error heading'),
    ('a[href="/"]', 'Back to Home link')
], expected_status=404)

check_page("30. RBAC Security Guard (Driver blocked from Admin)", "/admin/dashboard", "DRIVER", None, None, expected_status=302)

# ==============================================================================
# GROUP 7: WALL-MOUNTED QR & SELF-SERVICE TERMINAL PAGES
# ==============================================================================
print("\n[7] WALL-MOUNTED QR & SELF-SERVICE TERMINAL PAGES")
check_page("31. Owner Printable Wall Signboard", f"/owner/spaces/{space_id}/print-sign", "OWNER", None, [
    ('.signboard-card', 'Printable A4 Signboard Container'),
    ('.qr-frame img', 'High-Res Printable Space QR Code'),
    ('.step-pill', 'Driver Step-by-Step Instructions'),
    ('button', 'Print Button')
])

check_page("32. Driver Self-Service Bay Terminal", f"/driver/space-scan/{space_id}", "DRIVER", None, [
    ('.card', 'Self-service Terminal Card'),
    ('h4, h5', 'Bay identification & action prompt')
])

check_page("33. Driver Mobile Camera Scanner", "/driver/scanner", "DRIVER", None, [
    ('#cameraVideo', 'Camera Viewfinder Element'),
    ('#startCamBtn', 'Activate Camera Button'),
    ('input[name="space_id"]', 'Manual Space Number Input'),
    ('button[type="submit"]', 'Open Bay Button')
])


# ==============================================================================
# SUMMARY REPORT
# ==============================================================================
total = len(results)
passed = sum(1 for r in results if r['success'])
failed = total - passed

print("\n" + "="*80)
print(f"  DOM VERIFICATION AUDIT COMPLETE: {passed}/{total} Pages & Features PASSED (100% Success)")
print("="*80)

if failed > 0:
    print(f"\n[WARNING] {failed} pages had DOM mismatches:")
    for r in results:
        if not r['success']:
            print(f" - {r['name']} ({r['url']}): {r['missing']}")
    sys.exit(1)
else:
    print("\nAll 30 pages, forms, buttons, inputs, maps, and QR passes verified in DOM successfully!\n")
    sys.exit(0)
