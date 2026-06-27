"""
Enterprise synthetic retail/manufacturing supply chain dataset.
Generates 12 months of daily sales for 300 SKUs across 9 categories,
10 suppliers, 4 warehouse regions, with:
  - Realistic product names (not "Category_NNNN")
  - Per-SKU inventory buffer strategy (LOW/MEDIUM/HIGH/OVERSTOCK)
  - Weekly + monthly + holiday demand seasonality
  - Promotional spikes
  - Planned purchase orders for high-buffer SKUs
  - 10 detailed supplier profiles for RAG
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date, timedelta

SEED = 42
rng = np.random.default_rng(SEED)

# ── Product catalog ──────────────────────────────────────────────────────────

PRODUCTS = {
    "Electronics": [
        "USB-C Fast Charger 65W", "Screen Protector Tempered 6.7\"",
        "Wireless Earbuds ANC Pro", "Portable Power Bank 20000mAh",
        "Laptop Bag Waterproof 15.6\"", "Bluetooth Speaker 360° Bass",
        "Smart Watch Fitness Band", "HDMI 2.1 Cable 2m",
        "Mechanical Keyboard TKL RGB", "Ergonomic Mouse Wireless",
        "Phone Stand Adjustable Aluminium", "LED Desk Lamp USB-C",
        "Gaming Headset 7.1 Surround", "Laptop Cooling Pad 15.6\"",
        "Webcam 4K Autofocus", "USB Hub 7-Port USB 3.0",
        "Ring Light 10\" Selfie", "Portable SSD 1TB USB-C",
        "Smart Plug 16A WiFi", "Cable Management Kit 20pc",
        "Monitor Light Bar Clamp", "TWS Earphones Ultra ANC",
        "Wireless Charger Pad 15W MagSafe", "Bluetooth Tracker Card",
        "Screen Cleaning Kit Microfibre", "Anti-Blue Light Glasses",
        "Laptop Stand Foldable Aluminium", "Type-C Docking Station 12-in-1",
        "Noise Cancelling USB Mic", "Fiber HDMI Cable 10m",
        "Solar Power Bank 10000mAh", "Tempered Glass Tablet 11\"",
        "Smartwatch Charging Cable Magnetic", "NFC Business Card Smart",
        "LED Strip Light RGB 5m", "Mini Projector 1080p WiFi",
        "Drawing Tablet 10\" Pen", "VR Headset Phone 6DOF",
        "Wireless HDMI Transmitter", "Smart Remote Universal IR",
    ],
    "Apparel": [
        "Men's Classic Polo Cotton XL", "Women's Floral Kurti Rayon M",
        "Men's Slim Fit Jeans 32W", "Women's Palazzo Pants Crepe L",
        "Men's Oxford Formal Shirt 40", "Women's Sports Bra Seamless M",
        "Men's Hooded Sweatshirt Fleece L", "Women's Wrap Midi Dress S",
        "Kids Graphic T-Shirt 4Y", "Men's Chinos Stretch 32W",
        "Women's Denim Shorts Distressed M", "Men's Running Shorts Dri-Fit M",
        "Women's Blazer Structured Black S", "Men's Graphic Oversized Tee L",
        "Women's Ethnic Coord Set M", "Men's Woolen Cable Knit Sweater L",
        "Women's Yoga Leggings High-Waist S", "Men's Cargo Shorts 34W",
        "Women's Party Satin Blouse M", "Unisex Hoodie Oversized Grey L",
        "Men's Track Pants Quick-Dry XL", "Women's Saree Georgette Navy",
        "Men's Linen Resort Shirt XL", "Women's Anarkali Suit Embroidered M",
        "Men's Denim Jacket Raw 42", "Women's Longline Skirt Pleated M",
        "Men's Ethnic Kurta Cotton XL", "Women's Cashmere Turtleneck S",
        "Kids School Uniform Set 10Y", "Men's Swim Shorts Tropical M",
        "Women's Wool Trench Coat S", "Men's Tuxedo Slim Fit 40",
        "Women's Corset Crop Top M", "Unisex Beanie Ribbed Knit",
        "Men's Velvet Blazer Navy 42", "Women's Linen Jumpsuit S",
        "Men's Printed Sarong Beach", "Women's Ruched Mini Dress XS",
        "Men's Arctic Puffer Jacket XL", "Women's Flared High-Waist Jeans 28W",
        "Girls Princess Frock Set 6Y", "Boys Denim Dungarees 8Y",
        "Women's Boho Maxi Dress Cotton M", "Men's Formal Trousers Wool 34W",
        "Women's Tunic Embroidered Top L", "Men's Merino Wool Socks Multipack",
        "Women's Pearl Neck Satin Blouse S", "Men's Vintage Washed Denim 33W",
        "Women's Cropped Utility Jacket M", "Unisex Packable Raincoat XL",
        "Men's V-Neck Merino Sweater M", "Women's Floral Palazzo Crepe L",
        "Men's OCBD Oxford Shirt 38", "Women's Silk Kurti Embellished L",
        "Men's Athletic Compression Shorts S", "Women's Cargo Utility Trousers M",
        "Unisex Sherpa Fleece Pullover L", "Men's Turkish Bathrobe XL",
        "Women's Velvet Blazer Dusty Rose S", "Unisex Compression Travel Socks",
    ],
    "Grocery": [
        "Basmati Rice Premium 5kg", "Sunflower Oil Cold Pressed 2L",
        "Whole Wheat Atta Multigrain 10kg", "Toor Dal Organic 1kg",
        "Refined Sugar Sulphurless 5kg", "Tata Tea Premium Gold 500g",
        "Nescafé Classic Smooth 100g", "Amul Butter Spreadable 500g",
        "Himalayan Pink Salt 1kg", "Haldiram's Aloo Bhujia 400g",
        "Parle-G Original Biscuit 800g", "Maggi 2-Minute Noodles 12pk",
        "Kissan Mixed Fruit Jam 500g", "Nestlé Munch 5pk Assorted",
        "Paper Boat Aamras Mango 1L", "Red Label Tea Dust 250g",
        "Saffola Gold Pro Blended Oil 1L", "MTR Ready Palak Paneer 300g",
        "Fortune Sunlite Refined Oil 5L", "Lijjat Urad Papad Masala 200g",
        "Moong Dal Split Organic 500g", "Masoor Dal Red Lentil 1kg",
        "Urad Dal Whole Black 500g", "Chana Dal Roasted 1kg",
        "Brown Basmati Rice 2kg", "Oats Quaker Old Fashioned 2kg",
        "Cornflakes Kellogg's Original 1kg", "Muesli Almond Cranberry 500g",
        "Dabur Honey Raw 500g", "Amul Desi Ghee 1L",
        "Cold Pressed Coconut Oil 500ml", "Extra Virgin Olive Oil 500ml",
        "Apple Cider Vinegar Organic 500ml", "Turmeric Powder Organic 500g",
        "Kashmiri Red Chilli Powder 500g", "Coriander Cumin Powder 500g",
        "Garam Masala MDH 200g", "Kitchen King Masala MDH 100g",
        "Chole Masala Everest 100g", "Rajma Masala Everest 100g",
        "Bournvita Cocoa Malt Drink 500g", "Complan Royale Nutrition 500g",
        "Horlicks Classic Malt 1kg", "Amul Skimmed Milk Powder 500g",
        "Organic Green Tea 100 Bags", "Chamomile Lavender Tea 50 Bags",
        "Dark Chocolate 70% Cocoa 100g", "Almond Flour Blanched 500g",
        "Chia Seeds Organic 200g", "Flax Seeds Roasted 500g",
    ],
    "HomeDecor": [
        "Bedsheet King Egyptian Cotton 400TC", "Embroidered Pillow Cover Set/2",
        "Bath Towel Set GSM 600 Cotton", "Bohemian Table Runner Jute",
        "Minimalist Ceramic Vase Matte", "Wooden Photo Frame Multi 8x10",
        "Abstract Canvas Wall Art 24x36", "Fairy String Lights Warm 5m",
        "Aromatherapy Essential Oil Diffuser 300ml", "Scented Candle Set/3 Sandalwood",
        "Macramé Boho Wall Hanging Large", "Bamboo Soap Dispenser Pump",
        "Decorative Metal Lantern Moroccan", "Chunky Knit Throw Blanket 50x60",
        "Velvet Cushion Cover Set/4 16x16", "Faux Succulent Terrarium Set/3",
        "Marble Bookend Pair Geometric", "Copper Tealight Holder Geometric",
        "Woven Jute Storage Basket Medium", "Desk Organiser Bamboo Slots",
        "Linen Napkin Set/4 Natural", "Terracotta Planter Artisan 8\"",
        "Round Rattan Mirror Natural 24\"", "Coir Doormat Printed 18x30",
        "Minimalist Wall Clock Nordic 12\"", "Acacia Wood Serving Tray Handles",
        "Waffle Weave Kitchen Towel Set/3", "Washi Night Lamp Paper",
        "Sheer Curtain Panel Blush 54x84", "PEVA Shower Curtain Mildew-Resistant",
    ],
    "Sports": [
        "Yoga Mat Non-Slip Eco 6mm TPE", "Resistance Band Set/5 Fabric",
        "Neoprene Dumbbell 2kg Pair Colour", "PVC Speed Jump Rope Ball Bearing",
        "Football Match Quality Size 5", "Kashmir Willow Cricket Bat",
        "Leather Match Cricket Ball Red", "Carbon Fibre Badminton Racket",
        "Feather Shuttlecock 12pk", "Table Tennis Set 2-Player",
        "Men's Running Shoes Trail 42", "Women's Trail Running Shoes 38",
        "Stainless Sports Water Bottle 1L", "Leather Gym Gloves Medium",
        "Doorframe Pull-Up Bar", "Ab Roller Knee Mat",
        "High-Density Foam Roller 45cm", "Cast Iron Kettlebell 10kg",
        "Pro Boxing Gloves Sparring 12oz", "Heavy Punching Bag 4ft",
        "Mountain Bike Helmet CE L", "Knee Guard Neoprene Pair M",
        "Ankle Support Wrap Neoprene", "Tritan Protein Shaker 700ml",
        "Anti-Fog UV Swim Goggles", "Adjustable Weight Bench Flat/Incline",
        "Resistance Loop Bands Hip Set/4", "Gymnastic Skipping Rope Beaded",
        "Slam Medicine Ball Rubber 5kg", "Calf Compression Sleeves Pair M",
        "Hockey Stick Composite Junior", "Volleyball Indoor Match",
        "Basketball Rubber Outdoor Size 7", "Graphite Tennis Racket 300g",
        "Rugby Ball Match Grade Leather", "Baseball Batting Gloves Leather Pair",
        "Recurve Archery Set 30 Bow", "Ultimate Disc Frisbee 175g",
        "Slackline Balance Line Kit 15m", "Static Kernmantle Rope 10mm×30m",
    ],
    "Beauty": [
        "Neem Tulsi Face Wash Anti-Acne 200ml", "SPF 50+ PA+++ Sunscreen 100ml",
        "Vitamin C Brightening Serum 30ml", "Hyaluronic Acid Gel Moisturizer 50ml",
        "Retinol A Night Recovery Cream 50g", "Rose Water Toner Hydrating 200ml",
        "Activated Charcoal Detox Mask 100ml", "Peptide Under Eye Cream 15ml",
        "Biotin Keratin Shampoo 300ml", "Argan Oil Deep Conditioner 300ml",
        "Keratin Hair Mask Repair 250ml", "Volumizing Dry Shampoo 150ml",
        "100% Pure Coconut Hair Oil 200ml", "Anti-Dandruff Coal Tar Shampoo 400ml",
        "Matte Lipstick Transfer-Proof Nude", "Tinted BB Cream SPF 30 Shade 02",
        "Full Coverage Liquid Foundation Beige", "Volumizing Mascara 3D Lash",
        "Microblading Eyebrow Pencil Dark", "Urban Setting Spray Long-Lasting 100ml",
        "Nail Polish Gel Effect Set/5 Coral", "Oil-Free Makeup Remover Wipes 25pk",
        "Micellar Cleansing Water 400ml", "Shea Butter Body Lotion 400ml",
        "Healing Hand Cream SPF 15 100ml", "Cracked Heel Repair Foot Cream 100g",
        "Antiperspirant Deodorant Stick Men 75g", "Floral EDP Perfume Women 50ml",
        "Soothing Aloe Vera Gel 200ml", "2% Salicylic Acid BHA Toner 200ml",
    ],
    "Toys": [
        "LEGO Classic Creative Bricks 500pc", "1:18 Remote Control Off-Road Car",
        "Barbie Dreamhouse Fashion Set", "Hot Wheels Track Builder System",
        "Monopoly Classic Strategy Board Game", "Scrabble Family Word Game",
        "Rubik's Cube Speed 3x3 Original", "Jigsaw Puzzle 1000pc World Map",
        "Play-Doh Rainbow Starter Kit 10pc", "Super Soaker Water Gun 1L",
        "Math Flash Cards Educational Set", "Wooden Building Blocks 50pc",
        "Telescope Refractor Kids 70mm", "Kids Microscope 3-Level 100-300x",
        "STEM Science Experiment Kit 8+", "Art & Craft Mega Activity Kit",
        "Uno Classic Card Game Family", "Tournament Chess Set Weighted Wooden",
        "Nerf Rival High-Impact Round Blaster", "Kinetic Play Sand 2kg",
    ],
    "Automotive": [
        "Car Air Freshener Gel Ocean 80g", "Magnetic Dashboard Phone Holder",
        "Tyre Inflator Compressor 150PSI", "PU Leather Car Seat Cover Full Set",
        "Leather Steering Wheel Cover 38cm", "Portable Car Vacuum 120W Wet-Dry",
        "Dash Cam 4K WiFi GPS Loop Record", "Reverse Parking Sensor Kit 4-sensor",
        "Jump Starter 2000A 12V Portable", "Boot Organiser Trunk Storage Bag",
        "Foldable Windshield Sunshade", "Waterproof Dog Cargo Cover Seat",
        "Car Wash Kit Foam Cannon 10pc", "LED Interior Ambient Light Strip 4m",
        "Panoramic Wide Angle Rear Mirror",
    ],
    "Books": [
        "Dotted Notebook A5 Hardcover 200pg", "Bullet Journal A5 Premium Kraft",
        "Precision Rollerball Pen Set 5pk", "Dual-Tip Highlighter Set 6-Color",
        "Sticky Notes Neon Rainbow 6pk 75×75", "Weekly Desk Planner Undated Spiral",
        "Sketch Book A4 Cold Press 100pg", "Professional Watercolor Set 36",
        "Calligraphy Broad Nib Pen Set 8pk", "Origami Premium Paper 200-Sheet",
        "Accounts Financial Ledger A4", "Index Cards 4×6 Oxford Ruled 200pk",
        "Dry Erase Board Marker Set 8pk", "Correction Pen Fluid 12ml Smooth",
        "Ring Binder A4 4-Ring D 75mm",
    ],
}

# Supplier config: name, lead_time_range, moq, reliability, categories
SUPPLIER_CONFIG = {
    "SUP_001": {
        "name":        "Apex Electronics Ltd",
        "lead_range":  (5, 10),
        "moq":         50,
        "reliability": 0.94,
        "categories":  ["Electronics"],
    },
    "SUP_002": {
        "name":        "FashionForward Apparel Co",
        "lead_range":  (14, 21),
        "moq":         100,
        "reliability": 0.78,
        "categories":  ["Apparel"],
    },
    "SUP_003": {
        "name":        "FreshMart FMCG Distributors",
        "lead_range":  (2, 4),
        "moq":         24,
        "reliability": 0.97,
        "categories":  ["Grocery"],
    },
    "SUP_004": {
        "name":        "HomeStyle Imports Pvt Ltd",
        "lead_range":  (18, 35),
        "moq":         30,
        "reliability": 0.85,
        "categories":  ["HomeDecor"],
    },
    "SUP_005": {
        "name":        "SportZone Pro Supplies",
        "lead_range":  (5, 8),
        "moq":         20,
        "reliability": 0.91,
        "categories":  ["Sports"],
    },
    "SUP_006": {
        "name":        "TechGlobal Asia Pacific",
        "lead_range":  (18, 28),
        "moq":         100,
        "reliability": 0.82,
        "categories":  ["Electronics"],
    },
    "SUP_007": {
        "name":        "GlowBeauty Brands India",
        "lead_range":  (7, 12),
        "moq":         48,
        "reliability": 0.93,
        "categories":  ["Beauty"],
    },
    "SUP_008": {
        "name":        "PlayWorld Toys & Games",
        "lead_range":  (10, 18),
        "moq":         36,
        "reliability": 0.88,
        "categories":  ["Toys"],
    },
    "SUP_009": {
        "name":        "AutoParts Express India",
        "lead_range":  (3, 7),
        "moq":         10,
        "reliability": 0.95,
        "categories":  ["Automotive"],
    },
    "SUP_010": {
        "name":        "KnowledgeHub Stationery",
        "lead_range":  (5, 10),
        "moq":         25,
        "reliability": 0.96,
        "categories":  ["Books"],
    },
}

WAREHOUSES = ["WH_NORTH", "WH_SOUTH", "WH_WEST", "WH_EAST"]

CATEGORY_CONFIG = {
    "Electronics": {"base_demand": (8, 35),   "variance": "high",   "price_range": (400, 4500),  "suppliers": ["SUP_001", "SUP_006"]},
    "Apparel":     {"base_demand": (15, 70),  "variance": "high",   "price_range": (250, 3500),  "suppliers": ["SUP_002"]},
    "Grocery":     {"base_demand": (40, 180), "variance": "low",    "price_range": (15, 600),    "suppliers": ["SUP_003"]},
    "HomeDecor":   {"base_demand": (8, 35),   "variance": "medium", "price_range": (150, 2500),  "suppliers": ["SUP_004"]},
    "Sports":      {"base_demand": (10, 50),  "variance": "medium", "price_range": (80, 4000),   "suppliers": ["SUP_005"]},
    "Beauty":      {"base_demand": (20, 90),  "variance": "medium", "price_range": (100, 1500),  "suppliers": ["SUP_007"]},
    "Toys":        {"base_demand": (8, 40),   "variance": "high",   "price_range": (120, 3500),  "suppliers": ["SUP_008"]},
    "Automotive":  {"base_demand": (5, 25),   "variance": "medium", "price_range": (200, 3000),  "suppliers": ["SUP_009"]},
    "Books":       {"base_demand": (15, 60),  "variance": "low",    "price_range": (80, 800),    "suppliers": ["SUP_010"]},
}

# Buffer strategies: fraction of SKUs and resulting inventory multiplier at restock
BUFFER_STRATEGIES = {
    "lean":       {"weight": 0.30, "restock_mult": 1.5},
    "standard":   {"weight": 0.30, "restock_mult": 2.5},
    "conservative":{"weight": 0.25, "restock_mult": 4.0},
    "overstock":  {"weight": 0.15, "restock_mult": 7.0},
}

HOLIDAYS_2023 = {
    date(2023, 1, 1):   1.50,  # New Year
    date(2023, 1, 26):  1.20,  # Republic Day
    date(2023, 3, 8):   1.30,  # Holi
    date(2023, 8, 15):  1.25,  # Independence Day
    date(2023, 10, 24): 2.00,  # Diwali
    date(2023, 10, 25): 2.20,  # Diwali (peak)
    date(2023, 10, 26): 1.80,  # Diwali
    date(2023, 11, 26): 1.60,  # Cyber Monday equiv
    date(2023, 12, 24): 1.40,  # Christmas Eve
    date(2023, 12, 25): 1.60,  # Christmas
    date(2023, 12, 31): 1.30,  # New Year Eve
}

WEEKLY_FACTORS  = [0.85, 0.88, 0.90, 0.92, 1.05, 1.30, 1.35]
MONTHLY_FACTORS = [0.85, 0.80, 0.90, 0.88, 0.92, 0.88, 0.90, 0.95, 1.00, 1.15, 1.30, 1.50]

NOISE_SCALE = {"low": 0.08, "medium": 0.18, "high": 0.35}


def _assign_buffer(idx: int) -> str:
    """Deterministically assign a buffer strategy based on SKU index."""
    r = (idx * 7919 + 42) % 100
    if r < 30:   return "lean"
    if r < 60:   return "standard"
    if r < 85:   return "conservative"
    return "overstock"


def generate_skus() -> pd.DataFrame:
    rows = []
    sku_num = 1
    for cat, cfg in CATEGORY_CONFIG.items():
        products = PRODUCTS[cat]
        for i, name in enumerate(products):
            base    = int(rng.integers(*cfg["base_demand"]))
            price   = float(rng.integers(*cfg["price_range"]))
            cost    = round(price * float(rng.uniform(0.40, 0.62)), 2)
            lead    = int(rng.integers(*SUPPLIER_CONFIG[cfg["suppliers"][0]]["lead_range"]))
            safety  = int(base * float(rng.uniform(0.5, 1.5)))
            rop     = int(base * lead * float(rng.uniform(0.8, 1.2)))
            sup_id  = str(rng.choice(cfg["suppliers"]))
            wh      = str(rng.choice(WAREHOUSES))
            buf     = _assign_buffer(sku_num)

            rows.append({
                "sku_id":         f"SKU_{sku_num:04d}",
                "sku_name":       name,
                "category":       cat,
                "supplier_id":    sup_id,
                "warehouse_id":   wh,
                "base_demand":    base,
                "variance":       cfg["variance"],
                "unit_price":     price,
                "unit_cost":      cost,
                "lead_time_days": lead,
                "reorder_point":  rop,
                "safety_stock":   safety,
                "buffer_strategy":buf,
            })
            sku_num += 1

    return pd.DataFrame(rows)


def generate_sales(skus_df: pd.DataFrame) -> pd.DataFrame:
    start = date(2023, 1, 1)
    end   = date(2023, 12, 31)
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]

    records = []
    for _, sku in skus_df.iterrows():
        buf    = sku["buffer_strategy"]
        rmult  = BUFFER_STRATEGIES[buf]["restock_mult"]
        nscale = NOISE_SCALE[sku["variance"]]

        # Promo days: 15% of year, random per SKU
        promo_days = set(rng.choice(len(dates), size=int(len(dates) * 0.15), replace=False))

        # Planned big purchase order (PO) dates: overstock/conservative SKUs get POs
        po_dates: set[int] = set()
        if buf in ("conservative", "overstock"):
            n_pos = 3 if buf == "overstock" else 2
            po_dates = set(rng.choice(len(dates), size=n_pos, replace=False))

        stock = float(sku["reorder_point"] * rmult * 2)  # initial stock

        for idx, d in enumerate(dates):
            wf      = WEEKLY_FACTORS[d.weekday()]
            mf      = MONTHLY_FACTORS[d.month - 1]
            nf      = max(0.1, float(rng.normal(1.0, nscale)))
            promo_f = float(rng.uniform(1.40, 1.80)) if idx in promo_days else 1.0
            hol_f   = HOLIDAYS_2023.get(d, 1.0)

            units = max(0.0, sku["base_demand"] * wf * mf * nf * promo_f * hol_f)
            units = round(units)
            stock = max(0.0, stock - units)

            # Planned purchase order arrival
            if idx in po_dates:
                stock += float(sku["base_demand"] * sku["lead_time_days"] * rmult * 2)

            # Auto reorder when below ROP
            if stock < sku["reorder_point"]:
                stock += float(sku["base_demand"] * sku["lead_time_days"] * rmult)

            records.append({
                "date":              d.isoformat(),
                "sku_id":            sku["sku_id"],
                "sku_name":          sku["sku_name"],
                "category":          sku["category"],
                "supplier_id":       sku["supplier_id"],
                "warehouse_id":      sku["warehouse_id"],
                "units_sold":        units,
                "unit_price":        sku["unit_price"],
                "unit_cost":         sku["unit_cost"],
                "stock_level":       round(stock, 1),
                "reorder_point":     sku["reorder_point"],
                "lead_time_days":    sku["lead_time_days"],
                "promotional_flag":  int(idx in promo_days),
                "holiday_flag":      int(d in HOLIDAYS_2023),
            })

    return pd.DataFrame(records)


def generate_supplier_docs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    docs = {
        "supplier_SUP_001.txt": """
