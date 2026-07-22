"""
TalaMala v4 - File Upload Utilities
=====================================
Centralized image upload, validation, and optimization.
"""

import os
import shutil
import uuid
from typing import Optional, Tuple

from fastapi import UploadFile, HTTPException
from PIL import Image

from config.settings import (
    UPLOAD_DIR, ALLOWED_IMAGE_EXTENSIONS, MAX_FILE_SIZE, DEFAULT_IMAGE_MAX_SIZE,
    PRIVATE_UPLOAD_DIR, ALLOWED_DOCUMENT_EXTENSIONS,
)


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


def save_document_file(upload_file: UploadFile, subfolder: str = "") -> Optional[str]:
    """
    Save an uploaded document (PDF or scan) to the private upload dir.

    Unlike save_upload_file() this accepts PDFs and stores the file outside
    static/, so it is only reachable through an authenticated route.

    Returns the relative path, or None if no file was uploaded.
    """
    if not upload_file or not upload_file.filename:
        return None

    upload_file.file.seek(0, 2)
    file_size = upload_file.file.tell()
    upload_file.file.seek(0)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(413, f"حجم فایل بیش از حد مجاز است (حداکثر {MAX_FILE_SIZE // (1024*1024)} مگابایت)")

    ext = os.path.splitext(upload_file.filename)[1].lower()
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(400, f"فرمت فایل غیرمجاز است. فرمت‌های مجاز: {', '.join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))}")

    target_dir = os.path.join(PRIVATE_UPLOAD_DIR, subfolder) if subfolder else PRIVATE_UPLOAD_DIR
    os.makedirs(target_dir, exist_ok=True)

    file_path = os.path.join(target_dir, f"{uuid.uuid4().hex}{ext}")
    try:
        with open(file_path, "wb") as out:
            shutil.copyfileobj(upload_file.file, out)
        return file_path.replace("\\", "/")
    except Exception as e:
        print(f"Document Save Error: {e}")
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
