# FLEX COFFEE & TEA — DANH SÁCH ENTITY & QUAN HỆ (v1.4)

> Mục tiêu tài liệu: xác định khung xương database trước khi đi vào chi tiết logic sinh dữ liệu.

> Trạng thái: Đã Review

---

## 0. NGUYÊN TẮC THIẾT KẾ CHUNG

- Mỗi domain có 1-2 bảng "master/dimension" (thông tin ít thay đổi) và các bảng "transaction/fact" (sinh dữ liệu liên tục theo thời gian).
- Toàn bộ transaction đều tham chiếu `store_id` và `date/time` để phục vụ phân tích theo thời gian — cửa hàng — kênh bán.
- Naming convention: snake_case. Dimension dùng khóa chính `<entity>_id` (Logical). Fact dùng Composite Keys hoặc Logical Transaction ID.
- Các bảng có đánh dấu **(P2)** là mở rộng có thể làm sau, chưa bắt buộc ở bản v1.

---

## 1. DOMAIN: STORE (Cửa hàng & Vận hành mặt bằng)

| Entity | Mô tả | Loại |
|---|---|---|
| `dim_store` | Thông tin từng cửa hàng: mã, tên, thành phố, địa chỉ, diện tích (m2), loại vị trí (location_tier), ngày khai trương, ngày đóng cửa (nếu có), trạng thái hoạt động | Dimension |
| `store_lease` | Hợp đồng thuê mặt bằng: giá thuê/tháng, ngày bắt đầu/kết thúc hợp đồng, đơn vị cho thuê — tách riêng khỏi `dim_store` vì giá thuê có thể thay đổi theo chu kỳ tái ký hợp đồng | Dimension/Slowly-changing |
| `store_operating_hours` | Giờ mở/đóng cửa theo từng ngày trong tuần cho mỗi store (một số store trung tâm mở muộn hơn) | Dimension |

**Ghi chú thiết kế**: `dim_store` sẽ chứa các thuộc tính đầu vào cho "Store Profile Logic" (diện tích, vị trí) nhưng **không** có cột cứng phân loại Flagship/Standard — quy mô/doanh thu là kết quả suy ra từ dữ liệu giao dịch, không gán nhãn cứng trước.

---

## 2. DOMAIN: PRODUCT (Sản phẩm & Công thức)

| Entity | Mô tả | Loại |
|---|---|---|
| `dim_product_category` | Danh mục cấp 1 **[CẬP NHẬT v1.2]**: Cà phê, Trà, Đá xay, LTO, Food, Retail đóng gói, Merchandise (7 category, tách chi tiết hơn từ 5 category ban đầu) | Dimension |
| `dim_product` | Sản phẩm cụ thể (SKU gốc chưa gồm size): tên, category_id, mô tả, trạng thái active/discontinued, ngày ra mắt | Dimension |
| `dim_product_variant` | Biến thể bán được: product_id + size (M/L cho đồ uống, NULL cho Food/Retail/Merch) + `base_price_vnd` (giá bán) + **[v1.2] `cost_price_vnd`** (giá vốn, chỉ dùng cho Food/Retail/Merch) + **[v1.2] `sourcing_model`** (`in_house_recipe` = đồ uống pha chế theo BOM / `outsource_finished_goods` = Food/Retail/Merch nhập nguyên SKU) | Dimension |
| `dim_modifier` | Danh sách topping / tùy chỉnh: topping (trân châu, thạch...), mức đường (50/100/150%), mức đá — có nhóm modifier_group để phân biệt loại (topping vs sweetness vs ice). **[v1.2]** CHỈ áp dụng cho Cà phê/Trà/LTO; Đá xay không áp dụng mức đá | Dimension |
| `dim_recipe` | Công thức pha chế: product_variant_id → danh sách nguyên liệu (`ingredient_id`) và định lượng tiêu hao chuẩn. **[v1.2] CHỈ áp dụng cho sourcing_model = `in_house_recipe`** (Cà phê/Trà/Đá xay/LTO) | Dimension (BOM) |
| `dim_category_modifier_exclusion` **[v1.3]** | Khai báo các modifier_group KHÔNG được phép sử dụng cho một nhóm đồ uống nhất định (VD: Đá Xay không cho phép điều chỉnh `ice`) | Dimension |
| `dim_recipe_modifier_impact` **(P2)** | Định nghĩa modifier ảnh hưởng thế nào đến tiêu hao nguyên liệu (VD: topping trân châu → +1 phần trân châu vào recipe gốc) | Dimension |

