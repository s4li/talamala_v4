"""
Verification Service - QR Code Generation
============================================
Generate QR codes for gold bars linking to the public verification page.
"""

import io
import qrcode
from qrcode.image.pil import PilImage

from config.settings import BASE_URL


class VerificationService:

    def generate_qr_bytes(self, serial_code: str) -> bytes:
        """Generate QR code PNG bytes for a bar's verification URL."""
        url = f"{BASE_URL}/verify/check?code={serial_code}"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img: PilImage = qr.make_image(fill_color="#1a1a2e", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.getvalue()


verification_service = VerificationService()
