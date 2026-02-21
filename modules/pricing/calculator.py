"""
Pricing Module - Calculator
=============================
Metal bar price calculation: raw metal + wage + tax on wage.
Supports gold, silver, and any future precious metal via base_purity param.
"""

from decimal import Decimal, ROUND_FLOOR


def calculate_bar_price(
    weight,
    purity,
    wage_percent,
    base_metal_price,
    tax_percent=10,
    base_purity=750,
) -> dict:
    """
    Calculate metal bar price breakdown.

    Formula:
        raw_metal = weight × (purity / base_purity) × base_metal_price
        wage      = raw_metal × (wage% / 100)
        tax       = wage × (tax% / 100)
        total     = raw_metal + wage + tax

    Args:
        weight: Weight in grams (e.g., 1.000)
        purity: Purity in parts per thousand (e.g., 750 for 18K gold, 999 for pure silver)
        wage_percent: Manufacturing wage as percentage of metal value
        base_metal_price: Current base metal price per gram (Rials)
        tax_percent: VAT percentage (applied only on wage)
        base_purity: Reference purity for the base price (750 for gold 18K, 999 for pure silver)

    Returns:
        dict with: raw_gold, wage, tax, total, audit
    """
    D = lambda x: Decimal(str(x)) if x is not None else Decimal("0")

    d_weight = D(weight).quantize(Decimal("0.001"), rounding=ROUND_FLOOR)

    if D(purity) <= 0 or D(base_metal_price) <= 0 or d_weight <= 0:
        return {"error": "ورودی نامعتبر: وزن و قیمت باید مثبت باشند.", "total": 0}

    d_purity = D(purity)
    d_wage_pct = D(wage_percent)

    def to_int_rial_floor(x: Decimal) -> int:
        return int(x.quantize(Decimal("1"), rounding=ROUND_FLOOR))

    # قیمت واحد بر اساس عیار
    price_per_gram_raw = (D(base_metal_price) / D(base_purity)) * d_purity
    val_unit_price_int = to_int_rial_floor(price_per_gram_raw)

    # ارزش طلای خام
    val_gold_int = to_int_rial_floor(d_weight * Decimal(val_unit_price_int))

    # اجرت (درصدی از ارزش طلا)
    val_wage_int = to_int_rial_floor(Decimal(val_gold_int) * (d_wage_pct / D(100)))

    # مالیات فقط روی اجرت
    val_tax_int = to_int_rial_floor(Decimal(val_wage_int) * (D(tax_percent) / D(100)))

    total_payable = val_gold_int + val_wage_int + val_tax_int

    return {
        "raw_gold": val_gold_int,
        "wage": val_wage_int,
        "tax": val_tax_int,
        "total": total_payable,
        "audit": {
            "weight_used": d_weight,
            "weight_used_str": str(d_weight),
            "unit_price_used": val_unit_price_int,
            "wage_percent_str": str(d_wage_pct),
            "tax_percent_str": str(D(tax_percent)),
            "rounding": "FLOOR",
        },
    }