**Quan hệ chính**: `dim_product` 1—N `dim_product_variant`; với đồ uống: `dim_product_variant` 1—1 `dim_recipe` 1—N `dim_ingredient`; với Food/Retail/Merch: `dim_product_variant` KHÔNG có `dim_recipe`, tồn kho tham chiếu trực tiếp `variant_id` trong `fact_inventory` (xem Domain 6 cập nhật v1.2).

**[MỚI v1.2] Nguồn cung cấp cho Food/Retail/Merchandise**: 3 category này KHÔNG dùng `dim_ingredient`/`dim_recipe` để tránh phức tạp không cần thiết — mỗi sản phẩm là 1 SKU nhập nguyên (finished goods) từ nhà cung cấp outsource, có `cost_price_vnd` và `sell_price_vnd` (=`base_price_vnd`) gắn trực tiếp vào `dim_product_variant`. Margin tham khảo: Food ~55-58%, Merchandise ~55-64%, Retail ~30-40% (biên mỏng hơn vì là hàng bán lại nguyên gói). Xem chi tiết tại `Flex_CoffeeTea_Menu_Recipe_v1.md` mục 6-8 và script `generate_food_retail_merch.py`.

---

## 3. DOMAIN: CUSTOMER & MEMBERSHIP

| Entity | Mô tả | Loại |
|---|---|---|
| `dim_customer` | Thông tin khách hàng có định danh (đăng ký app/membership): tên, sđt/email (giả), ngày đăng ký, store đăng ký ban đầu, kênh đăng ký | Dimension |
| `dim_membership_tier` | Định nghĩa hạng thành viên: Member/Silver/Gold/VIP... — ngưỡng điểm/chi tiêu để lên hạng, quyền lợi | Dimension |
| `fact_customer_membership_history` | Lịch sử thay đổi hạng thành viên theo thời gian (nâng hạng, hết hạn, tụt hạng) | Fact/Slowly-changing |
| `fact_loyalty_point_transaction` | Mỗi lần cộng/trừ điểm: gắn với order_id (cộng điểm) hoặc redemption_id (trừ điểm khi đổi quà) | Fact |
| `dim_reward_catalog` | Danh mục quà/voucher có thể đổi bằng điểm: tên, số điểm cần, loại (voucher giảm giá, quà tặng vật lý, sản phẩm miễn phí) | Dimension |
| `fact_reward_redemption` | Giao dịch đổi điểm lấy quà: customer_id, reward_id, thời gian, trạng thái sử dụng | Fact |

**Ghi chú**: khách vãng lai (guest, ~kênh giao hàng/tại chỗ không đăng nhập) **không** có `customer_id` — order vẫn ghi nhận nhưng field customer_id = NULL, cần xử lý riêng trong phân tích (không nhầm guest thành 1 khách hàng duy nhất).

---

## 4. DOMAIN: SALES / ORDER (Bán hàng)

| Entity | Mô tả | Loại |
|---|---|---|
| `dim_sales_channel` | Danh mục kênh bán: Tại chỗ (POS), App riêng, Grab, ShopeeFood, GreenSM, BeFood | Dimension |
| `fact_order` | Đơn hàng: order_id, store_id, customer_id (nullable), channel_id, order_datetime, order_type (dine-in/takeaway/delivery), trạng thái (completed/canceled/refunded), tổng tiền trước/sau giảm giá | Fact (header) |
| `fact_order_item` | Chi tiết dòng sản phẩm trong đơn: PK là `(order_id, item_seq)`, product_variant_id, số lượng, đơn giá, thành tiền | Fact (detail) |
| `fact_order_item_modifier` | Modifier áp dụng cho dòng SP: PK là `(order_id, item_seq, modifier_id)` | Fact (detail) |
| `fact_payment` | Thông tin thanh toán: PK là `(order_id, payment_method)`, số tiền, trạng thái | Fact |
| `fact_order_discount` | Chi tiết giảm giá áp dụng cho đơn: PK là `(order_id, campaign_id)` | Fact |

