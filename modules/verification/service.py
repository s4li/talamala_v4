"""
Verification Service - QR Code Generation
============================================
Generate QR codes for gold bars linking to the public verification page.
Includes high-res QR with logo + serial text for laser printing on packaging.

SECURITY: QR images are generated on-the-fly (never saved to disk).
Only accessible via authenticated admin endpoint.
"""

import io
import os
import qrcode
from qrcode.image.pil import PilImage
from PIL import Image, ImageDraw, ImageFont

from config.settings import BASE_URL

# Custom logo path (user can replace with their own PNG)
LOGO_PATH = os.path.join("static", "assets", "img", "logo-qr.png")

# Brand color from SVG logomark
BRAND_COLOR = "#9E0042"


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
        """Generate high-res QR code with logo + serial text for laser printing.

        Returns PNG bytes (never saved to disk — security by design).

        - QR: box_size=20, border=0, ERROR_CORRECT_H (30% tolerance for logo)
        - Logo: brand logo embedded in center (~18% of QR area)
        - Serial text: auto-sized to fill QR width, printed below QR
        - QR flush to top/left/right edges (no whitespace)
        """
        url = f"{BASE_URL}/verify/check?code={serial_code}"

        # Generate QR with high error correction (needed for center logo)
        qr = qrcode.QRCode(
            version=None,  # auto-fit
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=20,
            border=0,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Create QR image — pure black on white for best laser printing
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

        # Embed logo in center
        logo = self._get_logo_image()
        if logo:
            qr_w, qr_h = qr_img.size
            # Logo should be ~18% of QR width
            logo_max = int(qr_w * 0.18)
            logo.thumbnail((logo_max, logo_max), Image.LANCZOS)
            logo_w, logo_h = logo.size

            # White padding around logo (prevents QR interference)
            pad = 8
            bg = Image.new("RGBA", (logo_w + pad * 2, logo_h + pad * 2), "white")
            bg.paste(logo, (pad, pad), logo if logo.mode == "RGBA" else None)

            # Paste centered
            pos_x = (qr_w - bg.width) // 2
            pos_y = (qr_h - bg.height) // 2
            qr_img.paste(bg, (pos_x, pos_y), bg)

        # Convert to RGB for final output
        qr_rgb = Image.new("RGB", qr_img.size, "white")
        qr_rgb.paste(qr_img, mask=qr_img.split()[3])

        # Crop ALL white borders so QR is flush on every side
        bbox = qr_rgb.getbbox()
        if bbox:
            qr_rgb = qr_rgb.crop(bbox)
        qr_w, qr_h = qr_rgb.size

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
        final_img.paste(qr_rgb, (0, 0))

        draw = ImageDraw.Draw(final_img)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_x = (qr_w - text_w) // 2
        text_y = qr_h + 5

        draw.text((text_x, text_y), text, fill="black", font=font)

        # Return as bytes (never save to disk)
        buf = io.BytesIO()
        final_img.save(buf, format="PNG")
        buf.seek(0)
        return buf.getvalue()

    def _get_logo_image(self) -> Image.Image | None:
        """Load brand logo for QR embedding.

        Priority:
        1. Custom PNG at static/assets/img/logo-qr.png
        2. Auto-generated circle logo with brand color
        """
        if os.path.exists(LOGO_PATH):
            try:
                return Image.open(LOGO_PATH).convert("RGBA")
            except Exception:
                pass

        # Fallback: generate a simple brand circle logo
        return self._generate_fallback_logo()

    def _generate_fallback_logo(self) -> Image.Image:
        """Create a simple circular brand logo with TM initials."""
        size = 120
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw filled circle with brand color
        draw.ellipse([4, 4, size - 4, size - 4], fill=BRAND_COLOR)

        # Draw "TM" text in center (white)
        font = self._get_font(size=38)
        text = "TM"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(((size - tw) // 2, (size - th) // 2 - 4), text, fill="white", font=font)

        return img

    def _get_font(self, size: int = 40) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Try to load a good monospace font, fall back to default."""
        font_candidates = [
            "consola.ttf",          # Windows Consolas
            "cour.ttf",             # Windows Courier New
            "arial.ttf",            # Windows Arial (fallback)
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
            "/usr/share/fonts/TTF/DejaVuSansMono.ttf",       # Arch
            "DejaVuSansMono.ttf",   # Linux (short name)
            "Courier New.ttf",      # macOS
        ]
        for font_name in font_candidates:
            try:
                return ImageFont.truetype(font_name, size)
            except (OSError, IOError):
                continue

        # Absolute fallback
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()


verification_service = VerificationService()
