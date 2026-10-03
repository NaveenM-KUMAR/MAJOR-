import os
from datetime import datetime, date, time, timedelta
from app.utils.timezone import utcnow
from decimal import Decimal
from app import create_app, db
from app.models.user import User
from app.models.parking import ParkingSpace
from app.models.booking import Booking
from app.models.review import Review
from app.models.notification import Notification
from app.models.audit import AuditLog

def seed_database(target_app=None):
    """Populates realistic demonstration dataset for evaluation and viva demonstration."""
    if target_app is None:
        target_app = create_app()
    with target_app.app_context():
        print("[*] Seeding Community Parking System Database...")
        db.create_all()

        # Check if already seeded
        if ParkingSpace.query.first():
            print("Database already contains seed data. Skipping creation.")
            return

        def get_or_create_user(name, email, phone, role, password, **kwargs):
            user = User.query.filter((User.email == email) | (User.phone == phone)).first()
            if not user:
                user = User(name=name, email=email, phone=phone, role=role, **kwargs)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
            else:
                user.name = name
                user.email = email
                user.phone = phone
                user.role = role
                user.set_password(password)
                for k, v in kwargs.items():
                    setattr(user, k, v)
                db.session.commit()
            return user

        # 1. Create Administrator
        admin = get_or_create_user(
            name="System Administrator",
            email="admin@cps.com",
            phone="9000000001",
            role="ADMIN",
            password="admin123",
            status="ACTIVE"
        )

        # 2. Create Property Owners
        owner1 = get_or_create_user(
            name="Rajesh Sharma",
            email="owner1@cps.com",
            phone="9876543210",
            role="OWNER",
            password="owner123",
            status="ACTIVE",
            owner_status="APPROVED",
            owner_address="#45, 4th Cross, 5th Block, Koramangala, Bangalore"
        )

        owner2 = get_or_create_user(
            name="Priya Venkat",
            email="owner2@cps.com",
            phone="9876543211",
            role="OWNER",
            password="owner123",
            status="ACTIVE",
            owner_status="APPROVED",
            owner_address="#12, 100 Feet Road, Indiranagar, Bangalore"
        )

        pending_owner = get_or_create_user(
            name="Vikram Mehta",
            email="pending_owner@cps.com",
            phone="9876543212",
            role="OWNER",
            password="owner123",
            status="ACTIVE",
            owner_status="PENDING",
            owner_address="#88, Outer Ring Road, Bellandur, Bangalore"
        )

        # 3. Create Drivers
        driver1 = get_or_create_user(
            name="Ananya Rao",
            email="driver1@cps.com",
            phone="9123456780",
            role="DRIVER",
            password="driver123",
            status="ACTIVE"
        )

        driver2 = get_or_create_user(
            name="Karthik Kumar",
            email="driver2@cps.com",
            phone="9123456781",
            role="DRIVER",
            password="driver123",
            status="ACTIVE"
        )

        driver3 = get_or_create_user(
            name="Sneha Patel",
            email="driver3@cps.com",
            phone="9123456782",
            role="DRIVER",
            password="driver123",
            status="ACTIVE"
        )

        # 4. Create Community Parking Spaces
        space1 = ParkingSpace(
            owner_id=owner1.id,
            title="Secure Covered Driveway near Sony World Signal",
            description="Spacious gated residential driveway with automated gate and CCTV. 3 minutes walk to Koramangala Sony World Signal. Suitable for SUVs and hatchbacks.",
            address="#45, 4th Cross, 5th Block, Koramangala",
            locality="Koramangala",
            city="Bangalore",
            latitude=Decimal('12.935200'),
            longitude=Decimal('77.624500'),
            parking_type="Private Driveway",
            vehicle_types="Car, Two Wheeler, SUV",
            total_slots=2,
            price_per_hour=Decimal('35.00'),
            price_per_day=Decimal('250.00'),
            operating_start=time(6, 0),
            operating_end=time(23, 0),
            available_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
            rules="Please reverse park. Keep speeds under 10 km/h in residential lane.",
            amenities="CCTV, Gated Security, Well Lit, Covered Roof",
            image_url="default_parking.jpg",
            is_active=True,
            approval_status="APPROVED"
        )

        space2 = ParkingSpace(
            owner_id=owner1.id,
            title="Koramangala 4th Block Wide Driveway",
            description="Wide private parking bay in a serene gated colony. Ideal for daily commuters to nearby offices and dining establishments.",
            address="#110, 80 Feet Road, 4th Block, Koramangala",
            locality="Koramangala",
            city="Bangalore",
            latitude=Decimal('12.931800'),
            longitude=Decimal('77.622900'),
            parking_type="Private Driveway",
            vehicle_types="Car, Two Wheeler, EV",
            total_slots=3,
            price_per_hour=Decimal('40.00'),
            price_per_day=Decimal('300.00'),
            operating_start=time(7, 0),
            operating_end=time(22, 0),
            available_days="Mon,Tue,Wed,Thu,Fri,Sat",
            rules="EV 15A charging plug available upon request with extra charge.",
            amenities="CCTV, EV Charging, Security Guard",
            image_url="default_parking.jpg",
            is_active=True,
            approval_status="APPROVED"
        )

        space3 = ParkingSpace(
            owner_id=owner2.id,
            title="100ft Road Prime Commercial Frontage Lot",
            description="Paved community parking lot directly off 100 Feet Road Indiranagar. Extremely convenient for shopping, dining, and metro access.",
            address="#12, 100 Feet Road, HAL 2nd Stage, Indiranagar",
            locality="Indiranagar",
            city="Bangalore",
            latitude=Decimal('12.978400'),
            longitude=Decimal('77.640800'),
            parking_type="Commercial",
            vehicle_types="Car, Two Wheeler, SUV, EV",
            total_slots=4,
            price_per_hour=Decimal('50.00'),
            price_per_day=Decimal('400.00'),
            operating_start=time(8, 0),
            operating_end=time(23, 30),
            available_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
            rules="No commercial transport goods loading.",
            amenities="24/7 Guard, High-Res CCTV, Wide Entry",
            image_url="default_parking.jpg",
            is_active=True,
            approval_status="APPROVED"
        )

        space4 = ParkingSpace(
            owner_id=owner2.id,
            title="Indiranagar 12th Main Gated Garage",
            description="Completely enclosed private garage with secure lockbox and CCTV monitoring. Safe overnight parking for luxury vehicles.",
            address="#77, 12th Main Road, Indiranagar",
            locality="Indiranagar",
            city="Bangalore",
            latitude=Decimal('12.971900'),
            longitude=Decimal('77.641200'),
            parking_type="Covered Garage",
            vehicle_types="Car, SUV",
            total_slots=1,
            price_per_hour=Decimal('45.00'),
            price_per_day=Decimal('350.00'),
            operating_start=time(6, 0),
            operating_end=time(22, 0),
            available_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
            rules="Keep garage shutter pulled down when leaving.",
            amenities="Fully Covered, Keyless Entry, CCTV",
            image_url="default_parking.jpg",
            is_active=True,
            approval_status="APPROVED"
        )

        db.session.add_all([space1, space2, space3, space4])
        db.session.commit()

        # 5. Create Realistic Historical & Active Bookings
        today = utcnow().date()
        
        # Completed historical bookings for revenue and prediction
        b1 = Booking(
            booking_reference="CPS-2026-B81A01",
            user_id=driver1.id,
            parking_space_id=space1.id,
            booking_date=today - timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(14, 0),
            duration_hours=Decimal('4.00'),
            vehicle_type="Car",
            vehicle_plate="KA01MJ4521",
            total_price=Decimal('140.00'),
            status="COMPLETED",
            qr_token="CPS-QR-HIST001",
            check_in_time=datetime.combine(today - timedelta(days=2), time(10, 2)),
            check_out_time=datetime.combine(today - timedelta(days=2), time(13, 58))
        )

        b2 = Booking(
            booking_reference="CPS-2026-B81A02",
            user_id=driver2.id,
            parking_space_id=space3.id,
            booking_date=today - timedelta(days=1),
            start_time=time(17, 0),
            end_time=time(20, 0),
            duration_hours=Decimal('3.00'),
            vehicle_type="SUV",
            vehicle_plate="KA05NB8899",
            total_price=Decimal('150.00'),
            status="COMPLETED",
            qr_token="CPS-QR-HIST002",
            check_in_time=datetime.combine(today - timedelta(days=1), time(17, 5)),
            check_out_time=datetime.combine(today - timedelta(days=1), time(20, 0))
        )

        b3 = Booking(
            booking_reference="CPS-2026-B81A03",
            user_id=driver3.id,
            parking_space_id=space1.id,
            booking_date=today - timedelta(days=1),
            start_time=time(9, 0),
            end_time=time(12, 0),
            duration_hours=Decimal('3.00'),
            vehicle_type="Car",
            vehicle_plate="KA03EK7112",
            total_price=Decimal('105.00'),
            status="COMPLETED",
            qr_token="CPS-QR-HIST003",
            check_in_time=datetime.combine(today - timedelta(days=1), time(9, 3)),
            check_out_time=datetime.combine(today - timedelta(days=1), time(11, 55))
        )

        # Active checked-in booking today
        b_active = Booking(
            booking_reference="CPS-2026-B81A04",
            user_id=driver1.id,
            parking_space_id=space3.id,
            booking_date=today,
            start_time=time(14, 0),
            end_time=time(19, 0),
            duration_hours=Decimal('5.00'),
            vehicle_type="Car",
            vehicle_plate="KA01MJ4521",
            total_price=Decimal('250.00'),
            status="ACTIVE",
            qr_token="CPS-QR-ACTIVE001",
            check_in_time=datetime.combine(today, time(14, 5))
        )

        # Upcoming approved booking
        b_upcoming = Booking(
            booking_reference="CPS-2026-B81A05",
            user_id=driver2.id,
            parking_space_id=space2.id,
            booking_date=today + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(13, 0),
            duration_hours=Decimal('3.00'),
            vehicle_type="Car",
            vehicle_plate="KA05NB8899",
            total_price=Decimal('120.00'),
            status="APPROVED",
            qr_token="CPS-QR-UPCOMING001"
        )

        # Pending booking request
        b_pending = Booking(
            booking_reference="CPS-2026-B81A06",
            user_id=driver3.id,
            parking_space_id=space1.id,
            booking_date=today + timedelta(days=2),
            start_time=time(15, 0),
            end_time=time(18, 0),
            duration_hours=Decimal('3.00'),
            vehicle_type="Two Wheeler",
            vehicle_plate="KA03EK7112",
            total_price=Decimal('105.00'),
            status="PENDING",
            qr_token="CPS-QR-PENDING001"
        )

        db.session.add_all([b1, b2, b3, b_active, b_upcoming, b_pending])
        db.session.commit()

        # 6. Reviews
        r1 = Review(
            booking_id=b1.id,
            parking_space_id=space1.id,
            user_id=driver1.id,
            rating=5,
            comment="Outstanding private driveway! Very easy to locate in Koramangala. The owner was extremely polite and check-in was seamless."
        )
        r2 = Review(
            booking_id=b2.id,
            parking_space_id=space3.id,
            user_id=driver2.id,
            rating=5,
            comment="Prime location right on 100ft road Indiranagar. Saved me at least 25 minutes of wandering looking for roadside parking."
        )
        r3 = Review(
            booking_id=b3.id,
            parking_space_id=space1.id,
            user_id=driver3.id,
            rating=4,
            comment="Spacious and safe parking. Clean compound and good lighting."
        )
        db.session.add_all([r1, r2, r3])

        # 7. Audit Logs
        log1 = AuditLog(actor_id=admin.id, action="SYSTEM_INIT", target_entity="System", target_id=1, details="System initialized and seeded with demo baseline")
        log2 = AuditLog(actor_id=admin.id, action="OWNER_APPROVE", target_entity="User", target_id=owner1.id, details="Approved owner Rajesh Sharma")
        log3 = AuditLog(actor_id=admin.id, action="OWNER_APPROVE", target_entity="User", target_id=owner2.id, details="Approved owner Priya Venkat")
        log4 = AuditLog(actor_id=owner2.id, action="QR_CHECK_IN", target_entity="Booking", target_id=b_active.id, details="Driver check-in verified via QR scanner")

        db.session.add_all([log1, log2, log3, log4])
        db.session.commit()

        print("[SUCCESS] Demo data seeded successfully!")
        print("Demo Credentials:")
        print("   - Admin:  admin@cps.com   / admin123")
        print("   - Owner:  owner1@cps.com  / owner123")
        print("   - Driver: driver1@cps.com / driver123")

if __name__ == '__main__':
    seed_database()
