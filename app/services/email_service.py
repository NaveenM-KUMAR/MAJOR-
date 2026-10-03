"""
Email Notification Service for Community Parking System
Handles asynchronous dispatch of HTML receipts, payment confirmations,
and owner KYC verification alerts.
"""
import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Local preview directory for testing and seminar presentation
SENT_EMAILS_DIR = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'instance', 'sent_emails')
os.makedirs(SENT_EMAILS_DIR, exist_ok=True)

def _dispatch_email_thread(to_email, subject, html_content, text_content=None):
    """Background thread worker to dispatch emails without blocking web requests."""
    from flask import current_app
    
    server_host = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    server_port = int(os.environ.get('MAIL_PORT', 587))
    use_tls = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    username = os.environ.get('MAIL_USERNAME', '').strip()
    password = os.environ.get('MAIL_PASSWORD', '').strip()
    sender = os.environ.get('MAIL_DEFAULT_SENDER', 'Community Parking System <noreply@cps.com>')

    # 1. Save local HTML copy for offline presentation / inspection
    try:
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_subject = "".join([c if c.isalnum() else "_" for c in subject])[:30]
        filename = f"{timestamp_str}_{safe_subject}.html"
        filepath = os.path.join(SENT_EMAILS_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"<!-- To: {to_email} | Subject: {subject} | Date: {datetime.now()} -->\n")
            f.write(html_content)
        # Also maintain a symlink-like latest.html for quick viewing
        latest_path = os.path.join(SENT_EMAILS_DIR, 'latest_email.html')
        with open(latest_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    except Exception as e:
        print(f"[!] Warning: Could not save email preview file: {e}")

    # 2. If SMTP credentials exist, send live email over the internet
    if username and password:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender
            msg['To'] = to_email

            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))

            server = smtplib.SMTP(server_host, server_port, timeout=10)
            if use_tls:
                server.starttls()
            server.login(username, password)
            server.sendmail(sender, [to_email], msg.as_string())
            server.quit()
            print(f"[EMAIL LIVE SENT] To: {to_email} | Subject: {subject}")
            return True
        except Exception as e:
            print(f"[EMAIL ERROR] Failed sending to {to_email} via SMTP: {e}")
            return False
    else:
        # Simulation / Local Demo Mode
        clean_subject = subject.encode('ascii', errors='ignore').decode('ascii')
        print(f"\n========================================================")
        print(f"[EMAIL NOTIFICATION DISPATCHED (Simulation Mode)]")
        print(f"   To:      {to_email}")
        print(f"   Subject: {clean_subject}")
        print(f"   Preview: {filepath}")
        print(f"========================================================\n")
        return True

def send_async_email(to_email, subject, html_content, text_content=None):
    """Fires non-blocking background thread for sending email."""
    t = threading.Thread(
        target=_dispatch_email_thread,
        args=(to_email, subject, html_content, text_content),
        daemon=True
    )
    t.start()


# ==========================================
# PRE-STYLED EMAIL TEMPLATES
# ==========================================

def send_owner_approval_email(owner):
    """Triggered when Admin approves space owner KYC."""
    subject = "🎉 Your Space Owner Account is Approved! — Community Parking System"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 30px; text-align: center; color: #ffffff;">
                <h1 style="margin: 0; font-size: 24px; font-weight: bold;">Account Approved!</h1>
                <p style="margin: 8px 0 0; font-size: 15px; opacity: 0.9;">Welcome to the Community Parking Network</p>
            </div>
            <div style="padding: 30px;">
                <p style="font-size: 16px;">Hello <strong>{owner.name}</strong>,</p>
                <p style="color: #475569; line-height: 1.6;">
                    Great news! The administrator has reviewed your property documents and <strong>approved your Space Owner account</strong>.
                </p>
                <div style="background: #ecfdf5; border-left: 4px solid #10b981; padding: 15px; border-radius: 4px; margin: 20px 0;">
                    <strong style="color: #065f46;">You can now:</strong>
                    <ul style="margin: 8px 0 0; padding-left: 20px; color: #047857;">
                        <li>List your private driveway, garage, or commercial space</li>
                        <li>Set your own hourly & daily parking rates</li>
                        <li>Scan driver QR passes upon check-in and check-out</li>
                        <li>Earn income from your unused parking space</li>
                    </ul>
                </div>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="http://127.0.0.1:5000/owner/spaces/new" style="background: #10b981; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block;">
                        + List Your First Parking Space
                    </a>
                </div>
                <p style="font-size: 13px; color: #94a3b8; text-align: center; margin-top: 30px; border-top: 1px solid #e2e8f0; padding-top: 15px;">
                    Community Parking System — Peer-to-Peer Smart Urban Mobility
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    send_async_email(owner.email, subject, html_content)


