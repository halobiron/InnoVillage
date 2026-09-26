from __future__ import annotations

"""Purchase-flow helpers for the Co.opSmile essential-goods catalog.

Delivery fees and per-store availability are not part of the imported catalog,
so the assistant must not assert them or invent cross-sell relationships.
"""

from typing import Any, Dict, Optional

from app.agent_core.text import strip_accents


def _flat(category: Optional[str]) -> str:
    return strip_accents((category or "").strip().lower())


def shipping_fee_line(category: Optional[str], price: float) -> None:
    """No delivery fee data is available in the catalog snapshot."""
    del category, price
    return None


def closing_hook(category: Optional[str] = None, price: float = 0.0,
                 addr: str = "", self_term: str = "") -> str:
    del category, price, addr, self_term
    return ("Em chưa có dữ liệu chính xác về phí giao hàng hoặc tồn kho tại chi nhánh. "
            "Anh/chị vui lòng kiểm tra trên kênh đặt hàng Co.opSmile trước khi mua ạ.")


def cross_sell_suggestion(category: Optional[str], price: float,
                          db_path: Optional[str] = None,
                          exclude_sku: Optional[str] = None) -> None:
    """Only suggest paired products after a verified relationship is sourced."""
    del category, price, db_path, exclude_sku
    return None


def cross_sell_line(row: Dict[str, Any], addr: str = "", self_term: str = "") -> str:
    del addr, self_term
    from app.agent_core.presenters import product_display_name
    from app.advice.provenance import format_vnd
    price = float(row.get("price_clean") or 0)
    price_text = format_vnd(int(price)) if price > 0 else "chưa có dữ liệu giá"
    return (f"Có thể xem thêm {product_display_name(row)} (giá {price_text}, nguồn: catalog). "
            "Anh/chị có muốn xem sản phẩm này không?")


_ORDER_CONFIRM_KW = [
    "chot don", "chot mua", "lay mon nay", "mua mon nay", "dat hang di",
    "dat hang giup", "xac nhan mua", "ok mua", "chot luon", "lay luon",
    "mua luon", "dong y mua", "chot don hang", "minh lay", "em lay", "anh lay",
]

_AFTERSALES_KW = [
    "mon da mua", "san pham da mua", "don da mua", "da mua truoc do",
    "lan truoc mua", "don hang truoc", "mon minh mua hom truoc",
    "khach hang cu", "khach cu", "uu dai khach cu",
]


def is_order_confirmation(message: str) -> bool:
    flat = strip_accents(message.lower())
    return any(k in flat for k in _ORDER_CONFIRM_KW)


def is_aftersales_question(message: str) -> bool:
    flat = strip_accents(message.lower())
    return any(k in flat for k in _AFTERSALES_KW)
