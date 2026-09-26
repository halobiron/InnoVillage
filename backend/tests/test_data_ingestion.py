import sqlite3

import pandas as pd

from app.agent_core import data_ingestion


def test_ingestion_accepts_every_sheet_without_a_category_whitelist(tmp_path, monkeypatch):
    source = tmp_path / "catalog.xlsx"
    db_path = tmp_path / "products.db"
    with pd.ExcelWriter(source) as writer:
        pd.DataFrame([{"model_code": "A-1", "sku": "sku-a", "brand": "Alpha", "giá gốc": 1_000_000}]).to_excel(
            writer, sheet_name="Thiết bị mới", index=False
        )
        pd.DataFrame([{"model_code": "B-1", "sku": "sku-b", "brand": "Beta", "giá gốc": 2_000_000}]).to_excel(
            writer, sheet_name="Đồ dùng lạ", index=False
        )

    monkeypatch.setattr(data_ingestion, "EXCEL_PATH", str(source))
    monkeypatch.setattr(data_ingestion, "DB_PATH", str(db_path))
    data_ingestion.ingest_data()

    conn = sqlite3.connect(db_path)
    try:
        categories = {row[0] for row in conn.execute("SELECT DISTINCT category FROM all_products")}
        tables = {row[0] for row in conn.execute("SELECT DISTINCT category_table FROM all_products")}
    finally:
        conn.close()
    assert categories == {"Thiết bị mới", "Đồ dùng lạ"}
    assert tables == {"thiet_bi_moi", "do_dung_la"}