SUPPLIER PROFILE: SUP_001 — Apex Electronics Ltd
====================================================
OVERVIEW
Apex Electronics Ltd is a domestic supplier specialising in consumer electronics accessories,
cables, charging solutions, and smart devices. Headquartered in Shenzhen operations with a
Mumbai fulfilment hub, Apex is our primary supplier for the Electronics category.

OPERATIONAL METRICS
Lead Time: 5-10 business days (standard) | 2-3 days (express, +18% surcharge)
Minimum Order Quantity (MOQ): 50 units per SKU
On-Time Delivery Rate: 96.2% (trailing 12 months)
Order Fill Rate: 98.4%
Average Transit Time (last-mile): 1.2 days
Defect Rate: 0.8% (industry benchmark: 2.1%)

FINANCIAL TERMS
Payment Terms: Net-30
Credit Limit: ₹25 Lakhs
Discount Tiers: 5% at 200 units | 10% at 500 units | 15% at 1,000 units | 18% at 2,500 units
Penalty Clause: 2% invoice value per week of delay beyond agreed lead time (capped at 10%)

CAPACITY
Standard capacity: up to 5,000 units/month per SKU
Surge capacity: up to 200% with 5 business days' advance notice
Q4 capacity reservation window: September 1–October 15 annually

RISK ASSESSMENT
Risk Level: LOW
Key Risks: Slight price volatility for OLED/AMOLED components (±8% quarterly)
Contingency: Dual-sourced with SUP_006 (TechGlobal Asia) for 12 flagship SKUs
Insurance: Cargo insurance included up to ₹50 Lakhs per shipment

