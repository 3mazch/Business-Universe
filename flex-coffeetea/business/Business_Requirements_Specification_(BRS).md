# Flex Coffee & Tea — Business Requirements Specification (BRS)

> **Trạng thái**: Final — khớp 1:1 với `Entity_List.md` và `create_schema.sql` (39 bảng, 9 domain).
> Tài liệu mô tả rule nghiệp vụ dùng để (1) thiết kế database và (2) viết engine sinh dữ liệu giả lập cho dự án phân tích dữ liệu F&B.
> Giá trị được đánh dấu **(derived)** là không sinh trực tiếp mà tính toán từ bảng/rule khác — engine cần đảm bảo nhất quán.

---

## 0. Bối cảnh doanh nghiệp

**Flex Coffee & Tea** là chuỗi F&B 100% công ty tự vận hành, kinh doanh cà phê, trà, food, retail đóng gói và merchandise.

| | |
|---|---|
| Quy mô | 25 cửa hàng — Hà Nội (10), TP.HCM (10), Đà Nẵng (5) |
| Giai đoạn | Đã qua tăng trưởng nóng, hiện **chững lại** — doanh thu đi ngang ở nhiều store trong 6–12 tháng gần nhất |
| Khách hàng | Đa dạng: dân văn phòng, học sinh–sinh viên, gia đình — không có phân khúc áp đảo |
| Khung dữ liệu | 3 năm gần nhất tính đến 07/2026 (~08/2023 – 07/2026) |

---

## 1. Domain: Store (Cửa hàng & vận hành mặt bằng)

- Không phân tầng cứng (Flagship/Standard/Kiosk). Mỗi cửa hàng có 3 thuộc tính đầu vào độc lập — `city`, `size_m2`, `location_tier` — và các outcome (rent, doanh thu, staff) được **suy ra** từ tổ hợp này, không gán nhãn trước. Công thức chi tiết ở tài liệu *Store Profile Logic*.
- Cho phép **outlier có chủ đích**: store diện tích nhỏ + vị trí đẹp → rent cao bất thường so với diện tích, cơ cấu doanh thu lệch về app/giao hàng (ít chỗ ngồi).
- `open_date` trải theo 4 làn sóng mở rộng (2020–2024, mật độ giảm dần) — tạo store "mới" (dữ liệu ngắn) và "cũ" (dữ liệu đầy đủ) trong cùng khung thời gian.
- Trạng thái hoạt động: `active`, `temporarily_closed_recent` (sửa chữa/đổi mặt bằng), `closed` (đóng vĩnh viễn) — 1–2 store có giai đoạn gián đoạn để phản ánh business case "chững lại".
- **Rent & Lease**: `store_lease.monthly_rent_vnd` là hàm của diện tích × vị trí × hệ số thành phố + nhiễu ngẫu nhiên (không tuyến tính đơn giản). Hợp đồng tái ký theo chu kỳ (2–3 năm/lần), mỗi lần tái ký rent tăng ~5–10% → nhiều dòng `store_lease` cho cùng 1 store nếu vòng đời dài hơn 1 chu kỳ.
- **Giờ hoạt động**: khác nhau theo thành phố và ngày trong tuần (`store_operating_hours`), là input bắt buộc cho engine sinh order — order chỉ được sinh trong khung giờ mở cửa.

---

## 2. Domain: Product (Sản phẩm & công thức)

- 7 category cấp 1: **Cà phê, Trà, Đá xay, LTO** (pha chế theo BOM) và **Food, Retail đóng gói, Merchandise** (nhập nguyên SKU từ outsource). Danh mục đầy đủ tại `Flex_CoffeeTea_Menu_Recipe_v1.md`.
- Đồ uống có 2 size (M/L) — mỗi size là 1 `dim_product_variant` riêng; L = định lượng nguyên liệu M × 1.3, giá bán cao hơn M. Food/Retail/Merchandise không có size, variant = chính SKU.
- Sản phẩm có vòng đời (`launch_date`/`discontinued_date`); LTO có vòng đời ngắn theo mùa (6–10 tuần, có thể lặp lại năm sau) — nguồn business case "uplift khi ra sản phẩm mới".

