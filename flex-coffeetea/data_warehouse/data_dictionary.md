# Flex Coffee & Tea — Data Dictionary

> Sinh trực tiếp từ `create_schema.sql` (SQL Server / T-SQL, v1.3) — 39 bảng trên 9 domain.
> Mục đích: tra cứu chính xác từng cột (kiểu dữ liệu, bắt buộc/nullable, khóa/tham chiếu, giá trị hợp lệ) khi viết query, ETL, hoặc data generation engine.
> Về ý nghĩa nghiệp vụ/rule đằng sau các bảng, xem `../business/Business_Requirements_Specification_(BRS).md` và `../business/Entity_List.md`.

## Cách đọc bảng

| Ký hiệu | Ý nghĩa |
|---|---|
| **PK** | Khóa chính |
| **FK → `table.column`** | Khóa ngoại tham chiếu đến bảng/cột khác |
| **UNIQUE** | Ràng buộc duy nhất trên riêng cột đó |
| `Ràng buộc bảng` | CHECK/UNIQUE áp dụng trên tổ hợp nhiều cột (không gắn vào 1 cột đơn lẻ) |
| `Index` | Index phụ trợ (ngoài PK) đã khai báo trong DDL |

Quy ước ID: hầu hết bảng dùng `IDENTITY(1,1)` (auto-increment). Riêng `dim_product`, `dim_product_variant` dùng `VARCHAR(20)` theo convention prefix (VD: `BVR-001`, `BVR-001-M`, `FOOD-001`); `dim_product_category`, `dim_membership_tier` dùng mã ngắn (`CAT-01`, `TIER-1`).

---

## Domain 1 — Store

### `dim_store`

Thông tin từng cửa hàng — thuộc tính vật lý (diện tích, vị trí), vòng đời (mở/đóng cửa), và các baseline suy ra từ Store Profile Logic (nhân sự, cơ cấu kênh).

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `store_id` | INT | NOT NULL | PK |  |  |
| `store_code` | VARCHAR(10) | NOT NULL | UNIQUE |  |  |
| `store_name` | NVARCHAR(150) | NOT NULL |  |  |  |
| `city` | NVARCHAR(50) | NOT NULL |  |  |  |
| `address` | NVARCHAR(250) | NULL |  |  |  |
| `warehouse_region` | NVARCHAR(50) | NOT NULL |  |  | 'Kho Mien Bac' / 'Kho Mien Nam' |
| `location_tier` | VARCHAR(20) | NOT NULL |  |  | giá trị hợp lệ: `prime`, `standard`, `secondary` |
| `size_m2` | INT | NOT NULL |  |  |  |
| `open_date` | DATE | NOT NULL |  |  |  |
| `closed_date` | DATE | NULL |  |  |  |
| `temp_close_start` | DATE | NULL |  |  |  |
| `temp_close_end` | DATE | NULL |  |  |  |
| `status` | VARCHAR(30) | NOT NULL |  | `'active'` | giá trị hợp lệ: `active`, `temporarily_closed_recent`, `closed` |
| `is_outlier_small_prime` | BIT | NOT NULL |  | `0` |  |
| `staff_count_baseline` | INT | NULL |  |  |  |
| `channel_mix_dine_in` | DECIMAL(5,3) | NULL |  |  |  |
| `channel_mix_app` | DECIMAL(5,3) | NULL |  |  |  |
| `channel_mix_delivery` | DECIMAL(5,3) | NULL |  |  |  |
| `created_at` | DATETIME2 | NOT NULL |  | `SYSDATETIME()` |  |

---

### `store_lease`