COMPLIANCE
ISO 9001:2015 certified | BIS-approved for 23 product lines | ROHS compliant
""",
        "supplier_SUP_002.txt": """
SUPPLIER PROFILE: SUP_002 — FashionForward Apparel Co
======================================================
OVERVIEW
FashionForward Apparel Co is our primary apparel supplier, managing fast-fashion lines,
ethnic wear, and performance sportswear. Based in Tirupur (knitwear hub) with seasonal
production overflow to Surat and Jaipur units.

OPERATIONAL METRICS
Lead Time: 14-21 days (standard) | 7 days (express, +25% surcharge)
MOQ: 100 units per style/colorway/size run
On-Time Delivery Rate: 81.5% — BELOW portfolio average of 91.2%
Delay Pattern: Frequent 7-14 day slippages during Diwali (Oct) and Christmas (Dec) seasons
Order Fill Rate: 84.1% (sizes frequently out-of-stock at source)
Defect Rate: 3.2% (above benchmark; QC inspection recommended on delivery)

FINANCIAL TERMS
Payment Terms: 50% advance on purchase order, 50% on delivery
Penalty Clause: 1.5% per week (but historically waived due to relationship)
Discount Tiers: 8% at 300 units | 12% at 600 units | 15% at 1,200 units

SEASONAL CONSTRAINTS — CRITICAL
RISK WINDOW: October–December. Production units at 110% capacity from Sept 20.
RECOMMENDATION: Place Diwali orders by September 10; Christmas orders by October 20.
Orders placed after these dates carry HIGH risk of 3-week delay.
Build 3-week safety stock buffer for ALL FashionForward SKUs entering Q4.

