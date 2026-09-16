# Flex Coffee & Tea — Danh sách Entity & Quan hệ

> Bảng đánh dấu **(P2)** là mở rộng ghi nhận cho version sau, **chưa có trong schema hiện tại**.

---

## 1. Domain: Store (3 bảng)

| Entity | Mô tả |
|---|---|
| `dim_store` | Thông tin từng cửa hàng: mã, tên, thành phố, địa chỉ, kho phục vụ, `location_tier`, diện tích, ngày mở/đóng cửa, trạng thái (`active` / `temporarily_closed_recent` / `closed`), cờ `is_outlier_small_prime`, baseline nhân sự & cơ cấu kênh |
| `store_lease` | Hợp đồng thuê mặt bằng: rent/tháng, ngày bắt đầu/kết thúc, chủ nhà, cờ hợp đồng hiện hành — tách khỏi `dim_store` vì rent thay đổi theo chu kỳ tái ký |
| `store_operating_hours` | Giờ mở/đóng cửa theo từng ngày trong tuần cho mỗi store |

**Ghi chú**: `dim_store` không có cột phân loại Flagship/Standard cứng — quy mô/doanh thu là kết quả suy ra từ Store Profile Logic, không gán nhãn trước.

---

## 2. Domain: Product (6 bảng + 1 P2)

| Entity | Mô tả |
|---|---|
| `dim_product_category` | 7 category cấp 1: Cà phê, Trà, Đá xay, LTO, Food, Retail đóng gói, Merchandise |
| `dim_product` | Sản phẩm gốc (chưa gồm size): tên, category, mô tả, trạng thái active/discontinued, ngày ra mắt |
| `dim_product_variant` | Biến thể bán được: size (M/L cho đồ uống, NULL cho Food/Retail/Merch), giá bán, `cost_price_vnd` (chỉ dùng cho Food/Retail/Merch), `sourcing_model` (`in_house_recipe` / `outsource_finished_goods`), hiệu lực giá theo thời gian |
| `dim_modifier` | Topping, mức đường, mức đá — phân nhóm qua `modifier_group` |
| `dim_category_modifier_exclusion` | Modifier_group nào bị loại trừ theo category (VD: Đá xay không áp dụng mức đá) |
| `dim_recipe` | Công thức pha chế: variant → nguyên liệu (`dim_ingredient`) + định lượng chuẩn. Chỉ áp dụng `sourcing_model = in_house_recipe` |
| `dim_recipe_modifier_impact` **(P2)** | Chuẩn hóa modifier ảnh hưởng thế nào đến tiêu hao nguyên liệu, thay vì hard-code trong engine |

**Quan hệ chính**: `dim_product` 1—N `dim_product_variant`. Đồ uống: `dim_product_variant` 1—N `dim_recipe` — N `dim_ingredient` (Domain 6). Food/Retail/Merch: không có `dim_recipe`, tồn kho tham chiếu trực tiếp `variant_id` trong `fact_inventory_transaction`.

---

## 3. Domain: Customer & Membership (6 bảng)

| Entity | Mô tả |
|---|---|
| `dim_customer` | Khách có định danh (app/membership): tên, sđt/email, ngày đăng ký, kênh đăng ký (`app`/`pos`), store đăng ký ban đầu, hạng hiện tại |
| `dim_membership_tier` | Định nghĩa hạng: tên, ngưỡng chi tiêu rolling 12 tháng, thứ hạng |
| `fact_customer_membership_history` | Lịch sử đổi hạng theo thời gian (nâng hạng / hết hạn tụt hạng / khởi tạo) |
| `dim_reward_catalog` | Danh mục quà/voucher đổi bằng điểm: tên, số điểm cần, loại (voucher/quà vật lý/sản phẩm miễn phí) |
| `fact_loyalty_point_transaction` | Mỗi lần cộng/trừ điểm — gắn với order (cộng) hoặc redemption (trừ) |
| `fact_reward_redemption` | Giao dịch đổi điểm lấy quà: khách, quà, thời gian, trạng thái (issued/used/expired) |

**Ghi chú**: khách vãng lai (guest — giao hàng bên thứ ba hoặc tại chỗ không đăng nhập) có `fact_order.customer_id = NULL`, không nhầm thành 1 khách hàng duy nhất khi phân tích.

