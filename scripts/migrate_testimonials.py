"""
Migration: Create testimonials table + uploads directory
Run on server: python scripts/migrate_testimonials.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import engine
from sqlalchemy import text

SQL = """
CREATE TABLE IF NOT EXISTS testimonials (
    id SERIAL PRIMARY KEY,
    person_name VARCHAR(200) NOT NULL,
    person_title VARCHAR(300) NOT NULL,
    body TEXT NOT NULL,
    avatar_path VARCHAR(500),
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

def main():
    with engine.begin() as conn:
        conn.execute(text(SQL))
    print("[OK] testimonials table created.")

    upload_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "static", "uploads", "testimonials",
    )
    os.makedirs(upload_dir, exist_ok=True)
    print(f"[OK] upload dir: {upload_dir}")

if __name__ == "__main__":
    main()
