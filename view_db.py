"""
Database Viewer Utility for Community Parking System
Run this script anytime to inspect all database tables in your terminal.
Usage: python view_db.py
"""
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from app import create_app, db
from app.models.user import User
from app.models.parking import ParkingSpace
from app.models.booking import Booking
from app.models.review import Review
from app.models.audit import AuditLog

app = create_app()

def print_separator(char="=", length=85):
    print(char * length)

def view_database():
    with app.app_context():
        print_separator()
        print("  COMMUNITY PARKING SYSTEM -- LIVE DATABASE INSPECTION")
        print_separator()

        # 1. USERS
        users = User.query.all()
        print(f"\n[TABLE: users] -- Total: {len(users)}")
        print(f"{'ID':<4} | {'Name':<20} | {'Role':<8} | {'Status':<8} | {'Email':<25} | {'Phone':<12}")
        print("-" * 85)
        for u in users:
            print(f"{u.id:<4} | {u.name[:18]:<20} | {u.role:<8} | {u.status:<8} | {u.email[:23]:<25} | {u.phone:<12}")

        # 2. PARKING SPACES
        spaces = ParkingSpace.query.all()
        print(f"\n[TABLE: parking_spaces] -- Total: {len(spaces)}")
        print(f"{'ID':<4} | {'Title':<25} | {'Locality':<15} | {'Slots':<6} | {'Price/Hr':<10} | {'Status':<10}")
        print("-" * 80)
        for s in spaces:
            print(f"{s.id:<4} | {s.title[:23]:<25} | {s.locality[:13]:<15} | {s.total_slots:<6} | Rs.{float(s.price_per_hour):<6.2f} | {s.approval_status:<10}")

        # 3. BOOKINGS
        bookings = Booking.query.all()
        print(f"\n[TABLE: bookings] -- Total: {len(bookings)}")
        print(f"{'ID':<4} | {'Reference':<16} | {'Driver ID':<10} | {'Space ID':<9} | {'Date':<11} | {'Status':<10} | {'Total':<8}")
        print("-" * 80)
        for b in bookings:
            print(f"{b.id:<4} | {b.booking_reference:<16} | {b.user_id:<10} | {b.parking_space_id:<9} | {str(b.booking_date):<11} | {b.status:<10} | Rs.{float(b.total_price):<6.2f}")

        # 4. REVIEWS
        reviews = Review.query.all()
        print(f"\n[TABLE: reviews] -- Total: {len(reviews)}")
        print(f"{'ID':<4} | {'Space ID':<9} | {'Driver ID':<10} | {'Rating':<8} | {'Comment':<35}")
        print("-" * 75)
        for r in reviews:
            print(f"{r.id:<4} | {r.parking_space_id:<9} | {r.user_id:<10} | {r.rating} stars | {r.comment[:33]:<35}")

        # 5. RECENT AUDIT LOGS
        logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(5).all()
        print(f"\n[TABLE: audit_logs (Last 5 actions)] -- Total: {AuditLog.query.count()}")
        print(f"{'ID':<4} | {'Action':<25} | {'Entity':<15} | {'Actor ID':<9} | {'Timestamp':<20}")
        print("-" * 80)
        for l in logs:
            ts = l.created_at.strftime("%Y-%m-%d %H:%M:%S") if l.created_at else ""
            print(f"{l.id:<4} | {l.action[:23]:<25} | {l.target_entity[:13]:<15} | {str(l.actor_id):<9} | {ts:<20}")

        print_separator()
        print("  Database inspection complete.")
        print_separator()

if __name__ == "__main__":
    view_database()