---

## 4. Domain: Sales / Order (6 bảng)

| Entity | Mô tả |
|---|---|
| `dim_sales_channel` | Kênh bán: Tại chỗ (POS), App riêng, Grab, ShopeeFood, GreenSM, BeFood — phân nhóm `channel_group` (dine_in/app/delivery), có `launch_date` cho kênh ra mắt sau |
| `fact_order` | Đơn hàng: store, customer (nullable), channel, thời điểm, `order_type` (dine-in/takeaway/delivery), trạng thái (completed/canceled/refunded), tổng tiền trước/sau giảm giá |
| `fact_order_item` | Chi tiết dòng sản phẩm: variant, số lượng, đơn giá, thành tiền |
| `fact_order_item_modifier` | Modifier áp dụng cho từng dòng sản phẩm (topping/đường/đá đã chọn) |
| `fact_payment` | Thanh toán: phương thức (tiền mặt/thẻ/ví/QR), số tiền, trạng thái |
| `fact_order_discount` | Giảm giá áp dụng cho đơn, liên kết `dim_campaign` nếu có |

**Quan hệ chính**: `fact_order` 1—N `fact_order_item` 1—N `fact_order_item_modifier`; `fact_order` 1—N `fact_payment`; `fact_order` N—1 `dim_store` / `dim_customer` (nullable) / `dim_sales_channel`.

---

## 5. Domain: Marketing & Campaign (2 bảng + 1 P2)

| Entity | Mô tả |
|---|---|
| `dim_campaign` | Chiến dịch: tên, loại (%discount/BOGO/flash sale/seasonal), thời gian, phạm vi (toàn hệ thống/store/channel), ngân sách, uplift kỳ vọng, mức ưu tiên |
| `dim_campaign_product_scope` | Sản phẩm/category nào thuộc phạm vi campaign (nếu giới hạn theo sản phẩm) |
| `fact_campaign_performance` **(P2)** | Tổng hợp kết quả campaign theo ngày/store (doanh thu, số đơn, uplift so với baseline) — có thể derive từ `fact_order` nên để P2 |

**Quan hệ**: `dim_campaign` liên kết `fact_order_discount` để biết đơn nào thuộc campaign nào.

---

## 6. Domain: Inventory & Supply Chain (6 bảng + 1 P2)

| Entity | Mô tả |
|---|---|
| `dim_ingredient` | Nguyên liệu thô: tên, đơn vị tính, `source_type` (central/local), hạn sử dụng trung bình |
| `dim_supplier` | Nhà cung cấp: tên, `supplies_ingredient_type` (central/local/outsource), khu vực phục vụ, `category_served` (cho supplier outsource) |
| `dim_warehouse` | Kho trung tâm theo miền: Kho miền Bắc, Kho miền Nam |
| `fact_purchase_order` | Đơn đặt hàng: giao đến store hoặc warehouse, nhà cung cấp, ngày đặt/giao dự kiến/giao thực tế, trạng thái |
| `fact_purchase_order_item` | Chi tiết dòng hàng: `ingredient_id` **hoặc** `variant_id` (đúng 1 trong 2, ràng buộc CHECK), số lượng, đơn giá |
| `fact_inventory_transaction` | Ledger tồn kho — `stock_in`/`stock_out_sales`/`adjustment`/`wastage`. Grain kép: `(store × ingredient × ngày)` cho đồ uống, hoặc `(store × variant × ngày)` cho Food/Retail/Merch — mỗi dòng chỉ dùng 1 trong 2 cột |
| `fact_inventory_snapshot` **(P2)** | Snapshot tồn kho cuối ngày theo store/ingredient — tăng tốc truy vấn thay vì tính lại từ ledger |

**Quan hệ chính**: `fact_order_item` (qua `dim_recipe`) sinh `fact_inventory_transaction` loại xuất bán hàng; `fact_purchase_order_item` sinh `fact_inventory_transaction` loại nhập kho.

---

## 7. Domain: Human Resources (5 bảng)

