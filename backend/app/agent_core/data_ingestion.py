import sys
import os
import re
import json
import sqlite3
import unicodedata
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app.config import get_settings
_S = get_settings()
EXCEL_PATH = _S.excel_source_path
DB_PATH = _S.agent_db_path

def table_name_for_sheet(sheet_name: str, used: set[str] | None = None) -> str:
    """Tạo tên bảng SQLite ổn định từ tên sheet, không cần whitelist ngành hàng."""
    # Chữ đ/Đ không tách thành dấu thanh trong Unicode NFD, nên thay trước.
    normalized = unicodedata.normalize("NFD", sheet_name.replace("đ", "d").replace("Đ", "D"))
    ascii_name = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    base = re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_") or "danh_muc"
    if used is None or base not in used:
        return base
    suffix = 2
    while f"{base}_{suffix}" in used:
        suffix += 1
    return f"{base}_{suffix}"

def clean_price_number(val):
    if pd.isna(val) or val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ['nan', 'none', 'null', 'không công bố']:
        return None
    # Remove currency symbols, commas, spaces
    cleaned = re.sub(r'[^\d.]', '', s)
    try:
        if '.' in cleaned:
            return float(cleaned)
        return float(int(cleaned))
    except Exception:
        return None

def clean_capacity_number(val):
    if pd.isna(val) or val is None:
        return None
    s = str(val).strip()
    # Extract first integer or decimal
    match = re.search(r'(\d+(?:\.\d+)?)', s)
    if match:
        try:
            return float(match.group(1))
        except Exception:
            return None
    return None

def ingest_data():
    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(f"Không tìm thấy file Excel tại {EXCEL_PATH}")

    print(f"Bắt đầu xử lý dữ liệu từ: {EXCEL_PATH}")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create unified table for quick searching across all categories
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS all_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_code TEXT,
        sku TEXT,
        category TEXT,
        category_table TEXT,
        brand TEXT,
        price_orig TEXT,
        price_promo TEXT,
        price_clean REAL,
        gift_promo TEXT,
        key_specs_summary TEXT,
        full_specs_json TEXT
    )
    """)

    xls = pd.ExcelFile(EXCEL_PATH)
    total_products = 0

    used_table_names: set[str] = set()
    for sheet_name in xls.sheet_names:
        table_name = table_name_for_sheet(sheet_name, used_table_names)
        used_table_names.add(table_name)
        print(f"Đang xử lý sheet: {sheet_name} -> bảng: {table_name}")
        df = pd.read_excel(xls, sheet_name=sheet_name)

        # Normalize column names
        df.columns = [str(col).strip() for col in df.columns]

        # Clean string columns
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.strip().replace({'nan': '', 'None': '', 'null': ''})

        # Add cleaned numeric columns for accurate SQL querying
        if 'giá khuyến mãi' in df.columns:
            df['price_promo_clean'] = df['giá khuyến mãi'].apply(clean_price_number)
        elif 'giá gốc' in df.columns:
            df['price_promo_clean'] = df['giá gốc'].apply(clean_price_number)
        else:
            df['price_promo_clean'] = None

        if 'Dung tích tổng' in df.columns:
            df['capacity_clean'] = df['Dung tích tổng'].apply(clean_capacity_number)
        elif 'Dung tích sử dụng' in df.columns:
            df['capacity_clean'] = df['Dung tích sử dụng'].apply(clean_capacity_number)
        elif 'Khối lượng tải chính' in df.columns:
            df['capacity_clean'] = df['Khối lượng tải chính'].apply(clean_capacity_number)
        else:
            df['capacity_clean'] = None

        # Write table to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)

        # Populate unified table
        for idx, row in df.iterrows():
            model_code = str(row.get('model_code', '')).strip()
            if not model_code or model_code.lower() == 'nan':
                model_code = f"SKU-{row.get('sku', idx)}"
            
            sku = str(row.get('sku', '')).strip()
            brand = str(row.get('brand', row.get('brand_id', ''))).strip()
            price_orig = str(row.get('giá gốc', '')).strip()
            price_promo = str(row.get('giá khuyến mãi', '')).strip()
            price_clean = row.get('price_promo_clean')
            if pd.isna(price_clean):
                price_clean = clean_price_number(price_orig)
            
            gift_promo = str(row.get('khuyến mãi quà', '')).strip()

            # Build dict of specs excluding ID columns and internal clean columns
            specs_dict = {}
            for col in df.columns:
                if col not in ['model_code', 'sku', 'productidweb', 'category_code', 'brand_id', 'brand', 'price_promo_clean', 'capacity_clean']:
                    val = row[col]
                    if pd.notna(val) and str(val).strip() not in ['', 'nan', 'None']:
                        specs_dict[col] = str(val).strip()

            full_specs_json = json.dumps(specs_dict, ensure_ascii=False)
            
            # Key summary for quick display and semantic scoring
            summary_items = [f"{k}: {v}" for k, v in list(specs_dict.items())[:8]]
            key_specs_summary = "; ".join(summary_items)

            cursor.execute("""
            INSERT INTO all_products (model_code, sku, category, category_table, brand, price_orig, price_promo, price_clean, gift_promo, key_specs_summary, full_specs_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (model_code, sku, sheet_name, table_name, brand, price_orig, price_promo, price_clean, gift_promo, key_specs_summary, full_specs_json))

            total_products += 1

    conn.commit()
    conn.close()
    print(f"Hoàn tất! Đã nạp tổng cộng {total_products} sản phẩm vào cơ sở dữ liệu {DB_PATH}.")

if __name__ == '__main__':
    ingest_data()