**Modifier & Recipe**
- 2 nhóm modifier: **topping** (chỉ áp dụng Cà phê/Trà/LTO, phụ thu 8.000–12.000đ, chọn 0–3/ly) và **mức đường/đá** (50/100/150%, không phụ thu, chỉ ảnh hưởng định lượng nguyên liệu).
- Đá xay là ngoại lệ: không áp dụng modifier "mức đá" — quy tắc loại trừ này chuẩn hóa vào bảng `dim_category_modifier_exclusion` thay vì hard-code trong engine.
- Mỗi variant đồ uống có 1 recipe chuẩn (`dim_recipe`) tại mức đường/đá 100%, size M. Khi mức đường/đá thay đổi, định lượng nguyên liệu liên quan được điều chỉnh tỷ lệ trong engine (không lưu bảng riêng). Topping cộng thêm 1 dòng tiêu hao cố định, không nhân theo size.

**Food / Retail / Merchandise — mô hình outsource**
- 3 category này **không** đi qua `dim_ingredient`/`dim_recipe`. Mỗi sản phẩm là 1 SKU nhập nguyên (finished goods) từ nhà cung cấp outsource.
- `dim_product_variant.cost_price_vnd` + `sourcing_model` (`in_house_recipe` vs `outsource_finished_goods`) phân biệt 2 mô hình.
- Margin tham khảo theo sub-category: Food ~55–58%, Retail đóng gói ~30–40% (biên mỏng hơn vì bán lại nguyên gói), Merchandise ~55–64%.
- Tồn kho tiêu hao 1:1 — bán 1 SKU trừ đúng 1 đơn vị đã nhập, ghi nhận qua `variant_id` (thay vì `ingredient_id`) trong `fact_inventory_transaction`.
- 4 nhà cung cấp outsource riêng theo sub-category (Food-bánh lạnh, Food-bánh nóng, Retail, Merchandise) — output: `dim_supplier_outsource.csv`, `dim_product_food_retail_merch.csv` (24 SKU).

---

## 3. Domain: Customer & Membership

- Chỉ khách đăng ký **App riêng** hoặc **membership tại quầy** có `dim_customer` record. Khách kênh giao hàng bên thứ ba và khách tại chỗ không đăng nhập → `customer_id = NULL` (guest).
- Tỷ lệ có membership theo kênh: Tại chỗ ~50%, App riêng gần 100%, Giao hàng 3 bên 0%.
- 1 khách có thể mua ở nhiều store; `home_store_id` chỉ là store đăng ký đầu tiên, không giới hạn hành vi mua sau này.
- **Hạng thành viên**: tối thiểu 3 hạng, phân hạng theo **tổng chi tiêu completed rolling 12 tháng gần nhất** (mô hình kiểu Phúc Long/Starbucks) — không phải điểm tích lũy trọn đời. Đánh giá lại hạng theo tần suất cố định (VD: đầu mỗi tháng hoặc mỗi quý). Mỗi lần đổi hạng ghi vào `fact_customer_membership_history` kèm lý do (đủ điều kiện lên hạng / hết hạn tụt hạng).
- Tích điểm theo % giá trị đơn hoàn thành (không tính đơn hủy/hoàn). Đổi điểm lấy quà (`fact_reward_redemption`) là sự kiện độc lập với order.
- Phân khúc khách hàng (văn phòng/sinh viên/gia đình) **không** lưu thành cột cứng — thể hiện qua pattern hành vi (giờ mua, tần suất, giỏ hàng trung bình, độ nhạy khuyến mãi) do engine sinh dữ liệu tạo ra.

---

## 4. Domain: Sales / Order

- 1 đơn hàng luôn thuộc đúng 1 store, 1 channel, có thể có/không có customer.
- `order_type` tương quan với channel: kênh giao hàng bên thứ ba → luôn `delivery`; App riêng → `takeaway` hoặc `delivery`; kênh tại quầy (POS) → `dine-in` hoặc `takeaway`.
- Trạng thái đơn: `completed` (đa số), `canceled` (không tính doanh thu/kho/điểm), `refunded` (đã hoàn thành nhưng hoàn tiền sau — cần logic đảo ngược). Tỷ lệ canceled/refunded nhỏ nhưng khác 0 (~1–3%).
- **Kênh bán**: baseline hệ thống Tại chỗ ~50% / App riêng ~20% / Giao hàng ~30% (gộp Grab, ShopeeFood, BeFood, GreenSM) — tỷ trọng thực tế dao động theo từng store profile (vị trí gần văn phòng vs khu dân cư).
- `fact_order_item.unit_price_vnd` lấy theo giá variant **tại thời điểm bán**, có cơ chế versioning giá đơn giản khi giá tăng theo thời gian.
- Giảm giá áp theo % tổng đơn hoặc theo item (BOGO), ghi ở `fact_order_discount`, liên kết `dim_campaign` nếu thuộc chiến dịch chính thức, hoặc NULL nếu là giảm giá tại chỗ (hiếm).
- **Seasonality**: 2 đỉnh giờ trong ngày (7h30–9h và 16h–19h); cao điểm mùa hè (đồ uống lạnh) và dịp lễ Tết/Giáng sinh; thấp điểm sau Tết (tháng 2–3).

