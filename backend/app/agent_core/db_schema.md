# Schema CSDL products.db (SQLite) — SINH TỰ ĐỘNG bởi scripts/gen_db_schema_md.py

## Quy tắc đọc
- `all_products`: một dòng cho mỗi mặt hàng trong snapshot catalog Co.opSmile.
- `sku` là mã nội bộ ổn định của snapshot; đây không phải mã barcode của nhà bán lẻ.
- Giá VND nằm trong `price_clean`; giá chỉ là catalog online tại ngày `retrieved_at`.
- Catalog không chứa tồn kho theo chi nhánh. `store_locations` chỉ có danh sách địa chỉ công khai.
- Bảng danh mục có thể JOIN với `all_products` qua `sku`.
- Tên cột tiếng Việt/có khoảng trắng phải bọc trong nháy kép.


## Bảng all_products (mọi ngành) (36 dòng)
- "id" — vd: 17
- "model_code" — vd: CS-PER-001
- "sku" — vd: CS-HOME-001
- "category" — vd: Chăm sóc cá nhân
- "category_table" — vd: cham_soc_ca_nhan
- "brand" — vd: Colgate
- "price_orig" — vd: 60000
- "price_promo" — vd: 60000
- "price_clean" — vd: 60000.0
- "gift_promo"
- "key_specs_summary" — vd: Kem đánh răng Colgate Optic White Purple 100g
- "full_specs_json" — vd: {"Tên sản phẩm": "Kem đánh răng Colgate Optic White Purple 1
- "product_name" — vd: Kem đánh răng Colgate Optic White Purple 100g
- "url" — vd: https://coopsmile.vn/collections/cham-soc-ca-nhan
- "source_name" — vd: Co.opSmile online catalog
- "retrieved_at" — vd: 2026-09-26

## Bảng "cham_soc_ca_nhan" — ngành "Chăm sóc cá nhân" (16 dòng)
- "id" — vd: 1
- "model_code" — vd: CS-PER-001
- "sku" — vd: CS-PER-001
- "product_name" — vd: Kem đánh răng Colgate Optic White Purple 100g
- "brand" — vd: Colgate
- "price_clean" — vd: 60000.0
- "regular_price" — vd: 243000.0
- "url" — vd: https://coopsmile.vn/collections/cham-soc-ca-nhan
- "retrieved_at" — vd: 2026-09-26

## Bảng "cham_soc_nha_cua" — ngành "Chăm sóc nhà cửa" (20 dòng)
- "id" — vd: 1
- "model_code" — vd: CS-HOME-001
- "sku" — vd: CS-HOME-001
- "product_name" — vd: Nước xả mềm vải Comfort Hoa Trắng Tinh Khôi túi 3.6L
- "brand" — vd: Comfort
- "price_clean" — vd: 259000.0
- "regular_price" — vd: 282000.0
- "url" — vd: https://coopsmile.vn/collections/cham-soc-nha-cua
- "retrieved_at" — vd: 2026-09-26
