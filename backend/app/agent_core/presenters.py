from __future__ import annotations
import json
import re
from typing import Any, Dict, List
from app.schemas import FactCard, FactLine
from app.advice.provenance import format_vnd

# Các mục dataset gốc không có -> luôn báo "chưa có dữ liệu".
_ALWAYS_MISSING = ["tồn kho theo chi nhánh", "đánh giá người dùng (review)"]
_NUM = re.compile(r"-?\d+(?:[.,]\d+)?")


def parse_leading_number(s: Any) -> float | None:
    if s is None:
        return None
    m = _NUM.search(str(s))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "."))
    except ValueError:
        return None


def load_specs(row: Dict[str, Any]) -> Dict[str, str]:
    raw = row.get("full_specs_json") or "{}"
    try:
        d = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    return {str(k): str(v) for k, v in d.items() if str(v).strip() not in ("", "nan", "None")}


def product_display_name(row: Dict[str, Any]) -> str:
    explicit_name = (row.get("product_name") or row.get("display_name") or "").strip()
    if explicit_name:
        return explicit_name
    specs = load_specs(row)
    explicit_name = (specs.get("Tên sản phẩm") or specs.get("tên sản phẩm") or "").strip()
    if explicit_name:
        return explicit_name
    brand = (row.get("brand") or "").strip()
    code = (row.get("model_code") or "").strip() or (row.get("sku") or "").strip()
    if code and not code.upper().startswith("SKU-"):
        return f"{brand} {code}".strip()
    summary = (row.get("key_specs_summary") or "").strip()
    if brand and summary:
        return f"{brand} - {summary[:40]}"
    return brand or summary[:40] or "Sản phẩm"


def _price_value(row: Dict[str, Any]) -> float:
    try:
        return float(row.get("price_clean") or 0)
    except (ValueError, TypeError):
        return 0.0


def _normalize_pid(raw: Any) -> str | None:
    if raw is None:
        return None
    pid = str(raw).strip()
    if pid.endswith(".0"):
        pid = pid[:-2]
    if not pid or pid.lower() in ("nan", "none", "null"):
        return None
    return pid


def _lookup_web_meta(row: Dict[str, Any]) -> Dict[str, Any]:
    """Return a saved product detail link; category URLs are not buy links."""
    meta: Dict[str, Any] = {"productidweb": _normalize_pid(row.get("productidweb")),
                            "link": None, "image": None, "rating": None}
    url = row.get("product_url")
    if isinstance(url, str) and url.startswith("https://"):
        meta["link"] = url
    return meta


def _apply_db_rating(card: FactCard, rating: float | None) -> None:
    """Nếu crawl runtime không lấy được đánh giá, dùng rating đã lưu trong DB."""
    if rating is None or card.rating is not None:
        return
    card.rating = rating
    card.lines.append(FactLine(label="Đánh giá", value=f"{rating}/5", source="catalog"))
    card.missing = [m for m in card.missing if m != "đánh giá người dùng (review)"]


def build_reco_card(row: Dict[str, Any], priority_features: List[str], self_term: str = "em") -> FactCard:
    """Card 'vì sao đề xuất': giá + hãng + vài spec liên quan ưu tiên của khách; mọi dòng gắn nguồn."""
    name = product_display_name(row)
    meta = _lookup_web_meta(row)
    lines: List[FactLine] = []
    missing: List[str] = []
    price = _price_value(row)
    if price > 0:
        lines.append(FactLine(label="Giá", value=format_vnd(int(price)), source="catalog"))
    else:
        missing.append("giá")
    if row.get("_over_budget"):
        lines.append(FactLine(label="Ngân sách", value="Vượt ngân sách khách đặt ra",
                              source="đối chiếu với yêu cầu khách"))
    lines.append(FactLine(label="Thương hiệu", value=row.get("brand") or "N/A", source="catalog"))
    if meta["link"]:
        lines.append(FactLine(label="Link sản phẩm", value=meta["link"], source="catalog"))

    specs = load_specs(row)
    prefs_low = [p.lower() for p in (priority_features or [])]
    # Ưu tiên hiển thị: (1) spec khớp ưu tiên khách, (2) spec CÓ SỐ (để LLM có con số hợp lệ
    # để trích dẫn, giảm fail-closed), (3) spec còn lại. Tối đa 5 dòng spec.
    ordered = sorted(
        specs.items(),
        key=lambda kv: (
            0 if any(p in kv[0].lower() or p in kv[1].lower() for p in prefs_low) else 1,
            0 if parse_leading_number(kv[1]) is not None else 1,
        ),
    )
    for k, v in ordered[:5]:
        lines.append(FactLine(label=k, value=v, source="thông số nhà sản xuất"))

    if row.get("gift_promo"):
        lines.append(FactLine(label="Khuyến mãi/quà kèm", value=str(row["gift_promo"]),
                               source="khuyến mãi (catalog)"))
    missing.extend(_ALWAYS_MISSING)

    card = FactCard(title=f"{name}", sku=row.get("sku"), lines=lines, missing=missing,
                    productidweb=meta["productidweb"], image_url=meta["image"],
                    product_link=meta["link"])
    _apply_db_rating(card, meta["rating"])
    return card


def build_detail_card(row: Dict[str, Any]) -> FactCard:
    """Fact-sheet đầy đủ 1 sản phẩm: giá + TOÀN BỘ spec + quà; mọi dòng gắn nguồn."""
    name = product_display_name(row)
    meta = _lookup_web_meta(row)
    lines: List[FactLine] = []
    missing: List[str] = []
    price = _price_value(row)
    if price > 0:
        lines.append(FactLine(label="Giá", value=format_vnd(int(price)), source="catalog"))
    else:
        missing.append("giá")
    lines.append(FactLine(label="Thương hiệu", value=row.get("brand") or "N/A", source="catalog"))
    if meta["link"]:
        lines.append(FactLine(label="Link sản phẩm", value=meta["link"], source="catalog"))
    for k, v in load_specs(row).items():
        lines.append(FactLine(label=k, value=v, source="thông số nhà sản xuất"))
    if row.get("gift_promo"):
        lines.append(FactLine(label="Khuyến mãi/quà kèm", value=str(row["gift_promo"]),
                               source="khuyến mãi (catalog)"))
    missing.extend(_ALWAYS_MISSING)

    card = FactCard(title=f"Thông tin chi tiết: {name}", sku=row.get("sku"), lines=lines, missing=missing,
                    productidweb=meta["productidweb"], image_url=meta["image"],
                    product_link=meta["link"])
    _apply_db_rating(card, meta["rating"])
    return card
