"""
Pricing Module - Calculator
=============================
Gold jewelry price calculation with full audit trail.
Exact formula from TalaMala v2, refactored into clean module.
"""

from decimal import Decimal, ROUND_FLOOR


def calculate_jewelry_price(
    weight,
    purity,
    wage,
    is_wage_percent,
    profit_percent=7,
    commission_percent=0,
    stone_price=0,
    accessory_cost=0,
    accessory_profit_percent=0,
    base_gold_price_18k=0,
    tax_percent=10,
) -> dict:
    """
    Calculate full jewelry price breakdown.

    Args:
        weight: Weight in grams (e.g., 1.000)
        purity: Purity in parts per thousand (e.g., 750 = 18K)
        wage: Manufacturing wage (percent or rial per gram)
        is_wage_percent: If True, wage is percentage of gold value
        profit_percent: Profit margin percentage
        commission_percent: Commission percentage
        stone_price: Stone price in Rials
        accessory_cost: Accessory cost in Rials
        accessory_profit_percent: Profit on accessories
        base_gold_price_18k: Current 18K gold price per gram (Rials)
        tax_percent: VAT percentage

    Returns:
        dict with: raw_gold, wage, profit, commission, stone, accessory, tax, total, audit
    """
    D = lambda x: Decimal(str(x)) if x is not None else Decimal("0")

    # وزن تا سه رقم اعشار (به پایین)
    d_weight = D(weight).quantize(Decimal("0.001"), rounding=ROUND_FLOOR)

    # Guards
    if D(purity) <= 0 or D(base_gold_price_18k) <= 0 or d_weight <= 0:
        return {"error": "ورودی نامعتبر: وزن و قیمت باید مثبت باشند.", "total": 0}

    d_purity = D(purity)
    d_wage = D(wage)
    d_stone = D(stone_price)

    def to_int_rial_floor(x: Decimal) -> int:
        return int(x.quantize(Decimal("1"), rounding=ROUND_FLOOR))

    # قیمت واحد بر اساس عیار
    price_per_gram_raw = (D(base_gold_price_18k) / D(750)) * d_purity
    val_unit_price_int = to_int_rial_floor(price_per_gram_raw)

    # ارزش طلای خام
    val_gold_int = to_int_rial_floor(d_weight * Decimal(val_unit_price_int))

    val_stone_int = to_int_rial_floor(d_stone)
    val_exempt_total_int = val_gold_int + val_stone_int

    # اجرت
    if is_wage_percent:
        wage_decimal = Decimal(val_gold_int) * (d_wage / D(100))
    else:
        wage_decimal = d_weight * d_wage
    val_wage_int = to_int_rial_floor(wage_decimal)

    base_for_margins_int = val_gold_int + val_wage_int

    val_profit_int = to_int_rial_floor(Decimal(base_for_margins_int) * (D(profit_percent) / D(100)))
    val_comm_int = to_int_rial_floor(Decimal(base_for_margins_int) * (D(commission_percent) / D(100)))

    # اکسسوری
    acc_sale_decimal = D(accessory_cost) * (D(1) + (D(accessory_profit_percent) / D(100)))
    val_acc_int = to_int_rial_floor(acc_sale_decimal)

    taxable_services_base = val_wage_int + val_profit_int + val_comm_int
    taxable_goods_base = val_acc_int
    total_taxable_base = taxable_services_base + taxable_goods_base

    # مالیات
    val_tax_int = to_int_rial_floor(Decimal(total_taxable_base) * (D(tax_percent) / D(100)))

    total_payable = (
        val_gold_int + val_wage_int + val_profit_int + val_comm_int
        + val_stone_int + val_acc_int + val_tax_int
    )

    return {
        "raw_gold": val_gold_int,
        "wage": val_wage_int,
        "profit": val_profit_int,
        "commission": val_comm_int,
        "stone": val_stone_int,
        "accessory": val_acc_int,
        "tax": val_tax_int,
        "total": total_payable,
        "audit": {
            "weight_used": d_weight,
            "weight_used_str": str(d_weight),
            "unit_price_used": val_unit_price_int,
            "exempt_principal_amount": val_exempt_total_int,
            "taxable_services_base": taxable_services_base,
            "taxable_goods_base": taxable_goods_base,
            "tax_percent_str": str(D(tax_percent)),
            "profit_percent_str": str(D(profit_percent)),
            "comm_percent_str": str(D(commission_percent)),
            "wage_is_percent": bool(is_wage_percent),
            "rounding": "FLOOR",
        },
    }