Hợp đồng thuê mặt bằng theo từng chu kỳ tái ký — tách khỏi `dim_store` vì rent thay đổi qua thời gian (1 store có thể có nhiều dòng lease).

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `lease_id` | INT | NOT NULL | PK |  |  |
| `store_id` | INT | NOT NULL | FK → `dim_store.store_id` |  |  |
| `lease_start_date` | DATE | NOT NULL |  |  |  |
| `lease_end_date` | DATE | NULL |  |  |  |
| `monthly_rent_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `landlord_name` | NVARCHAR(150) | NULL |  |  |  |
| `is_current` | BIT | NOT NULL |  | `1` |  |

> **Index**: `(store_id)`

---

### `store_operating_hours`

Giờ mở/đóng cửa theo từng ngày trong tuần cho mỗi store — input bắt buộc để engine không sinh order ngoài giờ hoạt động.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `operating_hours_id` | INT | NOT NULL | PK |  |  |
| `store_id` | INT | NOT NULL | FK → `dim_store.store_id` |  |  |
| `day_of_week` | TINYINT | NOT NULL |  |  | 1=Mon ... 7=Sun |
| `open_time` | TIME | NOT NULL |  |  |  |
| `close_time` | TIME | NOT NULL |  |  |  |

> **Ràng buộc bảng**: UNIQUE tổ hợp (store_id, day_of_week)

---


## Domain 2 — Product

### `dim_product_category`

7 category cấp 1: Cà phê, Trà, Đá xay, LTO, Food, Retail đóng gói, Merchandise.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `category_id` | VARCHAR(10) | NOT NULL | PK |  | CAT-01 .. CAT-07 |
| `category_name` | NVARCHAR(100) | NOT NULL | UNIQUE |  |  |

---

### `dim_product`

Sản phẩm gốc (chưa gồm size/biến thể) — vòng đời launch/discontinue.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `product_id` | VARCHAR(20) | NOT NULL | PK |  | BVR-001, FOOD-001... |
| `category_id` | VARCHAR(10) | NOT NULL | FK → `dim_product_category.category_id` |  |  |
| `product_name` | NVARCHAR(150) | NOT NULL |  |  |  |
| `description` | NVARCHAR(500) | NULL |  |  |  |
| `launch_date` | DATE | NULL |  |  |  |
| `discontinued_date` | DATE | NULL |  |  |  |
| `status` | VARCHAR(20) | NOT NULL |  | `'active'` | giá trị hợp lệ: `active`, `discontinued` |

> **Index**: `(category_id)`

---

### `dim_product_variant`

Biến thể bán được thực tế (size M/L cho đồ uống, SKU đơn cho Food/Retail/Merch). Chứa cả giá bán và giá vốn, phân biệt mô hình nguồn cung qua `sourcing_model`.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `variant_id` | VARCHAR(20) | NOT NULL | PK |  | BVR-001-M, FOOD-001... |
| `product_id` | VARCHAR(20) | NOT NULL | FK → `dim_product.product_id` |  |  |
| `size_code` | VARCHAR(5) | NULL |  |  | 'M' / 'L' / NULL |
| `sku` | VARCHAR(30) | NOT NULL | UNIQUE |  |  |
| `base_price_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `cost_price_vnd` | DECIMAL(18,0) | NULL |  |  | NULL cho do uong (tinh qua recipe) |
| `sourcing_model` | VARCHAR(30) | NOT NULL |  | `'in_house_recipe'` | giá trị hợp lệ: `in_house_recipe`, `outsource_finished_goods` |
| `effective_from` | DATE | NOT NULL |  |  |  |
| `effective_to` | DATE | NULL |  |  |  |
| `is_current` | BIT | NOT NULL |  | `1` |  |

> **Index**: `(product_id)`

---

### `dim_modifier`

Danh mục topping và tùy chỉnh mức đường/đá, phân nhóm qua `modifier_group`.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `modifier_id` | INT | NOT NULL | PK |  |  |
| `modifier_group` | VARCHAR(30) | NOT NULL |  |  | giá trị hợp lệ: `topping`, `sweetness`, `ice` |
| `modifier_name` | NVARCHAR(100) | NOT NULL |  |  |  |
| `extra_price_vnd` | DECIMAL(18,0) | NOT NULL |  | `0` |  |

---

### `dim_category_modifier_exclusion`

