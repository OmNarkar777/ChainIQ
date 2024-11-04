"""
Synthetic retail supply chain dataset generator.
Produces 12 months of daily sales data for 50 SKUs with:
  - Weekly seasonality (weekend peaks)
  - Monthly seasonality
  - Promotional spikes (+40-80%)
  - Holiday effects (Christmas, Diwali, New Year)
  - High-variance SKUs (fashion) vs stable SKUs (staples)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date, timedelta
import os

SEED = 42
rng = np.random.default_rng(SEED)

CATEGORIES = {
    "Electronics":  {"n": 8,  "base_demand": (15, 50),  "variance": "high",   "price_range": (500, 5000)},
    "Apparel":      {"n": 12, "base_demand": (20, 80),  "variance": "high",   "price_range": (300, 3000)},
    "Grocery":      {"n": 10, "base_demand": (50, 200), "variance": "low",    "price_range": (20, 500)},
    "HomeDecor":    {"n": 8,  "base_demand": (10, 40),  "variance": "medium", "price_range": (200, 2000)},
    "Sports":       {"n": 7,  "base_demand": (15, 60),  "variance": "medium", "price_range": (100, 3000)},
    "Toys":         {"n": 5,  "base_demand": (10, 45),  "variance": "high",   "price_range": (150, 1500)},
}

SUPPLIERS = [f"SUP_{i:03d}" for i in range(1, 11)]

HOLIDAYS_2023 = {
    date(2023, 1, 1):  ("New Year",     1.5),
    date(2023, 1, 26): ("Republic Day", 1.2),
    date(2023, 3, 8):  ("Holi",         1.3),
    date(2023, 8, 15): ("Independence", 1.25),
    date(2023, 10, 24):("Diwali",       2.0),
    date(2023, 10, 25):("Diwali",       2.2),
    date(2023, 10, 26):("Diwali",       1.8),
    date(2023, 12, 24):("Christmas Eve",1.4),
    date(2023, 12, 25):("Christmas",    1.6),
    date(2023, 12, 31):("New Year Eve", 1.3),
}


def _weekly_factor(dow: int) -> float:
    """Weekend demand is ~30-40% higher."""
    factors = [0.85, 0.88, 0.90, 0.92, 1.05, 1.30, 1.35]
    return factors[dow]


def _monthly_factor(month: int) -> float:
    factors = [0.85, 0.80, 0.90, 0.88, 0.92, 0.88,
               0.90, 0.95, 1.00, 1.15, 1.30, 1.50]
    return factors[month - 1]


def _noise(variance: str) -> float:
    scale = {"low": 0.08, "medium": 0.18, "high": 0.35}[variance]
    return rng.normal(1.0, scale)


def generate_skus() -> pd.DataFrame:
    skus = []
    sku_num = 1
    for cat, cfg in CATEGORIES.items():
        for _ in range(cfg["n"]):
            base = rng.integers(*cfg["base_demand"])
            price = rng.integers(*cfg["price_range"])
            lead  = int(rng.integers(3, 21))
            safety = int(base * rng.uniform(0.5, 1.5))
            reorder = int(base * lead * rng.uniform(0.8, 1.2))
            skus.append({
                "sku_id":        f"SKU_{sku_num:04d}",
                "sku_name":      f"{cat}_{sku_num:04d}",
                "category":      cat,
                "base_demand":   base,
                "variance":      cfg["variance"],
                "unit_price":    float(price),
                "unit_cost":     float(round(price * rng.uniform(0.4, 0.65), 2)),
                "lead_time_days":lead,
                "reorder_point": reorder,
                "safety_stock":  safety,
                "supplier_id":   rng.choice(SUPPLIERS),
            })
            sku_num += 1
    return pd.DataFrame(skus)


def generate_sales(skus_df: pd.DataFrame) -> pd.DataFrame:
    start = date(2023, 1, 1)
    end   = date(2023, 12, 31)
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]

    # ~15% of days are promotional for each SKU
    records = []
    for _, sku in skus_df.iterrows():
        promo_days = set(rng.choice(len(dates), size=int(len(dates) * 0.15), replace=False))
        stock = float(sku["reorder_point"] * 3)

        for idx, d in enumerate(dates):
            base = sku["base_demand"]
            wf   = _weekly_factor(d.weekday())
            mf   = _monthly_factor(d.month)
            nf   = _noise(sku["variance"])
            is_promo   = idx in promo_days
            promo_mult = rng.uniform(1.4, 1.8) if is_promo else 1.0
            hol_mult   = HOLIDAYS_2023.get(d, (None, 1.0))[1]
            is_holiday = d in HOLIDAYS_2023

            units = max(0, base * wf * mf * nf * promo_mult * hol_mult)
            units = round(units)
            stock = max(0, stock - units)

            # Restock when below reorder point
            if stock < sku["reorder_point"]:
                stock += float(sku["base_demand"] * sku["lead_time_days"] * 1.5)

            records.append({
                "date":             d.isoformat(),
                "sku_id":          sku["sku_id"],
                "sku_name":        sku["sku_name"],
                "category":        sku["category"],
                "units_sold":      units,
                "unit_price":      sku["unit_price"],
                "stock_level":     round(stock, 1),
                "reorder_point":   sku["reorder_point"],
                "lead_time_days":  sku["lead_time_days"],
                "supplier_id":     sku["supplier_id"],
                "promotional_flag":int(is_promo),
                "holiday_flag":    int(is_holiday),
            })

    return pd.DataFrame(records)


def generate_supplier_docs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    docs = {
        "supplier_SUP_001.txt": """
