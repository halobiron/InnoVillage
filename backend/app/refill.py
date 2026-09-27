"""Demo refill quotes derived from the scraped Co.opSmile product catalog.

All prices, delivery fees and fulfillment promises returned here are simulation
values owned by this demo. They are not Co.opSmile prices or services.
"""
from __future__ import annotations

import re
import sqlite3
from typing import Any

from app.agent_core.retriever import _resolve_db

_PACKAGE_RE = re.compile(r"([\d.,]+)\s*(kg|g)\b", re.IGNORECASE)
_REFILL_DISCOUNT = 0.10
_DEMO_DELIVERY_FEE = 15000
_DEMO_QUANTITIES_KG = (0.5, 1.0, 2.0)


def _package_kg(name: str) -> float | None:
    match = _PACKAGE_RE.search(name)
    if not match:
        return None
    amount = float(match.group(1).replace(",", "."))
    return amount if match.group(2).lower() == "kg" else amount / 1000


def _refill_candidates(db_path: str | None = None) -> list[dict[str, Any]]:
    conn = sqlite3.connect(_resolve_db(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT sku, brand, product_name, price_clean, product_url, retrieved_at "
            "FROM all_products WHERE category_table = ? AND product_name LIKE ? "
            "ORDER BY brand, product_name",
            ("cham_soc_nha_cua", "%Nước giặt%"),
        ).fetchall()
    finally:
        conn.close()

    products = []
    for row in rows:
        name = str(row["product_name"] or "")
        package_kg = _package_kg(name)
        # This prototype models only products whose catalog name identifies a
        # pouch, plus Surf pouch known from the source snapshot.
        if not package_kg or ("túi" not in name.casefold() and row["brand"] != "Surf"):
            continue
        price = float(row["price_clean"] or 0)
        if price <= 0:
            continue
        products.append({
            "sku": row["sku"],
            "brand": row["brand"],
            "name": name,
            "catalog_price_vnd": round(price),
            "catalog_package_kg": package_kg,
            "catalog_url": row["product_url"],
            "catalog_retrieved_at": row["retrieved_at"],
            "demo_price_per_kg_vnd": round(price / package_kg * (1 - _REFILL_DISCOUNT)),
        })
    return products


def get_refill_options(db_path: str | None = None) -> dict[str, Any]:
    products = _refill_candidates(db_path)
    return {
        "products": products,
        "quantities_kg": list(_DEMO_QUANTITIES_KG),
        "demo_discount_percent": int(_REFILL_DISCOUNT * 100),
        "demo_delivery_fee_vnd": _DEMO_DELIVERY_FEE,
        "demo_eta_minutes": 30,
        "notice": "Mô phỏng dịch vụ refill của ứng dụng; không phải dịch vụ Co.opSmile. Giá gốc lấy từ catalog, giá refill, phí giao và thời gian là dữ liệu demo.",
    }


def quote_refill(sku: str, quantity_kg: float, address: str,
                 db_path: str | None = None) -> dict[str, Any]:
    if quantity_kg not in _DEMO_QUANTITIES_KG:
        raise ValueError("Dung tích refill không hợp lệ.")
    address = address.strip()
    if len(address) < 8:
        raise ValueError("Vui lòng nhập địa chỉ giao hàng đầy đủ.")
    product = next((p for p in _refill_candidates(db_path) if p["sku"] == sku), None)
    if not product:
        raise ValueError("Sản phẩm này không có trong danh sách refill demo.")
    subtotal = round(product["demo_price_per_kg_vnd"] * quantity_kg)
    return {
        "product": product,
        "quantity_kg": quantity_kg,
        "subtotal_vnd": subtotal,
        "delivery_fee_vnd": _DEMO_DELIVERY_FEE,
        "total_vnd": subtotal + _DEMO_DELIVERY_FEE,
        "eta_minutes": 30,
        "address": address,
        "demo": True,
    }