Khai báo modifier_group nào KHÔNG áp dụng cho một category cụ thể (VD: Đá xay không có modifier mức đá).

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `exclusion_id` | INT | NOT NULL | PK |  |  |
| `category_id` | VARCHAR(10) | NOT NULL | FK → `dim_product_category.category_id` |  |  |
| `modifier_group` | VARCHAR(30) | NOT NULL |  |  |  |
| `reason` | NVARCHAR(200) | NULL |  |  |  |

> **Ràng buộc bảng**: UNIQUE tổ hợp (category_id, modifier_group)

---

### `dim_recipe`

Công thức pha chế (BOM): 1 variant đồ uống tiêu hao những nguyên liệu nào, định lượng bao nhiêu ở mức chuẩn (đường/đá 100%, size M).

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `recipe_id` | INT | NOT NULL | PK |  |  |
| `variant_id` | VARCHAR(20) | NOT NULL | FK → `dim_product_variant.variant_id` |  |  |
| `ingredient_id` | INT | NOT NULL | FK → `dim_ingredient.ingredient_id` |  |  |
| `quantity_per_unit` | DECIMAL(10,3) | NOT NULL |  |  |  |

> **Ràng buộc bảng**: UNIQUE tổ hợp (variant_id, ingredient_id)

---


## Domain 3 — Customer & Membership

### `dim_membership_tier`

