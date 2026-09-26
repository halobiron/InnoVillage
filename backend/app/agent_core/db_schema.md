# Schema CSDL products.db (SQLite) — SINH TỰ ĐỘNG bởi scripts/gen_db_schema_md.py

## Quy tắc đọc (quan trọng)
- `all_products`: 1 dòng = 1 sản phẩm (SKU), gộp mọi ngành. Cột `id` là khoá DUY NHẤT của dòng.
- `model_code` KHÔNG duy nhất (nhiều biến thể chung một mã) — không dùng làm khoá nhận diện.
- Giá bán (VND) là `price_clean`; giá trị 0/NULL nghĩa là CHƯA CÓ DỮ LIỆU giá, không phải miễn phí — muốn lọc/xếp theo giá phải kèm `price_clean > 0`.
- Mỗi ngành có bảng thông số riêng (1 dòng = 1 sản phẩm), JOIN với all_products qua `model_code`.
- Cột thông số là TEXT thường kèm đơn vị (vd '313 lít', '27 inch') — so sánh số bằng `CAST("tên cột" AS REAL)` (SQLite lấy phần số đứng đầu chuỗi).
- Tên cột tiếng Việt/có khoảng trắng phải bọc trong nháy kép: `"Dung tích tổng"`.


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
