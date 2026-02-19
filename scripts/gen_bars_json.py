"""Generate _private/bars_data.json from old DB dump."""
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OLD_PRODUCT_MAP = {
    1: ("gold-talamala", 0.1), 2: ("gold-talamala", 0.2), 3: ("gold-talamala", 0.5),
    4: ("gold-talamala", 1.0), 5: ("gold-talamala", 2.5), 6: ("gold-talamala", 5.0),
    7: ("gold-talamala", 10.0), 8: ("gold-talamala", 20.0), 9: ("gold-talamala", 31.1),
    10: ("gold-talamala", 50.0), 11: ("gold-talamala", 100.0),
    16: ("gold-investment", 0.1), 17: ("gold-investment", 0.2), 18: ("gold-investment", 0.5),
    19: ("gold-investment", 1.0), 20: ("gold-investment", 2.5), 21: ("gold-investment", 5.0),
    22: ("gold-investment", 10.0), 23: ("gold-investment", 20.0), 24: ("gold-investment", 100.0),
    25: ("gold-investment", 50.0), 26: ("gold-investment", 31.1),
    27: ("silver-talamala", 0.1),
}
SKIP = {12, 13, 14, 15}
CUSTOMER_MAP = {"14": "09122973972", "32": "09111274851"}

dump_path = os.path.join(PROJECT_ROOT, "_private", "old_db_plain.sql")
assigned = {}
sold = []
in_bars = False

with open(dump_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.rstrip("\n")
        if line.startswith("COPY public.bars "):
            in_bars = True
            continue
        if in_bars:
            if line == "\\.":
                break
            parts = line.split("\t")
            pid = int(parts[3]) if parts[3] != "\\N" else None
            if pid is None or pid in SKIP or pid not in OLD_PRODUCT_MAP:
                continue
            serial = parts[1].strip()
            status = parts[2]
            cid = parts[4] if parts[4] != "\\N" else None
            slug, weight = OLD_PRODUCT_MAP[pid]
            key = f"{slug}|{weight}"
            if status == "Sold" and cid and cid in CUSTOMER_MAP:
                sold.append({
                    "serial": serial,
                    "type": slug,
                    "weight": weight,
                    "customer_mobile": CUSTOMER_MAP[cid],
                })
            else:
                assigned.setdefault(key, []).append(serial)

assigned_sorted = {k: sorted(v) for k in sorted(assigned.keys()) for k, v in [(k, assigned[k])]}

data = {
    "assigned": assigned_sorted,
    "sold": sold,
    "customers": {
        "09122973972": {"first_name": "User", "last_name": "New", "national_id": "0072349743"},
        "09111274851": {"first_name": "User", "last_name": "Guest", "national_id": "GUEST_f1f7e107_09111274851"},
    },
}

out_path = os.path.join(PROJECT_ROOT, "_private", "bars_data.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

total_assigned = sum(len(v) for v in assigned_sorted.values())
print(f"bars_data.json created:")
print(f"  Assigned bars: {total_assigned}")
print(f"  Sold bars: {len(sold)}")
print(f"  Product groups: {len(assigned_sorted)}")
for k, v in assigned_sorted.items():
    print(f"    {k}: {len(v)}")