Định nghĩa các hạng thành viên và ngưỡng chi tiêu rolling 12 tháng để đạt hạng.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `tier_id` | VARCHAR(10) | NOT NULL | PK |  | TIER-1, TIER-2, TIER-3 |
| `tier_name` | NVARCHAR(50) | NOT NULL | UNIQUE |  |  |
| `min_spend_rolling_12m_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `tier_rank` | INT | NOT NULL |  |  |  |

---

### `dim_customer`

Khách hàng có định danh (đăng ký qua app hoặc tại quầy) — khách vãng lai không có record ở đây.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `customer_id` | INT | NOT NULL | PK |  |  |
| `full_name` | NVARCHAR(150) | NOT NULL |  |  |  |
| `phone_number` | VARCHAR(20) | NULL |  |  |  |
| `email` | VARCHAR(150) | NULL |  |  |  |
| `registration_date` | DATE | NOT NULL |  |  |  |
| `registration_channel` | VARCHAR(20) | NOT NULL |  |  | giá trị hợp lệ: `app`, `pos` |
| `home_store_id` | INT | NULL | FK → `dim_store.store_id` |  |  |
| `current_tier_id` | VARCHAR(10) | NULL | FK → `dim_membership_tier.tier_id` |  |  |

> **Index**: `(home_store_id)`

---

### `fact_customer_membership_history`

Lịch sử thay đổi hạng thành viên theo thời gian (nâng hạng / hết hạn tụt hạng / khởi tạo).

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `membership_history_id` | BIGINT | NOT NULL | PK |  |  |
| `customer_id` | INT | NOT NULL | FK → `dim_customer.customer_id` |  |  |
| `effective_date` | DATE | NOT NULL |  |  |  |
| `old_tier_id` | VARCHAR(10) | NULL | FK → `dim_membership_tier.tier_id` |  |  |
| `new_tier_id` | VARCHAR(10) | NOT NULL | FK → `dim_membership_tier.tier_id` |  |  |
| `change_reason` | VARCHAR(30) | NOT NULL |  |  | upgrade / downgrade_expiry / initial |

> **Index**: `(customer_id)`

---

### `dim_reward_catalog`

Danh mục quà/voucher có thể đổi bằng điểm loyalty.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `reward_id` | INT | NOT NULL | PK |  |  |
| `reward_name` | NVARCHAR(150) | NOT NULL |  |  |  |
| `points_required` | INT | NOT NULL |  |  |  |
| `reward_type` | VARCHAR(30) | NOT NULL |  |  | giá trị hợp lệ: `voucher`, `physical_gift`, `free_product` |

---

### `fact_loyalty_point_transaction`

Mọi lần cộng điểm (gắn với order) hoặc trừ điểm (gắn với redemption).

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `point_txn_id` | BIGINT | NOT NULL | PK |  |  |
| `customer_id` | INT | NOT NULL | FK → `dim_customer.customer_id` |  |  |
| `txn_datetime` | DATETIME2 | NOT NULL |  |  |  |
| `txn_type` | VARCHAR(20) | NOT NULL |  |  | giá trị hợp lệ: `earn`, `redeem` |
| `points` | INT | NOT NULL |  |  |  |
| `related_order_id` | BIGINT | NULL |  |  | soft FK -> fact_order (no constraint, circular) |
| `related_redemption_id` | BIGINT | NULL |  |  | soft FK -> fact_reward_redemption |

> **Index**: `(customer_id)`

---

### `fact_reward_redemption`

Giao dịch khách hàng đổi điểm lấy quà — sự kiện độc lập với order.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `redemption_id` | BIGINT | NOT NULL | PK |  |  |
| `customer_id` | INT | NOT NULL | FK → `dim_customer.customer_id` |  |  |
| `reward_id` | INT | NOT NULL | FK → `dim_reward_catalog.reward_id` |  |  |
| `redemption_datetime` | DATETIME2 | NOT NULL |  |  |  |
| `status` | VARCHAR(20) | NOT NULL |  | `'issued'` | giá trị hợp lệ: `issued`, `used`, `expired` |

---


## Domain 4 — Sales / Order

### `dim_sales_channel`

Danh mục kênh bán: POS tại chỗ, App riêng, và các nền tảng giao hàng bên thứ ba.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `channel_id` | INT | NOT NULL | PK |  |  |
| `channel_name` | NVARCHAR(50) | NOT NULL | UNIQUE |  |  |
| `channel_group` | VARCHAR(20) | NOT NULL |  |  | giá trị hợp lệ: `dine_in`, `app`, `delivery` |
| `launch_date` | DATE | NULL |  |  |  |

---

### `fact_order`

Bảng header đơn hàng — trung tâm của domain Sales, liên kết store/customer/channel/ngày.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `order_id` | BIGINT | NOT NULL | PK |  |  |
| `store_id` | INT | NOT NULL | FK → `dim_store.store_id` |  |  |
| `customer_id` | INT | NULL | FK → `dim_customer.customer_id` |  |  |
| `channel_id` | INT | NOT NULL | FK → `dim_sales_channel.channel_id` |  |  |
| `date_key` | INT | NULL | FK → `dim_date.date_key` |  |  |
| `order_datetime` | DATETIME2 | NOT NULL |  |  |  |
| `order_type` | VARCHAR(20) | NOT NULL |  |  | giá trị hợp lệ: `dine_in`, `takeaway`, `delivery` |
| `order_status` | VARCHAR(20) | NOT NULL |  | `'completed'` | giá trị hợp lệ: `completed`, `canceled`, `refunded` |
| `gross_amount_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `discount_amount_vnd` | DECIMAL(18,0) | NOT NULL |  | `0` |  |
| `net_amount_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |

> **Index**: `(store_id, order_datetime)`; `(customer_id)`; `(channel_id)`; `(date_key)`

---

### `fact_order_item`

Chi tiết từng dòng sản phẩm trong đơn hàng.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `order_item_id` | BIGINT | NOT NULL | PK |  |  |
| `order_id` | BIGINT | NOT NULL | FK → `fact_order.order_id` |  |  |
| `variant_id` | VARCHAR(20) | NOT NULL | FK → `dim_product_variant.variant_id` |  |  |
| `quantity` | INT | NOT NULL |  |  |  |
| `unit_price_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `line_amount_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |

> **Index**: `(order_id)`; `(variant_id)`

---

### `fact_order_item_modifier`

Modifier (topping/đường/đá) áp dụng cho từng dòng sản phẩm trong đơn.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `order_item_modifier_id` | BIGINT | NOT NULL | PK |  |  |
| `order_item_id` | BIGINT | NOT NULL | FK → `fact_order_item.order_item_id` |  |  |
| `modifier_id` | INT | NOT NULL | FK → `dim_modifier.modifier_id` |  |  |
| `extra_price_vnd` | DECIMAL(18,0) | NOT NULL |  | `0` |  |

> **Index**: `(order_item_id)`

---

### `fact_payment`

Thông tin thanh toán của đơn hàng — có thể nhiều dòng nếu chia nhiều phương thức.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `payment_id` | BIGINT | NOT NULL | PK |  |  |
| `order_id` | BIGINT | NOT NULL | FK → `fact_order.order_id` |  |  |
| `payment_method` | VARCHAR(20) | NOT NULL |  |  | giá trị hợp lệ: `cash`, `card`, `ewallet`, `qr` |
| `amount_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `payment_datetime` | DATETIME2 | NULL |  |  | nullable (pending/async payments) |
| `payment_status` | VARCHAR(20) | NOT NULL |  | `'success'` | giá trị hợp lệ: `success`, `failed`, `pending` |