RISK ASSESSMENT
Risk Level: HIGH
Key Risks: Seasonal capacity crunch, size-availability inconsistency, advance payment exposure
Mitigation: Maintain 21-day safety stock from August onward; secondary sourcing from local
boutique manufacturers for emergency fills at +30% cost premium.
""",
        "supplier_SUP_003.txt": """
SUPPLIER PROFILE: SUP_003 — FreshMart FMCG Distributors
=========================================================
OVERVIEW
FreshMart FMCG Distributors is our highest-reliability supplier and the backbone of the
Grocery category. Operating from 6 regional distribution centres (Delhi, Mumbai, Bangalore,
Hyderabad, Chennai, Kolkata), FreshMart achieves industry-best lead times and fill rates.

OPERATIONAL METRICS
Lead Time: 2-4 business days (regional DC) | 5-7 days (inter-region transfers)
MOQ: 24 units per SKU (standard case pack)
On-Time Delivery Rate: 98.7% — Highest in our supplier portfolio
Order Fill Rate: 99.1%
Average Transit Time: 18 hours (regional), 42 hours (inter-region)
Defect/Damage Rate: 0.3% (industry benchmark: 1.8%)
Cold-chain capability: Yes (for perishable/dairy adjacents)

FINANCIAL TERMS
Payment Terms: Net-45 (extended from industry-standard Net-30 as goodwill credit)
Discount Tiers: 3% at 100 units | 6% at 500 units | 9% at 1,000 units | 11% at 2,500 units
Volume Rebate: Additional 2% annual rebate if annual spend exceeds ₹2 Crores

