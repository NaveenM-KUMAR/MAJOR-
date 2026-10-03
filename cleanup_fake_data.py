"""
Database cleanup script:
Removes all fake registered users (retains only ADMIN accounts),
and deletes all listed parking spaces along with their bookings, reviews, and images.
"""
import os
from app import create_app, db
from app.models.user import User
from app.models.parking import ParkingSpace, ParkingImage
from app.models.booking import Booking
from app.models.review import Review
from app.models.notification import Notification
from app.models.audit import AuditLog

app = create_app()

def cleanup():
    with app.app_context():
        print("[*] Starting database cleanup...")

        # 1. Identify admin users to preserve
        admin_users = User.query.filter_by(role='ADMIN').all()
        admin_ids = [a.id for a in admin_users]
        print(f"[+] Preserving Admin accounts ({len(admin_users)} found):")
        for a in admin_users:
            print(f"    - ID: {a.id} | {a.name} ({a.email})")

        # 2. Identify non-admin users to delete
        non_admin_users = User.query.filter(User.role != 'ADMIN').all()
        non_admin_ids = [u.id for u in non_admin_users]
        print(f"\n[-] Found {len(non_admin_users)} non-admin users to remove.")

        # 3. Delete all reviews
        review_count = Review.query.count()
        Review.query.delete(synchronize_session=False)
        print(f"[-] Deleted {review_count} reviews.")

        # 4. Delete all bookings
        booking_count = Booking.query.count()
        Booking.query.delete(synchronize_session=False)
        print(f"[-] Deleted {booking_count} bookings.")

        # 5. Delete all parking space images & parking spaces
        image_count = ParkingImage.query.count()
        ParkingImage.query.delete(synchronize_session=False)
        print(f"[-] Deleted {image_count} parking images.")

        space_count = ParkingSpace.query.count()
        ParkingSpace.query.delete(synchronize_session=False)
        print(f"[-] Deleted {space_count} parking spaces.")

        # 6. Delete notifications for non-admin users
        if non_admin_ids:
            notif_count = Notification.query.filter(Notification.user_id.in_(non_admin_ids)).delete(synchronize_session=False)
            print(f"[-] Deleted {notif_count} notifications for non-admin users.")

        # 7. Unlink or delete audit logs associated with non-admin users
        if non_admin_ids:
            audit_count = AuditLog.query.filter(AuditLog.actor_id.in_(non_admin_ids)).delete(synchronize_session=False)
            print(f"[-] Deleted {audit_count} audit logs for non-admin users.")

        # 8. Delete all non-admin users
        for u in non_admin_users:
            print(f"[-] Removing user: {u.name} ({u.email}, Role: {u.role})")
            db.session.delete(u)

        db.session.commit()
        print("\n[SUCCESS] Cleanup successfully executed and committed to database!")

        # 9. Verify current database state
        remaining_users = User.query.all()
        remaining_spaces = ParkingSpace.query.count()
        remaining_bookings = Booking.query.count()

        print("\n=== CURRENT DATABASE STATE ===")
        print(f"Users remaining ({len(remaining_users)}):")
        for u in remaining_users:
            print(f"  - ID: {u.id} | {u.name} ({u.email}) [Role: {u.role}]")
        print(f"Parking spaces remaining: {remaining_spaces}")
        print(f"Bookings remaining: {remaining_bookings}")

if __name__ == '__main__':
    cleanup()