> **Index**: `(order_id)`

---

### `fact_order_discount`

Chi tiết giảm giá áp dụng cho đơn hàng, liên kết campaign nếu có.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `order_discount_id` | BIGINT | NOT NULL | PK |  |  |
| `order_id` | BIGINT | NOT NULL | FK → `fact_order.order_id` |  |  |
| `campaign_id` | INT | NULL | FK → `dim_campaign.campaign_id` |  |  |
| `discount_amount_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `discount_reason` | NVARCHAR(200) | NULL |  |  |  |

> **Index**: `(order_id)`

---


## Domain 5 — Marketing & Campaign

### `dim_campaign`

Chiến dịch marketing — loại, thời gian, phạm vi áp dụng, ngân sách và uplift kỳ vọng.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `campaign_id` | INT | NOT NULL | PK |  |  |
| `campaign_name` | NVARCHAR(150) | NOT NULL |  |  |  |
| `campaign_type` | VARCHAR(30) | NOT NULL |  |  | giá trị hợp lệ: `percent_discount`, `bogo`, `flash_sale`, `seasonal` |
| `start_date` | DATE | NOT NULL |  |  |  |
| `end_date` | DATE | NOT NULL |  |  |  |
| `scope_type` | VARCHAR(20) | NOT NULL |  |  | giá trị hợp lệ: `system`, `store`, `channel` |
| `scope_store_id` | INT | NULL | FK → `dim_store.store_id` |  |  |
| `scope_channel_id` | INT | NULL | FK → `dim_sales_channel.channel_id` |  |  |
| `discount_value` | DECIMAL(10,3) | NULL |  |  |  |
| `funding_source` | NVARCHAR(100) | NULL |  |  |  |
| `budget_vnd` | DECIMAL(18,0) | NULL |  |  |  |
| `expected_uplift_pct` | DECIMAL(6,3) | NULL |  |  |  |
| `priority` | INT | NULL |  |  |  |

---

### `dim_campaign_product_scope`

Giới hạn phạm vi sản phẩm/category mà 1 campaign áp dụng (nếu campaign không áp dụng toàn menu).

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `campaign_scope_id` | INT | NOT NULL | PK |  |  |
| `campaign_id` | INT | NOT NULL | FK → `dim_campaign.campaign_id` |  |  |
| `category_id` | VARCHAR(10) | NULL | FK → `dim_product_category.category_id` |  |  |
| `product_id` | VARCHAR(20) | NULL | FK → `dim_product.product_id` |  |  |

---


## Domain 6 — Inventory & Supply Chain

### `dim_ingredient`

Nguyên liệu thô dùng để pha chế đồ uống — phân biệt nguồn cung trung ương (`central`) hay địa phương (`local`).

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `ingredient_id` | INT | NOT NULL | PK |  |  |
| `ingredient_name` | NVARCHAR(150) | NOT NULL |  |  |  |
| `unit` | VARCHAR(20) | NOT NULL |  |  |  |
| `source_type` | VARCHAR(20) | NOT NULL |  |  | giá trị hợp lệ: `central`, `local` |
| `avg_shelf_life_days` | INT | NULL |  |  |  |

---

### `dim_supplier`

Nhà cung cấp nguyên liệu (central/local) hoặc nhà cung cấp hàng outsource (Food/Retail/Merch).

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `supplier_id` | INT | NOT NULL | PK |  |  |
| `supplier_name` | NVARCHAR(150) | NOT NULL |  |  |  |
| `supplies_ingredient_type` | VARCHAR(20) | NOT NULL |  |  | giá trị hợp lệ: `central`, `local`, `outsource` |
| `service_region` | NVARCHAR(50) | NULL |  |  |  |
| `category_served` | NVARCHAR(50) | NULL |  |  |  |

---

### `dim_warehouse`

2 kho trung tâm theo miền (Bắc/Nam) phục vụ các store tương ứng.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `warehouse_id` | INT | NOT NULL | PK |  |  |
| `warehouse_name` | NVARCHAR(100) | NOT NULL |  |  |  |
| `region` | NVARCHAR(50) | NOT NULL |  |  |  |

---

### `fact_purchase_order`

Đơn đặt hàng nhập nguyên liệu hoặc SKU thành phẩm — giao đến store hoặc kho trung tâm.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `purchase_order_id` | BIGINT | NOT NULL | PK |  |  |
| `store_id` | INT | NULL | FK → `dim_store.store_id` |  |  |
| `warehouse_id` | INT | NULL | FK → `dim_warehouse.warehouse_id` |  |  |
| `supplier_id` | INT | NOT NULL | FK → `dim_supplier.supplier_id` |  |  |
| `order_date` | DATE | NOT NULL |  |  |  |
| `expected_delivery_date` | DATE | NULL |  |  |  |
| `actual_delivery_date` | DATE | NULL |  |  |  |
| `status` | VARCHAR(20) | NOT NULL |  | `'ordered'` | giá trị hợp lệ: `ordered`, `delivered`, `canceled` |

> **Ràng buộc bảng**: CHECK ( store_id IS NOT NULL OR warehouse_id IS NOT NULL )

> **Index**: `(store_id)`; `(warehouse_id)`

---

### `fact_purchase_order_item`

Chi tiết dòng hàng trong 1 đơn đặt hàng — mỗi dòng chỉ dùng đúng 1 trong 2 cơ chế: nguyên liệu thô (`ingredient_id`) hoặc SKU thành phẩm (`variant_id`).

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `purchase_order_item_id` | BIGINT | NOT NULL | PK |  |  |
| `purchase_order_id` | BIGINT | NOT NULL | FK → `fact_purchase_order.purchase_order_id` |  |  |
| `ingredient_id` | INT | NULL | FK → `dim_ingredient.ingredient_id` |  |  |
| `variant_id` | VARCHAR(20) | NULL | FK → `dim_product_variant.variant_id` |  |  |
| `quantity` | DECIMAL(12,3) | NOT NULL |  |  |  |
| `unit_cost_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |

> **Ràng buộc bảng**: CHECK ( (ingredient_id IS NOT NULL AND variant_id IS NULL) OR (ingredient_id IS NULL AND variant_id IS NOT NULL) )

> **Index**: `(purchase_order_id)`

---

### `fact_inventory_transaction`

Ledger tồn kho (sổ cái) — mọi biến động nhập/xuất/điều chỉnh/hao hụt. Grain kép: theo `ingredient_id` (đồ uống) hoặc `variant_id` (Food/Retail/Merch).

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `inventory_txn_id` | BIGINT | NOT NULL | PK |  |  |
| `store_id` | INT | NOT NULL | FK → `dim_store.store_id` |  |  |
| `ingredient_id` | INT | NULL | FK → `dim_ingredient.ingredient_id` |  |  |
| `variant_id` | VARCHAR(20) | NULL | FK → `dim_product_variant.variant_id` |  |  |
| `txn_date` | DATE | NOT NULL |  |  |  |
| `txn_type` | VARCHAR(20) | NOT NULL |  |  | giá trị hợp lệ: `stock_in`, `stock_out_sales`, `adjustment`, `wastage` |
| `quantity` | DECIMAL(12,3) | NOT NULL |  |  | duong=nhap, am=xuat/hao hut |
| `unit_cost_vnd` | DECIMAL(18,0) | NULL |  |  |  |