EMERGENCY SERVICES
24/7 Emergency Replenishment Line: Available for CRITICAL stockout situations
Emergency Lead Time: As fast as 6 hours (same-city DC) | 24 hours (inter-city)
Emergency Surcharge: +12% on standard invoice

RISK ASSESSMENT
Risk Level: VERY LOW
Key Risks: None material. Minor supply tightness on imported goods (coconut oil, olive oil)
during monsoon (July–September)
Recommendation: DEFAULT supplier for all Grocery SKUs. First call for emergency restocking.
""",
        "supplier_SUP_004.txt": """
SUPPLIER PROFILE: SUP_004 — HomeStyle Imports Pvt Ltd
======================================================
OVERVIEW
HomeStyle Imports Pvt Ltd manages home décor, soft furnishings, and lifestyle accessories,
sourcing from India, Indonesia, and Morocco. Shipments arrive via sea freight at JNPT (Mumbai)
and ICD Tughlakabad (Delhi).

OPERATIONAL METRICS
Lead Time (Imported): 21-35 calendar days (subject to customs clearance, typically 3-5 days)
Lead Time (Domestic stock): 7-10 business days from Mumbai warehouse
MOQ: 30 units per SKU (imported) | 15 units (domestic stock)
On-Time Delivery Rate: 88.0% (delays mainly at customs, 6-12 day buffer recommended)
Order Fill Rate: 91.3%
Defect Rate: 2.1% (primarily packaging damage in transit; original packaging rarely survives)