---

## 5. Domain: Marketing & Campaign

- 4 loại campaign: giảm giá %, BOGO, flash sale (khung giờ ngắn), campaign theo mùa/lễ (dài hạn, có thể kết hợp ra mắt sản phẩm mới).
- Phạm vi áp dụng: toàn hệ thống, hoặc giới hạn theo store/thành phố/channel.
- Trong giai đoạn có campaign, order volume tại phạm vi áp dụng tăng so với baseline (uplift %, mức tăng khác nhau theo loại: flash sale mạnh–ngắn hạn, campaign mùa vừa phải–dài hạn).

---

## 6. Domain: Inventory & Supply Chain

- **Mô hình kho (nguyên liệu pha chế)**: nguyên liệu chính (cà phê, trà, sữa, syrup...) nhập từ kho trung tâm theo chu kỳ cố định (hàng tuần); nguyên liệu phụ/tươi sống do từng store tự đặt nhà cung cấp địa phương, chu kỳ ngắn hơn (2–3 lần/tuần). `dim_ingredient.source_type` phân biệt `central`/`local`.
- **2 kho trung tâm theo miền**: Kho miền Bắc (phục vụ 10 store Hà Nội), Kho miền Nam (phục vụ 10 store TP.HCM + 5 store Đà Nẵng). Đà Nẵng không có kho riêng → lead time giao hàng dài hơn, rủi ro stock-out/wastage cao hơn.
- Food/Retail/Merchandise **không** đi qua mô hình kho trung tâm/địa phương — nhập trực tiếp từ nhà cung cấp outsource (`source_type = outsource`), chu kỳ đặt hàng theo tuần.
- **Ledger tồn kho kép (dual-grain)**: nhánh đồ uống ở grain `(store × ingredient × ngày)`; nhánh Food/Retail/Merch ở grain `(store × variant × ngày)`. Cả hai dùng chung cấu trúc `stock_in` / `stock_out_sales` (derived từ order + recipe/modifier) / `adjustment` / `wastage`. Tồn kho tại 1 thời điểm = running balance của ledger, không lưu cột "tồn hiện tại" riêng. Không cho phép tồn kho âm.
- **Purchase Order**: chu kỳ và lead time khác nhau theo `source_type` — trung ương (tuần/2 tuần, lead time 3–5 ngày, dài hơn ở ĐN), địa phương (lead time 1–2 ngày), outsource (tuần, lead time 2–4 ngày). Số lượng đặt hàng tương quan với tốc độ tiêu thụ gần đây, không random hoàn toàn. `fact_purchase_order_item` và `fact_inventory_transaction` dùng CHECK đảm bảo mỗi dòng chỉ điền đúng 1 trong 2 cột (`ingredient_id` **hoặc** `variant_id`).
- **Wastage**: cao hơn với nguyên liệu tươi (hạn ngắn) và ở store doanh thu thấp/tồn kho dư thừa — business case "store nào wastage bất thường, vì sao?".

---

## 7. Domain: Human Resources

- Số nhân viên/store thay đổi theo diện tích và doanh thu kỳ vọng, không cố định giống nhau cho cả 25 store.
- Vị trí tối thiểu: Quản lý (1/store), Pha chế (2–4), Thu ngân/Phục vụ (2–5) — tỷ lệ pha chế:phục vụ khác nhau theo tỷ trọng kênh giao hàng.
- Có turnover — `termination_date` không NULL cho một phần nhân viên, tỷ lệ hợp lý theo ngành F&B (có thể 30–50%/năm cho vị trí thời vụ).
- `dim_shift` định nghĩa ca chuẩn (sáng/chiều/ca gãy) với lương/ca cố định + bonus (ca đêm, ngày lễ). `fact_employee_shift` ghi check-in/check-out thực tế, cho phép lệch so với ca chuẩn (đi trễ, về sớm, overtime) — tỷ lệ đi trễ biến động hợp lý theo ngày (VD: cao hơn thứ 2 đầu tuần, sau nghỉ lễ).
- `fact_payroll` **(derived)**: tổng hợp theo tháng từ shift thực tế + lương ca + phụ cấp/thưởng (có thể gắn KPI doanh thu store hoặc thưởng lễ Tết).

---

## 8. Domain: Finance

