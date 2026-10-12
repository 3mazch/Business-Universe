# Step 3: Load Dimensions to Data Warehouse

## Mục tiêu

Load toàn bộ **23 dimension tables** từ file CSV trong `data/dimension/full/` vào SQL Server database `FlexCoffeeTea`.

## Điều kiện tiên quyết

### 1. SQL Server & Database
- SQL Server đang chạy (local hoặc remote)
- Đã tạo database `FlexCoffeeTea` bằng script DDL:
  ```sql
  -- Chạy trong SSMS hoặc Azure Data Studio
  -- File: data_warehouse/schema/create_schema.sql
  ```

### 2. ODBC Driver
Cài **ODBC Driver 17 for SQL Server** từ Microsoft (nếu chưa có):
- Windows: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

### 3. Python dependencies
```bash
pip install -r requirements.txt
```

### 4. Dimension data
File CSV phải tồn tại trong `data/dimension/full/`.  
Nếu chưa có, chạy Step 2 trước:
```bash
python src/data_generation/run_dimensions.py
```

---

## Setup kết nối

```bash
# Copy template và điền thông tin
cp data_warehouse/db_loader/.env.example data_warehouse/db_loader/.env
```

Mở `.env` và chỉnh sửa:

```env
# Local default instance — Windows Authentication (recommended)
DB_SERVER=localhost
DB_NAME=FlexCoffeeTea
DB_TRUSTED=yes

# --- HOẶC --- SQL Server Authentication
# DB_USER=your_login
# DB_PASSWORD=your_password
```

Để `DB_PORT` unset khi dùng local default instance hoặc named instance. Chỉ đặt
`DB_PORT` nếu TCP/IP đã được cấu hình với port cố định. Có thể đặt `DB_SERVER`
thành tên instance như `localhost\SQLEXPRESS`; không cấu hình đồng thời tên
instance và `DB_PORT`.

Test kết nối (dùng cùng authentication mode và endpoint với loader):
```bash
python data_warehouse/db_loader/db_config.py
```

---

## Chạy loader

```bash
# Từ project root

# 1. Load tất cả 23 tables (lần đầu)
python data_warehouse/db_loader/load_dimensions.py

# 2. Dry-run (kiểm tra CSV mà không ghi vào DB)
python data_warehouse/db_loader/load_dimensions.py --dry-run

# 3. Overwrite (truncate + reload)
python data_warehouse/db_loader/load_dimensions.py --truncate

# 4. Load một table cụ thể
python data_warehouse/db_loader/load_dimensions.py --table dim_store

# 5. Validation sau khi load
python data_warehouse/db_loader/validate_dimensions.py
```

---

## Thứ tự load (FK dependency)

```
Tier 0 — Không có FK:
  dim_date, dim_product_category, dim_membership_tier,
  dim_modifier, dim_expense_category, dim_position,
  dim_shift, dim_warehouse, dim_supplier,
  dim_sales_channel, dim_reward_catalog

Tier 1 — Phụ thuộc Tier 0:
  dim_store, dim_product, dim_ingredient

Tier 2 — Phụ thuộc Tier 1:
  dim_product_variant, dim_customer, dim_employee,
  store_lease, store_operating_hours, dim_campaign

Tier 3 — Phụ thuộc Tier 2:
  dim_recipe, dim_category_modifier_exclusion,
  dim_campaign_product_scope
```

---

## Cấu trúc files

```
data_warehouse/db_loader/
├── .env.example          ← Template credentials (copy → .env)
├── .env                  ← Credentials thật (KHÔNG commit)
├── db_config.py          ← Connection factory, test kết nối
├── load_dimensions.py    ← Loader chính (23 tables)
├── validate_dimensions.py ← Post-load validation
└── README.md             ← File này
```

---

## Output mẫu

```
2026-10-09  INFO     Flex Coffee & Tea — Step 3: Load Dimensions to SQL Server
2026-10-09  INFO     Connected to SQL Server ✅
2026-10-09  INFO     ── dim_date ──────────────
2026-10-09  INFO       [dim_date] CSV: 1,126 rows | cols: [date_key, full_date, ...]
2026-10-09  INFO       [dim_date] ✅ Inserted 1,126 rows.
...
2026-10-09  INFO     SUMMARY
  Table                                    CSV     Ins   Err  Status
  dim_date                               1,126   1,126     0  ✅ ok
  dim_store                                 25      25     0  ✅ ok
  dim_customer                           5,200   5,200     0  ✅ ok
  dim_employee                           1,666   1,666     0  ✅ ok
  ...
  TOTAL                                 XX,XXX  XX,XXX     0
```

---

## Troubleshooting

| Lỗi | Nguyên nhân | Giải pháp |
|-----|-------------|-----------|
| `No suitable ODBC driver` | Chưa cài ODBC Driver | Cài ODBC Driver 17 from Microsoft |
| `Login failed for user` | Sai user/pass trong .env | Kiểm tra DB_USER, DB_PASSWORD |
| `Cannot open database "FlexCoffeeTea"` | DB chưa tạo | Chạy `create_schema.sql` trước |
| `TRUNCATE TABLE ... cannot be used` | FK constraint | Script sẽ tự động dùng DELETE |
| `FK violation` trên insert | Sai thứ tự load | Chạy toàn bộ (không dùng `--table`) |