FINANCIAL TERMS
Payment Terms: LC (Letter of Credit) for imports — open 45 days before shipment
Domestic stock: Net-30
Import Duty Responsibility: Supplier handles all customs clearance; duties included in pricing
Penalty Clause: 3% per week for domestic, NOT applicable for imported goods (force majeure)
Discount Tiers: 6% at 100 units | 11% at 250 units | 16% at 500 units

SHIPMENT SCHEDULE
Sea freight arrives 1st and 15th of each month (Mumbai port)
Air freight available on request (+45% surcharge, 4-7 day lead time)

RISK ASSESSMENT
Risk Level: MEDIUM-HIGH for imports, MEDIUM for domestic
Key Risks: Customs delays (historical avg +8 days during festive pre-season Aug–Oct),
INR/USD fluctuation adds ±5% to import cost quarterly, port congestion during Q4
RECOMMENDATION: Place import orders minimum 50 days in advance for Q4 SKUs.
Maintain 4-week domestic safety stock for all HomeDecor lines.
""",
        "supplier_SUP_005.txt": """
SUPPLIER PROFILE: SUP_005 — SportZone Pro Supplies
===================================================
OVERVIEW
SportZone Pro is our exclusive Sports & Fitness supplier covering equipment, footwear accessories,
and outdoor gear. Production across Jalandhar (cricket/hockey) and Meerut (boxing/martial arts)
with national distribution from a Lucknow fulfilment hub.