- **P&L theo store/tháng** `fact_store_pnl_monthly` **(derived)**, tính từ:

  | Thành phần | Nguồn |
  |---|---|
  | Doanh thu | Tổng `net_amount_vnd` của đơn `completed` trong tháng, theo store |
  | COGS | Từ `fact_inventory_transaction` loại `stock_out_sales` × giá vốn nguyên liệu (đề xuất: weighted average) |
  | Chi phí lương | Tổng `fact_payroll` của nhân viên thuộc store trong tháng |
  | Chi phí thuê | `store_lease.monthly_rent_vnd` áp dụng cho tháng đó |
  | Chi phí khác | Tổng `fact_store_expense` (điện nước, marketing local, bảo trì...) |
  | Lợi nhuận | Doanh thu − COGS − Lương − Thuê − Chi phí khác |

- Store outlier (nhỏ, vị trí đẹp, rent cao) cần thể hiện rõ **biên lợi nhuận mỏng dù doanh thu không thấp** — insight quan trọng nhất mà chuỗi logic Store Profile → Rent → P&L phải nhất quán tạo ra.
- Bảng này là sản phẩm của pipeline ETL định kỳ (mô phỏng batch job cuối tháng), không sinh ngẫu nhiên độc lập.

---

## 9. Domain: KPI & Analytics Support

- `dim_date` bao phủ toàn bộ khung thời gian dữ liệu (+ biên trước/sau vài tháng cho rolling metrics), đánh dấu ngày lễ/Tết Việt Nam làm driver seasonality.
- `fact_kpi_daily_store` **(derived)**: doanh thu, số đơn, AOV, số khách mới, food cost % — sản phẩm của cùng pipeline tổng hợp như P&L, ở tần suất ngày.

---

## 10. Ràng buộc liên domain (Cross-domain Consistency Rules)

Các rule đảm bảo dữ liệu giữa các domain khớp logic — quan trọng nhất khi viết Data Generation Engine vì sinh độc lập từng bảng dễ tạo dữ liệu vô lý.

1. Order chỉ được sinh trong khung giờ hoạt động của store (Store ↔ Sales).
2. Mỗi `fact_order_item` kích hoạt tiêu hao nguyên liệu theo `dim_recipe` (điều chỉnh theo modifier) → cộng dồn vào `fact_inventory_transaction` grain ngày (Product ↔ Sales ↔ Inventory).
3. Đơn `canceled` không trừ kho/cộng điểm/tính doanh thu; đơn `refunded` có logic đảo ngược (hoàn điểm nếu đã cộng, không hoàn nguyên liệu đã tiêu hao thực tế nhưng trừ doanh thu) (Sales ↔ Customer ↔ Finance).
4. Nhân sự phải tồn tại (active) tại store trước khi store có thể sinh order.
5. Campaign đang hiệu lực tăng order volume tại phạm vi áp dụng, đồng thời discount tương ứng xuất hiện trong `fact_order_discount` (Marketing ↔ Sales).
6. Store mới mở có doanh thu thấp hơn baseline rồi tăng dần (ramp-up curve), không ổn định ngay từ ngày đầu.
7. Giai đoạn "chững lại" toàn công ty thể hiện rõ ở hầu hết store cũ trong 6–12 tháng gần nhất — tăng trưởng chậm/đi ngang so với cùng kỳ năm trước, không tăng đều suốt 3 năm.

---

## 11. Ngoài phạm vi hiện tại (định hướng mở rộng)

Các ý tưởng đã ghi nhận nhưng chưa triển khai, dành cho version sau:

- Chuẩn hóa modifier → tiêu hao nguyên liệu vào DB (`dim_recipe_modifier_impact`) thay vì hard-code trong engine.
- `fact_campaign_performance` lưu kết quả campaign chính thức thay vì tính lại từ `fact_order` mỗi lần.
- Mô phỏng hiệu ứng cannibalization của campaign lên giai đoạn liền sau.
- Phí hoa hồng (%) khác nhau theo từng platform giao hàng.
- Cơ chế điểm loyalty hết hạn (expiry).
- Reorder point / safety stock tự động thay vì lịch đặt hàng cố định; `fact_inventory_snapshot` cuối ngày để tăng tốc truy vấn.
- Phạt/trừ lương do vi phạm giờ giấc.
- KPI nâng cao: retention, repeat purchase rate, employee productivity, inventory turnover.
- Domain mới: quản lý tài sản/thiết bị (bảo trì, khấu hao); feedback/review khách hàng theo đơn hàng.
- Landlord type, điều khoản phạt hợp đồng thuê sớm.