> **Ràng buộc bảng**: CHECK ( (ingredient_id IS NOT NULL AND variant_id IS NULL) OR (ingredient_id IS NULL AND variant_id IS NOT NULL) )

> **Index**: `(store_id, ingredient_id, txn_date)`; `(store_id, variant_id,   txn_date)`

---


## Domain 7 — Human Resources

### `dim_position`

Danh mục vị trí công việc và mức lương chuẩn theo vị trí.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `position_id` | INT | NOT NULL | PK |  |  |
| `position_name` | NVARCHAR(100) | NOT NULL | UNIQUE |  |  |
| `standard_monthly_salary_vnd` | DECIMAL(18,0) | NULL |  |  |  |

---

### `dim_shift`

Ca làm việc chuẩn (giờ bắt đầu/kết thúc, lương/ca, bonus).

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `shift_id` | INT | NOT NULL | PK |  |  |
| `shift_name` | NVARCHAR(50) | NOT NULL |  |  |  |
| `standard_start_time` | TIME | NOT NULL |  |  |  |
| `standard_end_time` | TIME | NOT NULL |  |  |  |
| `total_hours` | DECIMAL(4,2) | NOT NULL |  |  |  |
| `pay_per_shift_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `bonus_vnd` | DECIMAL(18,0) | NOT NULL |  | `0` |  |

---

### `dim_employee`

Nhân viên — vị trí, store, vòng đời làm việc (ngày vào/nghỉ), loại hợp đồng.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `employee_id` | INT | NOT NULL | PK |  |  |
| `full_name` | NVARCHAR(150) | NOT NULL |  |  |  |
| `position_id` | INT | NOT NULL | FK → `dim_position.position_id` |  |  |
| `store_id` | INT | NOT NULL | FK → `dim_store.store_id` |  |  |
| `hire_date` | DATE | NOT NULL |  |  |  |
| `termination_date` | DATE | NULL |  |  |  |
| `contract_type` | VARCHAR(20) | NOT NULL |  |  | giá trị hợp lệ: `full_time`, `part_time` |

> **Index**: `(store_id)`

---

### `fact_employee_shift`

Ca làm thực tế của từng nhân viên — check-in/check-out, số phút đi trễ/về sớm.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `employee_shift_id` | BIGINT | NOT NULL | PK |  |  |
| `employee_id` | INT | NOT NULL | FK → `dim_employee.employee_id` |  |  |
| `store_id` | INT | NOT NULL | FK → `dim_store.store_id` |  |  |
| `shift_id` | INT | NOT NULL | FK → `dim_shift.shift_id` |  |  |
| `work_date` | DATE | NOT NULL |  |  |  |
| `actual_check_in` | DATETIME2 | NULL |  |  |  |
| `actual_check_out` | DATETIME2 | NULL |  |  |  |
| `late_minutes` | INT | NOT NULL |  | `0` |  |
| `early_leave_minutes` | INT | NOT NULL |  | `0` |  |
| `actual_hours_worked` | DECIMAL(4,2) | NULL |  |  |  |

> **Index**: `(employee_id, work_date)`; `(store_id,    work_date)`

---

### `fact_payroll`

Bảng lương theo tháng, tổng hợp từ ca làm thực tế.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `payroll_id` | BIGINT | NOT NULL | PK |  |  |
| `employee_id` | INT | NOT NULL | FK → `dim_employee.employee_id` |  |  |
| `pay_month` | DATE | NOT NULL |  |  |  |
| `base_salary_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `bonus_allowance_vnd` | DECIMAL(18,0) | NOT NULL |  | `0` |  |
| `total_paid_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |

> **Ràng buộc bảng**: UNIQUE tổ hợp (employee_id, pay_month)

> **Index**: `(employee_id)`

---


## Domain 8 — Finance

### `dim_expense_category`

Danh mục chi phí vận hành khác ngoài COGS/lương/thuê (điện nước, marketing local, bảo trì...).

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `expense_category_id` | INT | NOT NULL | PK |  |  |
| `expense_category_name` | NVARCHAR(100) | NOT NULL | UNIQUE |  |  |

---

### `fact_store_expense`

Chi phí phát sinh theo store/ngày thuộc các danh mục chi phí khác.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `store_expense_id` | BIGINT | NOT NULL | PK |  |  |
| `store_id` | INT | NOT NULL | FK → `dim_store.store_id` |  |  |
| `expense_category_id` | INT | NOT NULL | FK → `dim_expense_category.expense_category_id` |  |  |
| `expense_date` | DATE | NOT NULL |  |  |  |
| `amount_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `note` | NVARCHAR(300) | NULL |  |  |  |