def send_owner_rejection_email(owner, reason):
    """Triggered when Admin rejects space owner KYC."""
    subject = "Notice Regarding Your Space Owner Application — Community Parking System"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <div style="background: #ef4444; padding: 25px; text-align: center; color: #ffffff;">
                <h2 style="margin: 0;">Verification Update</h2>
            </div>
            <div style="padding: 30px;">
                <p>Hello <strong>{owner.name}</strong>,</p>
                <p style="color: #475569; line-height: 1.6;">
                    Thank you for applying to list spaces on Community Parking System. Following verification, our administration team was unable to approve your application at this time.
                </p>
                <div style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 15px; margin: 20px 0;">
                    <strong>Reason for rejection:</strong>
                    <p style="color: #b91c1c; margin: 5px 0 0;">{reason}</p>
                </div>
                <p style="color: #475569;">Please re-upload a clear government ID proof or update your property address to request re-verification.</p>
            </div>
        </div>
    </body>
    </html>
    """
    send_async_email(owner.email, subject, html_content)


def send_booking_payment_receipt_email(booking, driver, space, owner):
    """Triggered when a booking is created and payment confirmed."""
    subject = f"✅ Payment Receipt & Booking Confirmation [{booking.booking_reference}]"
    b_date_str = booking.booking_date.strftime('%d %B %Y') if hasattr(booking.booking_date, 'strftime') else str(booking.booking_date)
    start_str = booking.start_time.strftime('%H:%M') if hasattr(booking.start_time, 'strftime') else str(booking.start_time)
    end_str = booking.end_time.strftime('%H:%M') if hasattr(booking.end_time, 'strftime') else str(booking.end_time)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); padding: 30px; text-align: center; color: #ffffff;">
                <h2 style="margin: 0; font-size: 22px;">Booking & Payment Receipt</h2>
                <p style="margin: 5px 0 0; font-size: 14px; opacity: 0.85;">Ref: {booking.booking_reference}</p>
            </div>

            <!-- Content -->
            <div style="padding: 30px;">
                <p style="font-size: 15px;">Hello <strong>{driver.name}</strong>,</p>
                <p style="color: #475569; font-size: 14px;">Your parking spot reservation has been confirmed. Below is your official receipt and ticket details:</p>

                <!-- Receipt Table -->
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px;">
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                        <td style="padding: 10px 0; color: #64748b;">Parking Space:</td>
                        <td style="padding: 10px 0; text-align: right; font-weight: bold;">{space.title}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                        <td style="padding: 10px 0; color: #64748b;">Location:</td>
                        <td style="padding: 10px 0; text-align: right;">{space.address}, {space.locality}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                        <td style="padding: 10px 0; color: #64748b;">Date of Booking:</td>
                        <td style="padding: 10px 0; text-align: right; font-weight: bold;">{b_date_str}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                        <td style="padding: 10px 0; color: #64748b;">Scheduled Time:</td>
                        <td style="padding: 10px 0; text-align: right;">{start_str} - {end_str} ({float(booking.duration_hours):.1f} hrs)</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                        <td style="padding: 10px 0; color: #64748b;">Vehicle Plate:</td>
                        <td style="padding: 10px 0; text-align: right; font-weight: bold;">{booking.vehicle_plate} ({booking.vehicle_type})</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                        <td style="padding: 10px 0; color: #64748b;">Host / Space Owner:</td>
                        <td style="padding: 10px 0; text-align: right;">{owner.name} ({owner.phone})</td>
                    </tr>
                    <tr style="background: #f1f5f9;">
                        <td style="padding: 12px 10px; font-size: 16px; font-weight: bold; color: #0f172a;">Amount Paid:</td>
                        <td style="padding: 12px 10px; text-align: right; font-size: 18px; font-weight: bold; color: #10b981;">₹{float(booking.total_price):.2f}</td>
                    </tr>
                </table>

                <!-- QR Ticket & Navigation Links -->
                <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 20px; text-align: center; margin: 25px 0;">
                    <h3 style="margin: 0 0 8px; color: #1e40af; font-size: 16px;">📱 Your Digital QR Gate Pass</h3>
                    <p style="margin: 0 0 15px; font-size: 13px; color: #3b82f6;">Present your QR pass to the owner upon arrival to check in seamlessly.</p>
                    <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap;">
                        <a href="http://127.0.0.1:5000/driver/ticket/{booking.booking_reference}" style="background: #2563eb; color: #ffffff; text-decoration: none; padding: 10px 22px; border-radius: 25px; font-weight: bold; font-size: 14px; display: inline-block; margin: 4px;">
                            View QR Ticket Pass
                        </a>
                        <a href="https://www.google.com/maps/dir/?api=1&destination={space.latitude},{space.longitude}" target="_blank" style="background: #059669; color: #ffffff; text-decoration: none; padding: 10px 22px; border-radius: 25px; font-weight: bold; font-size: 14px; display: inline-block; margin: 4px;">
                            🚗 Start GPS Navigation
                        </a>
                    </div>
                </div>

                <p style="font-size: 12px; color: #94a3b8; text-align: center; margin-top: 20px;">
                    Thank you for choosing Community Parking System. Safe travels!
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    send_async_email(driver.email, subject, html_content)


def send_owner_new_booking_alert_email(booking, owner, space, driver):
    """Notifies the space owner that a driver has booked their spot."""
    subject = f"🔔 New Booking Alert: {space.title} on {booking.booking_date}"
    b_date_str = booking.booking_date.strftime('%d %B %Y') if hasattr(booking.booking_date, 'strftime') else str(booking.booking_date)
    start_str = booking.start_time.strftime('%H:%M') if hasattr(booking.start_time, 'strftime') else str(booking.start_time)
    end_str = booking.end_time.strftime('%H:%M') if hasattr(booking.end_time, 'strftime') else str(booking.end_time)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <div style="background: #0f172a; padding: 25px; text-align: center; color: #ffffff;">
                <h2 style="margin: 0;">New Reservation Received</h2>
                <p style="margin: 5px 0 0; color: #94a3b8; font-size: 14px;">Booking #{booking.booking_reference}</p>
            </div>
            <div style="padding: 30px;">
                <p>Hello <strong>{owner.name}</strong>,</p>
                <p style="color: #475569;">A driver has just booked a parking slot at your listing: <strong>{space.title}</strong>.</p>
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin: 20px 0; font-size: 14px;">
                    <p style="margin: 5px 0;"><strong>Driver Name:</strong> {driver.name}</p>
                    <p style="margin: 5px 0;"><strong>Vehicle:</strong> {booking.vehicle_plate} ({booking.vehicle_type})</p>
                    <p style="margin: 5px 0;"><strong>Schedule:</strong> {b_date_str} from {start_str} to {end_str}</p>
                    <p style="margin: 5px 0;"><strong>Your Payout:</strong> <span style="color: #10b981; font-weight: bold;">₹{float(booking.total_price):.2f}</span></p>
                </div>
                <div style="text-align: center; margin-top: 25px;">
                    <a href="http://127.0.0.1:5000/owner/scanner" style="background: #0f172a; color: #ffffff; text-decoration: none; padding: 10px 24px; border-radius: 20px; font-weight: bold; font-size: 14px; display: inline-block;">
                        Open QR Check-In Scanner
                    </a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    send_async_email(owner.email, subject, html_content)
