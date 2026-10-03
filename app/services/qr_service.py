import io
import base64
import qrcode
from PIL import Image

def generate_qr_base64(qr_token):
    """
    Generates a high-quality QR code image from token and returns
    as a base64 encoded PNG data URI.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    # The payload is the secure token reference
    qr.add_data(qr_token)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="#1e293b", back_color="#ffffff")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return f"data:image/png;base64,{img_str}"


def generate_space_qr_base64(space_id, scan_url=None):
    """
    Generates a wall-mounted signboard QR code for a specific parking space.
    When scanned by any standard smartphone camera or app, it navigates
    directly to the driver self-service check-in / check-out portal.
    """
    payload = scan_url if scan_url else f"/driver/space-scan/{space_id}"
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H, # High error correction for printed signs
        box_size=12,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return f"data:image/png;base64,{img_str}"