> **Index**: `(store_id, expense_date)`

---

### `fact_store_pnl_monthly`

P&L tổng hợp theo store/tháng — bảng derive, tính từ order, payroll, lease, expense.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `pnl_id` | BIGINT | NOT NULL | PK |  |  |
| `store_id` | INT | NOT NULL | FK → `dim_store.store_id` |  |  |
| `pnl_month` | DATE | NOT NULL |  |  | ngay dau thang (VD: 2025-06-01) |
| `revenue_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `cogs_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `labor_cost_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `rent_cost_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `other_expense_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `net_profit_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |

> **Ràng buộc bảng**: UNIQUE tổ hợp (store_id, pnl_month)

> **Index**: `(store_id, pnl_month)`

---


## Domain 9 — KPI & Analytics Support

### `dim_date`

Date dimension chuẩn — phục vụ join theo ngày/tuần/tháng/quý và đánh dấu ngày lễ/Tết làm driver seasonality.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `date_key` | INT | NOT NULL | PK |  | YYYYMMDD |
| `full_date` | DATE | NOT NULL | UNIQUE |  |  |
| `day_of_week` | TINYINT | NOT NULL |  |  |  |
| `day_name` | NVARCHAR(20) | NOT NULL |  |  |  |
| `month_num` | TINYINT | NOT NULL |  |  |  |
| `month_name` | NVARCHAR(20) | NOT NULL |  |  |  |
| `quarter_num` | TINYINT | NOT NULL |  |  |  |
| `year_num` | SMALLINT | NOT NULL |  |  |  |
| `is_weekend` | BIT | NOT NULL |  |  |  |
| `is_holiday` | BIT | NOT NULL |  | `0` |  |
| `holiday_name` | NVARCHAR(100) | NULL |  |  |  |
| `is_double_day` | BIT | NOT NULL |  | `0` |  |

---

### `fact_kpi_daily_store`

KPI vận hành tổng hợp theo ngày/store — bảng derive phục vụ dashboard.

| Cột | Kiểu dữ liệu | Bắt buộc | Khóa / Tham chiếu | Mặc định | Ghi chú |
|---|---|---|---|---|---|
| `kpi_id` | BIGINT | NOT NULL | PK |  |  |
| `store_id` | INT | NOT NULL | FK → `dim_store.store_id` |  |  |
| `kpi_date` | DATE | NOT NULL |  |  |  |
| `date_key` | INT | NULL | FK → `dim_date.date_key` |  |  |
| `revenue_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `order_count` | INT | NOT NULL |  |  |  |
| `aov_vnd` | DECIMAL(18,0) | NOT NULL |  |  |  |
| `new_customer_count` | INT | NOT NULL |  | `0` |  |
| `food_cost_pct` | DECIMAL(6,3) | NULL |  |  |  |

> **Ràng buộc bảng**: UNIQUE tổ hợp (store_id, kpi_date)

> **Index**: `(store_id, kpi_date)`

---
