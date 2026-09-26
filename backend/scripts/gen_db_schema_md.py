"""Sinh file mô tả schema DB cho tool SQL của agent: app/agent_core/db_schema.md.

Đọc trực tiếp products.db để file luôn khớp thực tế (chạy lại sau mỗi lần rebuild DB):
    ./.venv/Scripts/python scripts/gen_db_schema_md.py
Mỗi cột kèm một giá trị ví dụ thật để model biết định dạng/đơn vị của dữ liệu.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sqlite3

from app.config import get_settings

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "app", "agent_core", "db_schema.md")

HEADER = """# Schema CSDL products.db (SQLite) — SINH TỰ ĐỘNG bởi scripts/gen_db_schema_md.py

## Quy tắc đọc
- `all_products`: một dòng cho mỗi mặt hàng trong snapshot catalog Co.opSmile.
- `sku` là mã nội bộ ổn định của snapshot; đây không phải mã barcode của nhà bán lẻ.
- Giá VND nằm trong `price_clean`; giá chỉ là catalog online tại ngày `retrieved_at`.
- Catalog không chứa tồn kho theo chi nhánh. `store_locations` chỉ có danh sách địa chỉ công khai.
- Bảng danh mục có thể JOIN với `all_products` qua `sku`.
- Tên cột tiếng Việt/có khoảng trắng phải bọc trong nháy kép.
"""


def sample(conn, table: str, col: str):
    try:
        row = conn.execute(
            f'SELECT "{col}" FROM "{table}" WHERE "{col}" IS NOT NULL '
            f'AND TRIM(CAST("{col}" AS TEXT)) NOT IN ("", "nan", "None") LIMIT 1').fetchone()
    except sqlite3.Error:
        return None
    return row[0] if row else None


def describe(conn, table: str, title: str) -> str:
    cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]
    n = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    lines = [f"\n## {title} ({n} dòng)"]
    for c in cols:
        v = sample(conn, table, c)
        v_txt = "" if v is None else f" — vd: {str(v)[:60]}"
        lines.append(f'- "{c}"{v_txt}')
    return "\n".join(lines)


def main():
    db = get_settings().agent_db_path
    conn = sqlite3.connect(db)
    parts = [HEADER, describe(conn, "all_products", "Bảng all_products (mọi ngành)")]
    cat_tables = conn.execute(
        "SELECT DISTINCT category, category_table FROM all_products "
        "WHERE category_table IS NOT NULL ORDER BY category_table").fetchall()
    for category, table in cat_tables:
        parts.append(describe(conn, table, f'Bảng "{table}" — ngành "{category}"'))
    conn.close()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")
    print(f"Đã ghi {OUT} ({os.path.getsize(OUT)} byte, {len(cat_tables)} bảng ngành)")


if __name__ == "__main__":
    main()