**Quan hệ chính**: `fact_order` 1—N `fact_order_item` 1—N `fact_order_item_modifier`; `fact_order` 1—1(hoặc N nếu chia nhiều lần) `fact_payment`; `fact_order` N—1 `dim_store`, N—1 `dim_customer` (nullable), N—1 `dim_sales_channel`.

---

## 5. DOMAIN: MARKETING & CAMPAIGN

| Entity | Mô tả | Loại |
|---|---|---|
| `dim_campaign` | Chiến dịch marketing: tên, loại (%discount, BOGO, flash sale, seasonal), thời gian bắt đầu/kết thúc, phạm vi áp dụng (toàn hệ thống/theo store/theo channel) | Dimension |
| `dim_campaign_product_scope` | Sản phẩm/category nào được áp dụng campaign (nếu campaign giới hạn phạm vi sản phẩm) | Dimension |
| `fact_campaign_performance` **(P2)** | Bảng tổng hợp kết quả campaign theo ngày/store (doanh thu trong campaign, số đơn, uplift so với baseline) — có thể derive từ fact_order nên để P2 | Fact/Aggregate |

**Quan hệ**: `dim_campaign` liên kết tới `fact_order_discount` để biết đơn nào thuộc campaign nào.

---

## 6. DOMAIN: INVENTORY & SUPPLY CHAIN (Kho vận)

