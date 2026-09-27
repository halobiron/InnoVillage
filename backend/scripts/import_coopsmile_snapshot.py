"""Build the runtime SQLite catalog from the checked-in Co.opSmile snapshot.

Refresh source snapshots under ``data/`` from Co.opSmile's public catalog/store
pages before running this script. The store list does not represent per-store
inventory; only online catalog prices are imported.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
CATALOG_FILE = REPO_DIR / "data" / "coopsmile_catalog.json"
STORES_FILE = REPO_DIR / "data" / "coopsmile_stores.json"
DB_FILE = BACKEND_DIR / "app" / "agent_core" / "products.db"
TEMP_DB = DB_FILE.with_suffix(".db.new")
sys.path.insert(0, str(BACKEND_DIR))


def table_name(category: str) -> str:
    from app.agent_core.data_ingestion import table_name_for_sheet
    return table_name_for_sheet(category)


def main() -> None:
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    store_data = json.loads(STORES_FILE.read_text(encoding="utf-8"))
    products = catalog["products"]
    if not products:
        raise ValueError("Catalog snapshot is empty; keeping the existing database.")

    TEMP_DB.unlink(missing_ok=True)
    conn = sqlite3.connect(TEMP_DB)
    try:
        conn.execute("""CREATE TABLE all_products (
            id INTEGER PRIMARY KEY,
            model_code TEXT,
            sku TEXT UNIQUE,
            category TEXT,
            category_table TEXT,
            brand TEXT,
            price_orig TEXT,
            price_promo TEXT,
            price_clean REAL,
            gift_promo TEXT,
            key_specs_summary TEXT,
            full_specs_json TEXT,
            product_name TEXT,
            url TEXT,
            product_url TEXT,
            source_name TEXT,
            retrieved_at TEXT
        )""")
        by_category: dict[str, list[dict]] = {}
        for item in products:
            by_category.setdefault(item["category"], []).append(item)

        for category, rows in by_category.items():
            table = table_name(category)
            conn.execute(f'''CREATE TABLE "{table}" (
                id INTEGER PRIMARY KEY,
                model_code TEXT,
                sku TEXT,
                product_name TEXT,
                brand TEXT,
                price_clean REAL,
                regular_price REAL,
                url TEXT,
                retrieved_at TEXT
            )''')
            for item in rows:
                price = int(item["price"])
                regular = item.get("regular_price")
                facts = {
                    "Tên sản phẩm": item["name"],
                    "Danh mục": category,
                    "Giá niêm yết": f"{price:,}đ",
                    "Nguồn giá": "Catalog trực tuyến Co.opSmile",
                    "URL nguồn": item["url"],
                    "Ngày lấy dữ liệu": catalog["retrieved_at"],
                    "Tồn kho theo chi nhánh": "Chưa có dữ liệu",
                }
                if regular:
                    facts["Giá gốc niêm yết"] = f"{int(regular):,}đ"
                conn.execute("""INSERT INTO all_products
                    (model_code, sku, category, category_table, brand, price_orig,
                     price_promo, price_clean, gift_promo, key_specs_summary,
                    full_specs_json, product_name, url, product_url, source_name, retrieved_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)""",
                    (item["sku"], item["sku"], category, table, item.get("brand"),
                     str(regular or price), str(price), price, item["name"],
                     json.dumps(facts, ensure_ascii=False), item["name"], item["url"],
                     item.get("product_url"),
                     catalog["source_name"], catalog["retrieved_at"]))
                conn.execute(f'''INSERT INTO "{table}"
                    (model_code, sku, product_name, brand, price_clean, regular_price,
                     url, retrieved_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (item["sku"], item["sku"], item["name"], item.get("brand"),
                     price, regular, item["url"], catalog["retrieved_at"]))

        conn.execute("""CREATE TABLE store_locations (
            store_code TEXT PRIMARY KEY,
            address TEXT NOT NULL,
            phone TEXT,
            opening_hours TEXT,
            source_url TEXT,
            retrieved_at TEXT
        )""")
        conn.executemany("""INSERT INTO store_locations
            (store_code, address, phone, opening_hours, source_url, retrieved_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            [(store["store_code"], store["address"], store.get("phone"),
              store.get("opening_hours"), store_data["source"], store_data["retrieved_at"])
             for store in store_data["stores"]])
        conn.commit()
    finally:
        conn.close()

    os.replace(TEMP_DB, DB_FILE)
    print(f"Imported {len(products)} products and {len(store_data['stores'])} store records into {DB_FILE}")


if __name__ == "__main__":
    main()
