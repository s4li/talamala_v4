"""
TalaMala v4 - File Upload Utilities
=====================================
Centralized image upload, validation, and optimization.
"""

import os
import uuid
from typing import Optional, Tuple

from fastapi import UploadFile, HTTPException
from PIL import Image

from config.settings import UPLOAD_DIR, ALLOWED_IMAGE_EXTENSIONS, MAX_FILE_SIZE, DEFAULT_IMAGE_MAX_SIZE


def save_upload_file(
    upload_file: UploadFile,
    max_size: Tuple[int, int] = DEFAULT_IMAGE_MAX_SIZE,
    subfolder: str = "",
) -> Optional[str]:
    """
    Save an uploaded image file with validation and optimization.

    Args:
        upload_file: The uploaded file from FastAPI
        max_size: Maximum dimensions (width, height) to resize to
        subfolder: Optional subfolder within UPLOAD_DIR

    Returns:
        Relative file path string, or None if upload is empty/invalid
    """
    if not upload_file or not upload_file.filename:
        return None

    # Validate file size
    upload_file.file.seek(0, 2)
    file_size = upload_file.file.tell()
    upload_file.file.seek(0)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(413, f"حجم فایل بیش از حد مجاز است (حداکثر {MAX_FILE_SIZE // (1024*1024)} مگابایت)")

    # Validate extension
    ext = os.path.splitext(upload_file.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(400, f"فرمت فایل غیرمجاز است. فرمت‌های مجاز: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}")

    # Build save path
    target_dir = os.path.join(UPLOAD_DIR, subfolder) if subfolder else UPLOAD_DIR
    os.makedirs(target_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(target_dir, unique_name)

    try:
        img = Image.open(upload_file.file)
        img.thumbnail(max_size)

        if ext in [".jpg", ".jpeg"]:
            img.save(file_path, optimize=True, quality=80)
        else:
            img.save(file_path)

        # Always use forward slashes for URLs
        return file_path.replace("\\", "/")

    except Exception as e:
        print(f"Image Save Error: {e}")
        return None


def delete_file(file_path: str) -> bool:
    """Safely delete a file from disk. Returns True if deleted."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return True
    except OSError:
        pass
    return False