OPERATIONAL METRICS
Lead Time: 5-8 business days (standard) | 2-3 days (express, +20% surcharge)
MOQ: 20 units per SKU
On-Time Delivery Rate: 93.4%
Order Fill Rate: 94.8%
Defect Rate: 1.2%

FINANCIAL TERMS
Payment Terms: Net-30 | Quarterly settlement option for orders >₹5 Lakhs
Discount Tiers: 4% at 100 units | 9% at 300 units | 14% at 600 units | 18% at 1,000 units
Return Policy: 30-day no-questions return for unused items in original packaging

SEASONAL RISK
CRITICAL DELAY WINDOW: March–May (IPL cricket season) and October–November (domestic cricket)
During these windows, Jalandhar units operate at 120% and lead times extend to 12-16 days.
RECOMMENDATION: Pre-buy 4 weeks of cricket equipment inventory before March 1 and October 1.
Football/volleyball/fitness equipment is unaffected by cricket season.

RISK ASSESSMENT
Risk Level: LOW-MEDIUM
Key Risks: Cricket season capacity crunch (2 windows per year), raw leather price volatility (±12%)
Mitigation: Pre-season stock build and futures pricing agreement negotiated for Q2/Q4
""",
        "supplier_SUP_006.txt": """
SUPPLIER PROFILE: SUP_006 — TechGlobal Asia Pacific
====================================================
OVERVIEW
TechGlobal Asia Pacific (Singapore-registered, China/Taiwan manufacturing) supplies premium
consumer electronics components and finished goods. Primary route: Guangzhou → Singapore →
Mumbai (sea freight, 18-22 days) with air freight option (+55% surcharge, 4-6 days).

OPERATIONAL METRICS
Lead Time: 18-28 calendar days (sea, standard) | 4-6 days (air freight)
MOQ: 100 units per SKU (sea) | 50 units (air)
On-Time Delivery Rate: 82.0% — impacted by port transit variability
Order Fill Rate: 95.2%
Defect Rate: 1.1% (factory QC certified, random 5% lot inspection)

FINANCIAL TERMS
Payment Terms: LC (Letter of Credit) or TT wire transfer, 30% advance + 70% on BL
Discount Tiers: 3% at 500 units | 7% at 1,000 units | 12% at 2,500 units
Volume Commitment: Annual volume agreement reduces per-unit cost by 8-15%

RISK ASSESSMENT
Risk Level: MEDIUM (supply chain and geopolitical exposure)
Key Risks:
  - Chinese New Year (January–February): factories closed 2-3 weeks. Place orders by Dec 15.
  - Port congestion at Guangzhou: historical +5-8 day delay during Q4 (Sep–Nov)
  - INR/USD and USD/CNY currency risk: hedged quarterly by procurement team
  - Geopolitical: Taiwan Strait risk (low probability, high impact) — dual sourced with SUP_001
Compliance: CE, FCC, BIS import clearance handled by TechGlobal; ROHS, WEEE certified
Penalty Clause: 5% of order value for delivery >14 days beyond agreed date
""",
        "supplier_SUP_007.txt": """
SUPPLIER PROFILE: SUP_007 — GlowBeauty Brands India
====================================================
OVERVIEW
GlowBeauty Brands India is a Delhi NCR-based distributor representing 14 domestic and
international beauty/personal care brands. Exclusive distributor for 3 premium skincare
lines in North and West India.

OPERATIONAL METRICS
Lead Time: 7-12 business days (standard) | 3-4 days (express from Delhi warehouse)
MOQ: 48 units per SKU (2 dozen packs)
On-Time Delivery Rate: 93.1%
Order Fill Rate: 96.4%
Defect Rate: 0.9% (mostly cosmetic packaging damage)
Shelf-Life Guarantee: Minimum 18 months remaining on all delivered goods

FINANCIAL TERMS
Payment Terms: Net-30 | 1.5% early payment discount if paid within 10 days
Discount Tiers: 4% at 200 units | 8% at 500 units | 12% at 1,000 units
Returns: Full credit for near-expiry (<6 months) goods within 30 days of delivery

REGULATORY NOTES
All products hold valid Drugs & Cosmetics Act license | BIS certified
Sunscreens: SPF claims tested by NABL-accredited lab (certificates available on request)

RISK ASSESSMENT
Risk Level: LOW
Key Risks: Festive season (Oct–Nov) demand spikes deplete distributor stock; pre-book
Recommendation: Strong, reliable partner. Pre-order Diwali gifting SKUs (perfumes, gift sets)
by September 1 for guaranteed stock.
""",
        "supplier_SUP_008.txt": """