| Entity | Mô tả | Loại |
|---|---|---|
| `dim_ingredient` | Nguyên liệu thô: tên, đơn vị tính (kg/lít/gói/cái), loại (nguyên liệu chính từ kho trung tâm / nguyên liệu phụ đặt địa phương), hạn sử dụng trung bình | Dimension |
| `dim_supplier` | Nhà cung cấp: tên, loại nguyên liệu cung cấp (`central`/`local`/**[v1.2] `outsource`**), khu vực phục vụ, **[v1.2] `category_served`** (cho nhà cung cấp outsource: Food-BánhLạnh/Food-BánhNóng/Retail/Merchandise) | Dimension |
| `dim_warehouse` | Kho: kho trung tâm (theo miền hoặc toàn quốc) và có thể coi mỗi store cũng có "kho tại chỗ" (store as mini-warehouse) | Dimension |
| `fact_purchase_order` | Đơn đặt hàng nhập nguyên liệu: PK là `po_id` VARCHAR. Lưu warehouse/store nhận, supplier, ngày đặt... | Fact (header) |
| `fact_purchase_order_item` | Chi tiết nguyên liệu/SKU trong đơn nhập: **[v1.2]** `ingredient_id` (nguyên liệu thô, cho đồ uống) HOẶC `variant_id` (SKU thành phẩm, cho Food/Retail/Merch) — chỉ 1 trong 2 được điền, số lượng, đơn giá | Fact (detail) |
| `fact_inventory` | (PK: `transaction_id` VARCHAR) Mọi biến động tồn kho: nhập (từ purchase order), xuất (do bán hàng, gộp theo ngày), điều chỉnh, hao hụt/hết hạn (wastage) — thiết kế dạng ledger (sổ cái). **[v1.2]** Grain kép: `(store × ingredient × ngày)` cho đồ uống pha chế, HOẶC `(store × variant × ngày)` cho SKU thành phẩm Food/Retail/Merch — mỗi dòng chỉ dùng 1 trong 2 cơ chế | Fact (ledger) |
| `fact_inventory_snapshot` **(P2)** | Snapshot tồn kho cuối ngày theo store/ingredient — giúp truy vấn nhanh hơn thay vì tính lại từ ledger mỗi lần | Fact/Aggregate |

**Quan hệ chính**: `fact_order_item` (qua `dim_recipe`) sinh ra `fact_inventory` loại "xuất do bán hàng"; `fact_purchase_order_item` sinh ra `fact_inventory` loại "nhập kho".

---

## 7. DOMAIN: HUMAN RESOURCES (Nhân sự)

| Entity | Mô tả | Loại |
|---|---|---|
| `dim_employee` | Nhân viên: tên, vị trí (QL/pha chế/thu ngân/phục vụ), store_id hiện tại, ngày vào làm, ngày nghỉ việc (nếu có), loại hợp đồng | Dimension |
| `dim_position` | Danh mục vị trí công việc + mức lương chuẩn theo vị trí | Dimension |
| `dim_shift` | Ca làm chuẩn: shift_id, tên ca (Sáng/Chiều/Tối), giờ bắt đầu chuẩn, giờ kết thúc chuẩn, tổng số giờ, lương/giờ hoặc lương/ca cố định, bonus (ca đêm/lễ) | Dimension |
| `fact_employee_shift` | Ca làm thực tế: PK `(employee_id, work_date, shift_id)`. Dùng tính giờ làm thực tế. | Fact |
| `fact_payroll` | Bảng lương theo tháng: PK `(employee_id, pay_month)`. Tính tổng lương thực nhận. | Fact |

**Quan hệ**: `dim_employee` N—1 `dim_store`; `dim_shift` 1—N `fact_employee_shift` 1—N (tổng hợp theo tháng) `fact_payroll`.

---

## 8. DOMAIN: FINANCE (Tài chính & P&L)

| Entity | Mô tả | Loại |
|---|---|---|
| `fact_store_pnl_monthly` | P&L tổng hợp theo store/tháng: PK `(store_id, pnl_month)`. Bảng derive phục vụ báo cáo nhanh. | Fact/Aggregate |
| `dim_expense_category` | Danh mục chi phí vận hành khác (điện nước, marketing local, bảo trì...) | Dimension |
| `fact_store_expense` | Chi phí phát sinh khác ngoài COGS/lương/thuê: PK `(store_id, expense_date, expense_category_id)` | Fact |

**Ghi chú**: `fact_store_pnl_monthly` về bản chất là bảng **aggregate/derived** — sẽ được Python engine tính toán từ `fact_order`, `fact_payroll`, `store_lease`, `fact_store_expense` chứ không sinh độc lập, để đảm bảo số liệu luôn khớp logic.

---

## 9. DOMAIN: KPI & ANALYTICS SUPPORT **(P2 — có thể để sau)**

| Entity | Mô tả | Loại |
|---|---|---|
| `dim_date` | Bảng ngày chuẩn (date dimension) — phục vụ join theo ngày/tuần/tháng/quý, đánh dấu ngày lễ/Tết | Dimension |
| `fact_kpi_daily_store` | KPI tổng hợp theo ngày/store: PK `(store_id, kpi_date)`. Bảng derive phục vụ dashboard | Fact/Aggregate |

---

## 10. TỔNG QUAN QUAN HỆ GIỮA CÁC DOMAIN (ERD dạng text)

```
dim_store ──┬── store_lease
            ├── store_operating_hours
            ├── dim_employee ── fact_employee_shift ── fact_payroll
            │        └── dim_shift ──┘
            ├── fact_order ──┬── fact_order_item ── fact_order_item_modifier
            │                ├── fact_payment
            │                └── fact_order_discount ── dim_campaign
            ├── fact_purchase_order ── fact_purchase_order_item ── dim_ingredient
            ├── fact_inventory ── dim_ingredient
            ├── fact_store_expense
            └── fact_store_pnl_monthly (derived)

dim_product_category ── dim_product ── dim_product_variant ──┬── [in_house_recipe] dim_recipe ── dim_ingredient
                                                                ├── [outsource] cost_price_vnd (cot truc tiep, khong qua dim_ingredient)
                                                                └── fact_order_item
                                        dim_product_variant ── fact_inventory (Food/Retail/Merch, qua variant_id)

dim_customer ──┬── fact_order
                ├── fact_customer_membership_history ── dim_membership_tier
                ├── fact_loyalty_point_transaction
                └── fact_reward_redemption ── dim_reward_catalog

dim_sales_channel ── fact_order
```

---

## 11. NHỮNG ĐIỂM LƯU Ý

📌 Các domain mở rộng khác (tài sản/thiết bị, feedback/review khách hàng...) — để dành cho v2/v3, không đưa vào v1.

### Ước tính khối lượng `fact_inventory`
| Kịch bản | Grain | Ước tính số dòng (3 năm, 25 store) |
|---|---|---|
| A — chi tiết theo order_item | store × order_item × ingredient | ~55-65 triệu dòng |
| **B — đã chọn** | store × ingredient × ngày | **~4-5 triệu dòng** (xuất kho ~3.3-4.1tr + nhập kho ~0.5-0.6tr + điều chỉnh/hao hụt vài trăm nghìn) |

Kịch bản B nhẹ hơn ~10-15 lần, vẫn giữ bản chất ledger, đủ chi tiết để phân tích tồn kho/hao hụt/dự báo nhập hàng theo store-ingredient-ngày.

