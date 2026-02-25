"""
Verification Service - QR Code Generation
============================================
Generate QR codes for gold bars linking to the public verification page.
High-res QR + serial text for laser printing on packaging.

SECURITY: QR images are generated on-the-fly (never saved to disk).
Only accessible via authenticated admin endpoint.
"""

import io
import qrcode
from qrcode.image.pil import PilImage
from PIL import Image, ImageDraw, ImageFont

from config.settings import BASE_URL


class VerificationService:

    def generate_qr_bytes(self, serial_code: str) -> bytes:
        """Generate QR code PNG bytes for a bar's verification URL (web display)."""
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

    def generate_qr_for_print(self, serial_code: str) -> bytes:
        """Generate high-res QR code + serial text for printing.

        Returns PNG bytes (never saved to disk — security by design).

        - QR: box_size=20, border=0, ERROR_CORRECT_M
        - No logo — maximum scan reliability even with weak cameras
        - Serial text: bold, auto-sized to fill QR width
        - QR flush to edges (no whitespace)
        """
        url = f"{BASE_URL}/verify/check?code={serial_code}"

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=20,
            border=0,
        )
        qr.add_data(url)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        # Crop all white borders so QR is flush on every side
        bbox = qr_img.getbbox()
        if bbox:
            qr_img = qr_img.crop(bbox)
        qr_w, qr_h = qr_img.size

        # Calculate font size so serial text fills the full QR width
        text = serial_code
        ref_size = 60
        ref_font = self._get_font(size=ref_size)
        temp_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        ref_bbox = temp_draw.textbbox((0, 0), text, font=ref_font)
        ref_text_w = ref_bbox[2] - ref_bbox[0]
        target_font_size = max(20, int(ref_size * qr_w / ref_text_w))
        font = self._get_font(size=target_font_size)

        # Measure actual text dimensions
        text_bbox = temp_draw.textbbox((0, 0), text, font=font)
        actual_text_h = text_bbox[3] - text_bbox[1]
        text_height = actual_text_h + 50

        # Build final image: QR flush to edges + serial text below
        final_img = Image.new("RGB", (qr_w, qr_h + text_height), "white")
        final_img.paste(qr_img, (0, 0))

        draw = ImageDraw.Draw(final_img)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_x = (qr_w - text_w) // 2
        text_y = qr_h + 5

        draw.text((text_x, text_y), text, fill="black", font=font)

        buf = io.BytesIO()
        final_img.save(buf, format="PNG")
        buf.seek(0)
        return buf.getvalue()

    def _get_font(self, size: int = 40) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Try to load a good bold monospace font, fall back to default."""
        font_candidates = [
            "consolab.ttf",         # Windows Consolas Bold
            "courbd.ttf",           # Windows Courier New Bold
            "arialbd.ttf",          # Windows Arial Bold (fallback)
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf",
            "/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf",  # Arch
            "DejaVuSansMono-Bold.ttf",  # Linux (short name)
            # Regular fallbacks if no bold found
            "consola.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "DejaVuSansMono.ttf",
        ]
        for font_name in font_candidates:
            try:
                return ImageFont.truetype(font_name, size)
            except (OSError, IOError):
                continue

        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()


verification_service = VerificationService()