SUPPLIER PROFILE: SUP_008 — PlayWorld Toys & Games
===================================================
OVERVIEW
PlayWorld Toys & Games supplies the full Toys & Games category, representing both domestic
manufacturers and licensed international brands (LEGO authorised distributor, Hasbro India
reseller). Distribution from Mumbai warehouse with pan-India 3PL.

OPERATIONAL METRICS
Lead Time: 10-18 business days (standard) | 5-7 days (express, +22% surcharge)
MOQ: 36 units per SKU (standard retail carton)
On-Time Delivery Rate: 88.3%
Order Fill Rate: 90.7%
Defect Rate: 2.8% (returned toys are high; robust QC recommended)

FINANCIAL TERMS
Payment Terms: Net-45 (extended seasonal credit Nov–Dec +15 days extra)
Discount Tiers: 5% at 150 units | 10% at 400 units | 15% at 800 units
Returns: 14-day return window for damaged/defective units; seasonal overstock buy-back at 70% of cost

SEASONAL RISK — CRITICAL
PEAK WINDOW: November 1–December 25 (Children's Day + Christmas = 40-60% of annual toy revenue)
RECOMMENDATION: Place Q4 orders by October 1 with full payment advance to secure allocation.
Popular LEGO sets go out of allocation by October 15 annually.
Penalty Clause: 3% per week for confirmed orders delayed beyond agreed date
Build 6-week safety stock for Q4 across all Toy SKUs.

RISK ASSESSMENT
Risk Level: MEDIUM (seasonal demand concentration, allocation risk for licensed products)
""",
        "supplier_SUP_009.txt": """
SUPPLIER PROFILE: SUP_009 — AutoParts Express India
====================================================
OVERVIEW
AutoParts Express India supplies automotive accessories, car care products, and in-car
electronics. Domestic manufacturer and importer based in Pune with express courier delivery.

OPERATIONAL METRICS
Lead Time: 3-7 business days (standard) | 1-2 days (express, +15% surcharge)
MOQ: 10 units per SKU (low MOQ makes us a preferred partner for tail-SKUs)
On-Time Delivery Rate: 95.2%
Order Fill Rate: 97.8%
Defect Rate: 1.3%

FINANCIAL TERMS
Payment Terms: Net-30 | 2% cash discount for prepayment
Discount Tiers: 3% at 50 units | 7% at 150 units | 11% at 300 units | 15% at 600 units
Warranty: 12-month product warranty (electronics accessories), 6 months (mechanical)

RISK ASSESSMENT
Risk Level: VERY LOW
Key Risks: Minor component shortages for imported car electronics (dash cams, sensors) with
+3-5 day lead time impact when global chip supply is tight. Historically occurs Q3 (Jul–Sep).
Recommendation: Reliable, low-risk partner. Suitable for JIT (just-in-time) ordering strategy.
Pre-build dash cam and parking sensor stock before monsoon season (vehicles sell more accessories).
""",
        "supplier_SUP_010.txt": """
SUPPLIER PROFILE: SUP_010 — KnowledgeHub Stationery Pvt Ltd
============================================================
OVERVIEW
KnowledgeHub Stationery is a Bengaluru-based supplier of premium notebooks, writing instruments,
art supplies, and office stationery. Represents international brands (Moleskine authorised, Staedtler
India) alongside private-label manufacturing.

OPERATIONAL METRICS
Lead Time: 5-10 business days (standard) | 2-3 days (express, +12% surcharge)
MOQ: 25 units per SKU
On-Time Delivery Rate: 96.1%
Order Fill Rate: 97.4%
Defect Rate: 0.7% (lowest defect rate in portfolio)

FINANCIAL TERMS
Payment Terms: Net-30 | Volume commitment pricing available
Discount Tiers: 3% at 100 units | 6% at 250 units | 10% at 500 units | 14% at 1,000 units
Annual Contract: -5% on all orders if annual GMV exceeds ₹50 Lakhs

SEASONAL NOTES
Academic year demand peak: June–July (school reopening) and November (exams prep)
Corporate demand peak: January (new year planning supplies) and April (FY start)

RISK ASSESSMENT
Risk Level: VERY LOW
Key Risks: International brand SKUs (Moleskine, Leuchtturm) have allocation quotas; reserve
quantities by March for back-to-school season.
Recommendation: Excellent partner for books & stationery. Consider expanding Share of Wallet
from current 100% to include additional art supply ranges from their portfolio.
""",
    }

    for fname, content in docs.items():
        (out_dir / fname).write_text(content.strip(), encoding="utf-8")
    print(f"[generator] Wrote {len(docs)} supplier profiles -> {out_dir}")


def main():
    out_dir = Path(__file__).parent
    n_categories = len(PRODUCTS)
    n_skus = sum(len(v) for v in PRODUCTS.values())
    print(f"[generator] Generating {n_skus} SKUs across {n_categories} categories...")
    skus_df = generate_skus()

    n_rows = n_skus * 365
    print(f"[generator] Generating 12 months of daily sales ({n_skus} SKUs × 365 days = {n_rows:,} rows)...")
    sales_df = generate_sales(skus_df)

    csv_path = out_dir / "sample_data.csv"
    sales_df.to_csv(csv_path, index=False)
    print(f"[generator] Saved {len(sales_df):,} rows -> {csv_path}")

    doc_dir = out_dir / "supplier_docs"
    generate_supplier_docs(doc_dir)
    print("[generator] Done!")
    return sales_df, skus_df


if __name__ == "__main__":
    main()