SUPPLIER PROFILE: SUP_001 — Apex Electronics Ltd
=========================================================
Lead Time: 7-10 business days (standard), 3-4 days (express, +15% surcharge)
Minimum Order Quantity (MOQ): 50 units per SKU
Reliability Score: 94/100
On-Time Delivery Rate: 96.2% (last 12 months)
Payment Terms: Net-30
Capacity Notes: Can handle peak demand surge up to 200% with 5-day notice.
Preferred Categories: Electronics, Gadgets
Discount Tiers: 5% at 200 units, 10% at 500 units, 15% at 1000 units
Returns Policy: Accepts returns within 14 days for defective units only.
Notes: Preferred partner for Q4 electronics surge. Book capacity by October 1.
""",
        "supplier_SUP_002.txt": """
SUPPLIER PROFILE: SUP_002 — FashionForward Apparel
=========================================================
Lead Time: 14-21 days (standard), 7 days (express, +25% surcharge)
MOQ: 100 units per style/colorway
Reliability Score: 78/100
On-Time Delivery Rate: 81.5% — NOTE: Frequent delays during festival season
Payment Terms: 50% advance, 50% on delivery
Capacity Notes: Seasonal constraints Oct-Dec. Place orders by Sep 15 for Diwali.
Preferred Categories: Apparel, Accessories
Discount Tiers: 8% at 300 units, 12% at 600 units
Returns Policy: No returns on custom/seasonal items.
Notes: High-variance supplier. Always maintain 3-week safety stock buffer.
""",
        "supplier_SUP_003.txt": """
SUPPLIER PROFILE: SUP_003 — FreshMart FMCG Distributors
=========================================================
Lead Time: 2-3 business days (regional warehouse), 5-7 days (national)
MOQ: 24 units per SKU (case packs)
Reliability Score: 97/100
On-Time Delivery Rate: 98.7% — Most reliable supplier in portfolio
Payment Terms: Net-45
Capacity Notes: No surge limitations. 24/7 emergency order line available.
Preferred Categories: Grocery, FMCG, Personal Care
Discount Tiers: 3% at 100 units, 6% at 500 units, 9% at 1000 units
Returns Policy: Full credit for expired/damaged goods within 30 days.
Notes: Use as default for Grocery SKUs. Can activate emergency replenishment
within 24 hours for critical stockout risk.
""",
        "supplier_SUP_004.txt": """
SUPPLIER PROFILE: SUP_004 — HomeStyle Imports Pvt Ltd
=========================================================
Lead Time: 21-35 days (imported goods), 7-10 days (domestic stock)
MOQ: 30 units per SKU
Reliability Score: 85/100
On-Time Delivery Rate: 88.0%
Payment Terms: LC (Letter of Credit) for imports, Net-30 for domestic
Capacity Notes: Import shipments arrive 1st and 15th of each month.
Preferred Categories: Home Decor, Furniture, Kitchenware
Discount Tiers: 6% at 100 units, 11% at 250 units
Returns Policy: Returns within 7 days of delivery, 20% restocking fee.
Notes: Plan import orders minimum 45 days in advance. Domestic stock limited.
""",
        "supplier_SUP_005.txt": """
SUPPLIER PROFILE: SUP_005 — SportZone Pro Supplies
=========================================================
Lead Time: 5-8 business days
MOQ: 20 units per SKU
Reliability Score: 91/100
On-Time Delivery Rate: 93.4%
Payment Terms: Net-30
Capacity Notes: Cricket/badminton season (Mar-May, Oct-Nov) causes 2-week delays.
Preferred Categories: Sports Equipment, Fitness, Outdoor
Discount Tiers: 4% at 100 units, 9% at 300 units, 14% at 600 units
Returns Policy: 30-day no-questions return for unused items with original packaging.
Notes: Reliable for non-seasonal orders. Build 4-week buffer before cricket season.
"""
    }
    for fname, content in docs.items():
        (out_dir / fname).write_text(content.strip())
    print(f"[generator] Wrote {len(docs)} supplier docs to {out_dir}")


def main():
    out_dir = Path(__file__).parent
    print("[generator] Generating 50 SKUs...")
    skus_df = generate_skus()

    print("[generator] Generating 12 months of daily sales (50 SKUs × 365 days)...")
    sales_df = generate_sales(skus_df)

    csv_path = out_dir / "sample_data.csv"
    sales_df.to_csv(csv_path, index=False)
    print(f"[generator] Saved {len(sales_df):,} rows → {csv_path}")

    doc_dir = out_dir / "supplier_docs"
    generate_supplier_docs(doc_dir)
    print("[generator] Done!")
    return sales_df, skus_df


if __name__ == "__main__":
    main()