| Entity | Mô tả |
|---|---|
| `dim_position` | Vị trí công việc + mức lương chuẩn |
| `dim_shift` | Ca làm chuẩn: tên ca, giờ bắt đầu/kết thúc chuẩn, tổng giờ, lương/ca, bonus |
| `dim_employee` | Nhân viên: tên, vị trí, store hiện tại, ngày vào/nghỉ việc, loại hợp đồng (full_time/part_time) |
| `fact_employee_shift` | Ca làm thực tế: check-in/check-out, số phút đi trễ/về sớm, tổng giờ làm thực tế |
| `fact_payroll` | Bảng lương theo tháng: lương cơ bản, thưởng/phụ cấp, tổng thực nhận — tổng hợp từ `fact_employee_shift` + `dim_shift` |

**Quan hệ**: `dim_employee` N—1 `dim_store`; `dim_shift` 1—N `fact_employee_shift` → tổng hợp theo tháng thành `fact_payroll`.

---

## 8. Domain: Finance (3 bảng)

| Entity | Mô tả |
|---|---|
| `fact_store_pnl_monthly` | P&L theo store/tháng: doanh thu, COGS, chi phí lương, chi phí thuê, chi phí khác, lợi nhuận — derive từ các fact khác, lưu riêng để phục vụ báo cáo nhanh |
| `dim_expense_category` | Danh mục chi phí vận hành khác (điện nước, marketing local, bảo trì...) |
| `fact_store_expense` | Chi phí phát sinh ngoài COGS/lương/thuê, theo store/ngày |

**Ghi chú**: `fact_store_pnl_monthly` là bảng aggregate — được tính từ `fact_order`, `fact_payroll`, `store_lease`, `fact_store_expense`, không sinh độc lập.

---

## 9. Domain: KPI & Analytics Support (2 bảng)

| Entity | Mô tả |
|---|---|
| `dim_date` | Date dimension đầy đủ: ngày/tuần/tháng/quý/năm, cờ cuối tuần, ngày lễ/Tết, ngày đôi |
| `fact_kpi_daily_store` | KPI theo ngày/store: doanh thu, số đơn, AOV, số khách mới, food cost % — bảng derive phục vụ dashboard |

---

## 10. Tổng quan quan hệ giữa các domain (ERD dạng text)

```
dim_store ──┬── store_lease
            ├── store_operating_hours
            ├── dim_employee ── fact_employee_shift ── fact_payroll
            │        └── dim_shift ──┘
            ├── fact_order ──┬── fact_order_item ── fact_order_item_modifier
            │                ├── fact_payment
            │                └── fact_order_discount ── dim_campaign
            ├── fact_purchase_order ── fact_purchase_order_item ──┬── dim_ingredient
            │                                                     └── dim_product_variant
            ├── fact_inventory_transaction ──┬── dim_ingredient
            │                                └── dim_product_variant
            ├── fact_store_expense
            └── fact_store_pnl_monthly (derived)

dim_product_category ── dim_product ── dim_product_variant ──┬── [in_house_recipe] dim_recipe ── dim_ingredient
                                                              ├── [outsource] cost_price_vnd (cột trực tiếp)
                                                              ├── fact_order_item
                                                              └── fact_inventory_transaction (qua variant_id)

dim_customer ──┬── fact_order
               ├── fact_customer_membership_history ── dim_membership_tier
               ├── fact_loyalty_point_transaction
               └── fact_reward_redemption ── dim_reward_catalog

dim_sales_channel ── fact_order
dim_date ── fact_order / fact_kpi_daily_store
```

---

## 11. Ước tính khối lượng dữ liệu

`fact_inventory_transaction` chọn grain `(store × ingredient/variant × ngày)` thay vì chi tiết theo từng `order_item`:

| Kịch bản | Grain | Ước tính số dòng (3 năm, 25 store) |
|---|---|---|
| Chi tiết theo order_item | store × order_item × ingredient | ~55–65 triệu dòng |
| **Đã chọn** | store × ingredient/variant × ngày | **~4–5 triệu dòng** (xuất ~3.3–4.1tr + nhập ~0.5–0.6tr + điều chỉnh/hao hụt vài trăm nghìn) |

Nhẹ hơn ~10–15 lần, vẫn giữ bản chất ledger, đủ chi tiết để phân tích tồn kho/hao hụt/dự báo nhập hàng theo store–ingredient–ngày.
