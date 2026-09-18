# FLEX COFFEE & TEA — BUSINESS REQUIREMENTS SPECIFICATION (BRS) v1.2

> Tài liệu này là **nguồn sự thật (source of truth)** cho toàn bộ dự án: từ thiết kế DDL (SQL schema) đến logic sinh dữ liệu (Python data generation engine). Mọi rule ở đây phải khớp với Entity List v1.1.
>
> **Quy ước gắn nhãn rule:**
> - **[v1]** — bắt buộc, áp dụng ngay trong bản database/data hiện tại.
> - **[v2+]** — ý tưởng nâng cấp, ghi nhận lại để mở rộng entity/logic sau này, KHÔNG triển khai ở v1.
> - **[DERIVED]** — giá trị không sinh trực tiếp mà được tính toán từ rule/bảng khác — cần nhất quán khi viết engine.

---

## 0. BỐI CẢNH DOANH NGHIỆP (Business Context)

**Flex Coffee & Tea** là chuỗi F&B 100% công ty tự vận hành (company-owned), kinh doanh cà phê, trà, food (bánh nóng/lạnh), retail đóng gói (cà phê/trà bán mang về) và merchandise (ly, cốc, túi).

- **Quy mô**: 25 cửa hàng — Hà Nội (10), TP.HCM (10), Đà Nẵng (5).
- **Giai đoạn**: đã trải qua giai đoạn tăng trưởng nóng (mở rộng nhanh từ ít cửa hàng lên 25), hiện đang **chững lại** — tăng trưởng doanh thu chậm dần hoặc đi ngang ở nhiều cửa hàng trong 6-12 tháng gần nhất.
- **Khách hàng mục tiêu**: đa dạng — dân văn phòng, học sinh-sinh viên, gia đình — không có 1 phân khúc áp đảo.
- **Khung thời gian dữ liệu**: 3 năm gần nhất tính đến 07/2026 (tức khoảng 08/2023 – 07/2026).

---

## 1. DOMAIN: STORE (Cửa hàng & Vận hành mặt bằng)

### 1.1 Nguyên tắc cốt lõi
- **[v1]** Không phân tầng cứng (Flagship/Standard/Kiosk). Mỗi cửa hàng có bộ thuộc tính độc lập: `city`, `size_m2`, `location_tier` (vị trí đẹp/thường/hẻm), và các outcome (doanh thu, rent, staff_count) được **suy ra từ tổ hợp thuộc tính**, không gán nhãn cố định trước.
- **[v1]** Cho phép **outlier có chủ đích**: cửa hàng diện tích nhỏ nhưng vị trí đẹp (VD: mặt phố trung tâm, gần văn phòng lớn) → rent cao bất thường so với diện tích, và có cơ cấu doanh thu lệch (VD: tỷ trọng khách vãng lai/app cao hơn tại chỗ). Logic chi tiết công thức tương quan sẽ định nghĩa ở tài liệu **"Store Profile Logic"** (bước kế tiếp sau BRS).
- **[v1]** Mỗi cửa hàng có `open_date` nằm trong giai đoạn công ty mở rộng (không phải tất cả 25 store mở cùng lúc) — cần mô phỏng lịch sử mở cửa theo làn sóng (VD: 2021-2022 mở đợt đầu ở HN/HCM, 2023 mở rộng ra ĐN và các store còn lại) để dữ liệu 3 năm gần nhất có store "mới" (dữ liệu ngắn) và store "cũ" (dữ liệu đầy đủ suốt kỳ).
- **[v1]** Trạng thái hoạt động: `active`, `temporarily_closed` (sửa chữa/thuê lại mặt bằng), `closed` (đóng vĩnh viễn) — cho phép 0-2 cửa hàng có giai đoạn đóng cửa tạm thời hoặc đóng hẳn trong 3 năm để phản ánh giai đoạn "chững lại" của doanh nghiệp — đây là nguồn business case thực tế (phân tích lý do đóng cửa, so sánh store còn sống vs đã đóng).

### 1.2 Rent & Lease
- **[v1]** `store_lease.monthly_rent` là hàm của `size_m2` × `location_tier` × `city_base_rate`, KHÔNG tuyến tính đơn giản — có nhiễu ngẫu nhiên (±15-20%) để tạo outlier.
- **[v1]** Hợp đồng thuê có chu kỳ tái ký (VD: 2-3 năm/lần) — mỗi lần tái ký, rent có thể tăng (escalation ~5-10%) — sinh nhiều dòng trong `store_lease` cho cùng 1 store nếu vòng đời store dài hơn 1 chu kỳ hợp đồng.
- **[v2+]** Thêm cột `landlord_type` (cá nhân/doanh nghiệp) hoặc điều khoản phạt phá vỡ hợp đồng sớm — phục vụ phân tích rủi ro mặt bằng.

### 1.3 Giờ hoạt động
- **[v1]** Giờ mở/đóng cửa khác nhau theo thành phố và theo ngày trong tuần: cửa hàng ở khu văn phòng có thể mở sớm hơn (6h30-7h) phục vụ giờ đi làm, cửa hàng gần khu sinh viên/giải trí mở muộn hơn tối. Ghi nhận trong `store_operating_hours`.
- **[v1]** Giờ hoạt động là **input cho engine sinh order** — order chỉ được sinh trong khung giờ mở cửa của store đó (tránh dữ liệu vô lý: đơn hàng lúc 2h sáng ở store đóng cửa 22h).

---

## 2. DOMAIN: PRODUCT (Sản phẩm & Công thức)

### 2.1 Danh mục & cấu trúc sản phẩm
- **[v1.2] [CẬP NHẬT]** 7 category cấp 1: **Cà phê, Trà, Đá xay, LTO** (đồ uống — pha chế theo BOM), **Food, Retail đóng gói, Merchandise** (nhập nguyên SKU từ outsource).
- **[v1]** Đồ uống (Cà phê/Trà/Đá xay/LTO) có **2 size: M, L** — mỗi size là 1 `dim_product_variant` riêng, L = định lượng nguyên liệu M × hệ số 1.3, giá bán L cao hơn M.
- **[v1]** Food, Retail, Merchandise: không có size (variant = chính sản phẩm, giá cố định theo SKU).
- **[v1]** Sản phẩm có vòng đời: `launch_date`, và có thể `discontinued_date` — không phải tất cả sản phẩm tồn tại xuyên suốt 3 năm. **LTO đặc biệt có vòng đời ngắn hạn theo mùa** (6-10 tuần/lần xuất hiện, có thể lặp lại năm sau) — nguồn business case "uplift khi ra mắt sản phẩm mới".

### 2.2 Modifier (Topping & tùy chỉnh)
- **[v1]** 2 nhóm modifier chính:
  - **Topping** (chỉ áp dụng đồ uống Cà phê/Trà/LTO): trân châu đen, trân châu trắng, thạch, pudding... — có phụ thu riêng (+8.000-12.000đ/loại), khách có thể chọn 0-3 topping/ly.
  - **Điều chỉnh mức đường/đá**: 50%/100%/150% — KHÔNG phụ thu, chỉ ảnh hưởng định lượng nguyên liệu tiêu hao (đường/đá) trong recipe.
- **[v1]** Modifier áp dụng cho Cà phê/Trà/LTO — Food/Retail/Merchandise không có modifier.
- **[v1.2] [NGOẠI LỆ MỚI]** **Đá xay KHÔNG áp dụng modifier "mức đá"** (bản chất món đã xay đá sẵn, chỉ áp dụng modifier "mức đường"). Engine sinh dữ liệu cần loại trừ modifier_group='ice' khi product thuộc category Đá xay.
- **[v2+]** Mở rộng modifier cho Food (VD: thêm topping bánh, chọn nóng/lạnh cho 1 số món) nếu muốn tăng độ phức tạp.

### 2.3 Recipe (Công thức - BOM) — CHỈ áp dụng cho đồ uống (Cà phê/Trà/Đá xay/LTO)
- **[v1]** Mỗi `dim_product_variant` đồ uống có 1 recipe chuẩn: danh sách nguyên liệu + định lượng chuẩn tại mức đường/đá 100%, size M. Chi tiết template theo từng kiểu pha chế (phin truyền thống, espresso-based, trà trái cây, trà sữa, trà kem phô mai, matcha/chocolate latte, đá xay) đã định nghĩa.
- **[v1]** Khi mức đường/đá thay đổi (50%/150%), định lượng nguyên liệu tương ứng (Syrup đường, Đá viên) được điều chỉnh tỷ lệ tương ứng trong lúc tính tiêu hao — logic ở **engine Python**, không lưu bảng riêng (không cần `dim_recipe_modifier_impact` đầy đủ ở v1).
- **[v1]** Topping được cộng thêm 1 dòng tiêu hao riêng ngoài recipe gốc, định lượng cố định không nhân theo size (VD: trân châu đen luôn +30g/phần).
- **[v2+]** Bảng `dim_recipe_modifier_impact` đầy đủ (P2) — chuẩn hóa quy tắc modifier→nguyên liệu vào database thay vì hard-code trong Python.

### 2.4 [v1.2] Food / Retail / Merchandise — Mô hình Outsource (KHÔNG dùng dim_ingredient/dim_recipe)
- **[v1.2] [CHỐT]** Để tránh phức tạp không cần thiết, 3 category này **KHÔNG** đi qua `dim_ingredient`/`dim_recipe`. Mỗi sản phẩm là **1 SKU nhập nguyên (finished goods)** từ nhà cung cấp outsource (xem `dim_supplier.supplies_ingredient_type = 'outsource'`).
- **[v1.2]** `dim_product_variant` có thêm 2 cột: `cost_price_vnd` (giá vốn nhập) và `sourcing_model` (`in_house_recipe` cho đồ uống / `outsource_finished_goods` cho Food/Retail/Merch).
- **[v1.2]** Margin (`(sell_price - cost_price) / sell_price`) khác nhau theo sub-category, phản ánh đặc tính ngành:
  - Food (bánh lạnh/bánh nóng): margin ~55-58%.
  - Retail đóng gói: margin ~30-40% (biên mỏng hơn vì bản chất là bán lại hàng đóng gói).
  - Merchandise: margin ~55-64% (hàng thương hiệu, biên tốt).
- **[v1.2]** Tồn kho của 3 category này tiêu hao theo kiểu **1:1** — bán 1 SKU trừ đúng 1 đơn vị đã nhập, ghi nhận trong `fact_inventory` qua cột `variant_id` (thay vì `ingredient_id` như đồ uống).
- **[v1.2]** 4 nhà cung cấp outsource riêng biệt theo sub-category (Food-bánh lạnh, Food-bánh nóng, Retail, Merchandise) — đã sinh sẵn trong `dim_supplier_outsource.csv`.
- Output đã sinh: `dim_product_food_retail_merch.csv` (24 SKU) qua script `generate_food_retail_merch.py`.

---

## 3. DOMAIN: CUSTOMER & MEMBERSHIP

### 3.1 Định danh khách hàng
- **[v1]** Chỉ khách đăng ký **App riêng** hoặc **membership tại quầy** mới có `dim_customer` record. Khách kênh giao hàng (Grab/Shopee/Be/GreenSM) và khách tại chỗ không đăng nhập → `fact_order.customer_id = NULL` (guest).
- **[v1]** Tỷ lệ có membership theo kênh: Tại chỗ ~50% đơn có membership (khách quen), App riêng gần như 100% có membership (vì phải đăng nhập mới đặt được), Giao hàng 3 bên = 0% (không định danh được, vì tài khoản thuộc về platform Grab/Shopee chứ không phải Flex).
- **[v1]** 1 khách hàng có thể mua ở nhiều store khác nhau (không giới hạn theo store đăng ký ban đầu) — `dim_customer.home_store_id` chỉ là store đăng ký đầu tiên, không giới hạn hành vi mua sau này.

### 3.2 Membership Tier & Loyalty
- **[v1] [CHỐT]** Cấu trúc hạng: tối thiểu 3 hạng (VD: Member → Gold → VIP), phân hạng dựa trên **tổng chi tiêu tích lũy rolling 12 tháng gần nhất** (giống mô hình Phúc Long/Starbucks thực tế) — không phải điểm tích lũy trọn đời. Nghĩa là: mỗi ngày/mỗi lần đánh giá lại hạng, hệ thống nhìn lại tổng chi tiêu completed trong đúng 12 tháng gần nhất tính đến thời điểm đó; nếu khách ngừng chi tiêu, chi tiêu rolling giảm dần theo thời gian → có thể bị tụt hạng khi hết hạn đánh giá định kỳ (VD: đánh giá lại mỗi đầu tháng hoặc mỗi 3 tháng — chọn 1 tần suất cố định khi viết engine để tránh tính lại mỗi ngày quá tốn công).
- **[v1]** Tích điểm: mỗi đơn hàng hoàn thành (không tính đơn hủy/hoàn) cộng điểm theo tỷ lệ % trên giá trị đơn (VD: 1 điểm / 10.000đ chi tiêu).
- **[v1]** `fact_customer_membership_history` ghi nhận mỗi lần đổi hạng (ngày hiệu lực, hạng cũ → hạng mới, lý do: đủ điều kiện lên hạng / hết hạn bị tụt hạng).
- **[v1]** Đổi điểm lấy quà (`fact_reward_redemption`) là sự kiện độc lập với order — khách có thể đổi điểm bất kỳ lúc nào miễn đủ điểm, không nhất thiết gắn với 1 đơn hàng cụ thể.
- **[v2+]** Thêm cơ chế điểm hết hạn (expiry) nếu không dùng sau X tháng — tăng độ phức tạp phân tích "điểm chết".

### 3.3 Hành vi mua hàng (input cho engine, không phải bảng riêng)
- **[v1]** Phân khúc khách hàng (văn phòng/sinh viên/gia đình) **không cần lưu thành cột cứng** trong `dim_customer`, mà thể hiện qua **pattern hành vi** khi sinh dữ liệu: giờ mua hàng, tần suất, giỏ hàng trung bình, độ nhạy khuyến mãi — logic này thuộc về Data Generation Engine, sẽ định nghĩa chi tiết ở tài liệu riêng (không phải BRS cấu trúc bảng).

---

## 4. DOMAIN: SALES / ORDER (Bán hàng)

### 4.1 Cấu trúc đơn hàng
- **[v1]** 1 đơn hàng (`fact_order`) luôn thuộc về đúng 1 store, 1 channel, có thể có hoặc không có customer_id.
- **[v1]** `order_type` (dine-in/takeaway/delivery) có tương quan với `channel`: kênh Grab/Shopee/Be/GreenSM → luôn là `delivery`; kênh App riêng → có thể `takeaway` (khách đặt trước rồi ra lấy) hoặc `delivery` (nếu app hỗ trợ ship); kênh Tại chỗ (POS) → `dine-in` hoặc `takeaway`.
- **[v1]** Trạng thái đơn: `completed` (đa số), `canceled` (hủy trước khi hoàn thành — không tính doanh thu, không trừ kho, không cộng điểm), `refunded` (đã hoàn thành nhưng hoàn tiền sau — cần logic đảo ngược ảnh hưởng đến kho/điểm/doanh thu).
- **[v1]** Tỷ lệ canceled/refunded nên nhỏ nhưng khác 0 (VD: 1-3% tổng đơn) — tạo dữ liệu thực tế cho phân tích chất lượng vận hành, không phải toàn bộ đơn đều hoàn hảo.

### 4.2 Kênh bán & tỷ trọng
- **[v1]** Tỷ trọng kênh: Tại chỗ ~50%, App riêng ~20%, Giao hàng ~30% (tổng của Grab+ShopeeFood+GreenSM+BeFood) — đây là baseline trung bình toàn hệ thống; **tỷ trọng thực tế theo từng store nên dao động quanh baseline này** (không ép cứng y hệt cho cả 25 store) vì store ở vị trí khác nhau (gần văn phòng vs gần khu dân cư) sẽ có cơ cấu kênh khác nhau — đây là 1 phần của "Store Profile Logic".
- **[v1]** Trong nhóm Giao hàng, chia tỷ trọng tương đối giữa 4 platform (không cần bằng nhau — Grab/ShopeeFood thường chiếm thị phần lớn hơn GreenSM/BeFood theo thực tế thị trường Việt Nam).
- **[v2+]** Thêm phí hoa hồng platform (commission %) khác nhau theo từng đối tác giao hàng — ảnh hưởng đến biên lợi nhuận thực nhận, phục vụ phân tích "kênh nào thực sự lời nhất" (không chỉ nhìn doanh thu gộp).

### 4.3 Giá & Discount
- **[v1]** `fact_order_item.unit_price` lấy theo giá `dim_product_variant` tại **thời điểm bán** (không phải giá hiện tại) — cần cơ chế versioning giá đơn giản nếu giá sản phẩm có thay đổi trong 3 năm (VD: tăng giá 1 lần/năm do lạm phát nguyên liệu).
- **[v1]** Giảm giá có thể áp theo % trên tổng đơn, hoặc theo item cụ thể (BOGO) — ghi nhận ở `fact_order_discount`, liên kết `dim_campaign` nếu thuộc chiến dịch, hoặc NULL nếu là giảm giá tại chỗ không thuộc campaign chính thức (hiếm, VD: nhân viên áp mã lỗi/đền bù khách).

### 4.4 Seasonality & giờ cao điểm
- **[v1]** Order volume theo giờ trong ngày có 2 đỉnh: sáng (7h30-9h, dân văn phòng) và chiều-tối (16h-19h, sau giờ học/giờ tan làm) — áp dụng khác nhau theo store profile.
- **[v1]** Order volume theo mùa: cao điểm hè (tháng 4-8, đồ uống lạnh tăng), cao điểm dịp lễ Tết/Giáng sinh (doanh thu tăng đột biến kèm campaign), thấp điểm sau Tết (tháng 2-3, chi tiêu giảm).
- **[v1]** Thời tiết ảnh hưởng nhẹ đến tỷ lệ đồ uống nóng/lạnh theo mùa (không cần dữ liệu thời tiết thật, chỉ cần seasonal factor đơn giản theo tháng).

---

## 5. DOMAIN: MARKETING & CAMPAIGN

### 5.1 Loại campaign
- **[v1]** 4 loại: giảm giá theo % (VD: -20% toàn menu), mua 1 tặng 1 (BOGO), flash sale (khung giờ ngắn, VD: 14h-16h giảm sâu), campaign theo mùa/lễ (Tết, Giáng sinh, sinh nhật thương hiệu) — thời gian dài hơn, có thể kết hợp sản phẩm mới ra mắt.
- **[v1]** Campaign có phạm vi áp dụng: toàn hệ thống, hoặc giới hạn theo store/thành phố (VD: campaign khai trương chỉ áp dụng cho 1-2 store mới mở), hoặc giới hạn theo channel (VD: ưu đãi chỉ áp dụng khi đặt qua App riêng để thúc đẩy kênh này).

### 5.2 Hiệu ứng lên doanh số (uplift)
- **[v1]** Trong giai đoạn có campaign, order volume tại store/channel áp dụng cần **tăng so với baseline bình thường** (uplift %, mức tăng khác nhau theo loại campaign — flash sale tăng mạnh nhưng ngắn hạn, campaign theo mùa tăng vừa phải nhưng kéo dài) — đây là rule quan trọng để `fact_campaign_performance` (P2) có ý nghĩa phân tích thực.
- **[v2+]** Bảng `fact_campaign_performance` chính thức (đã đánh dấu P2 trong entity list) — lưu kết quả tổng hợp thay vì tính lại mỗi lần từ `fact_order`.
- **[v2+]** Mô phỏng hiệu ứng "cannibalization" (campaign hút doanh thu từ giai đoạn ngay sau đó do khách gom mua trong lúc giảm giá) — bài toán phân tích nâng cao cho DA giỏi hơn.

---

## 6. DOMAIN: INVENTORY & SUPPLY CHAIN (Kho vận)

### 6.1 Mô hình kho
- **[v1]** Kết hợp 2 nguồn (áp dụng cho **nguyên liệu pha chế đồ uống** — Cà phê/Trà/Đá xay/LTO): nguyên liệu chính (cà phê, trà, sữa, syrup cốt...) nhập từ **kho trung tâm** theo chu kỳ cố định (VD: hàng tuần); nguyên liệu phụ/tươi sống (sữa tươi, trái cây, một số topping) do **từng store tự đặt nhà cung cấp địa phương** theo chu kỳ ngắn hơn (VD: 2-3 lần/tuần).
- **[v1]** `dim_ingredient.source_type` phân biệt `central` vs `local` để engine biết áp dụng chu kỳ đặt hàng và supplier phù hợp.
- **[v1] [CHỐT]** `dim_warehouse`: **2 kho trung tâm theo miền** — Kho miền Bắc (phục vụ 10 store Hà Nội) và Kho miền Nam (phục vụ 10 store TP.HCM + 5 store Đà Nẵng). Vì Đà Nẵng không có kho riêng, lead time giao hàng nguyên liệu trung tâm cho 5 store ĐN cần dài hơn so với HCM (khoảng cách vận chuyển xa hơn) — đây là 1 điểm tạo khác biệt hợp lý giữa các store cùng nhận từ Kho miền Nam, và là input quan trọng cho Store Profile Logic (ĐN có thể có rủi ro stock-out/wastage cao hơn nếu dự báo nhập hàng không tốt).
- **[v1.2] [MỚI]** **Food/Retail/Merchandise KHÔNG đi qua mô hình kho trung tâm/địa phương ở trên.** 3 category này nhập trực tiếp từ **nhà cung cấp outsource** (không phân biệt central/local, chỉ có `source_type = outsource`), theo chu kỳ đặt hàng riêng (đề xuất: theo tuần, vì đều là hàng có hạn sử dụng dài hơn nguyên liệu tươi hoặc là hàng phi thực phẩm).

### 6.2 Ledger tồn kho — **[v1.2] Ledger kép (dual-grain)**
- **[v1] Nhánh đồ uống**: grain `(store × ingredient × ngày)` — đã chốt Kịch bản B. Mỗi ngày/store/ingredient có tối đa vài dòng transaction: `stock_in` (nhập từ purchase order), `stock_out_sales` (xuất do bán hàng, tổng hợp tiêu hao cả ngày từ toàn bộ order/recipe/modifier của ngày đó — **[DERIVED]** từ `fact_order_item` + `dim_recipe`), `adjustment`, `wastage`.
- **[v1.2] [MỚI] Nhánh Food/Retail/Merch**: grain `(store × variant × ngày)` — cùng cấu trúc ledger (`stock_in`/`stock_out_sales`/`adjustment`/`wastage`) nhưng dùng cột `variant_id` thay vì `ingredient_id`, vì tiêu hao là 1:1 (bán 1 SKU = xuất đúng 1 đơn vị variant đó, không qua recipe).
- **[v1]** Tồn kho tại bất kỳ thời điểm nào = tổng cộng dồn (running balance) của ledger — không lưu cột "tồn kho hiện tại" trực tiếp trong dimension, tránh dữ liệu không nhất quán.
- **[v1]** Cần đảm bảo logic **không cho tồn kho âm** trong engine sinh dữ liệu, áp dụng cho cả 2 nhánh.

### 6.3 Purchase Order
- **[v1]** Chu kỳ đặt hàng khác nhau theo `source_type`: nguyên liệu trung tâm đặt theo tuần/2 tuần với lead time dài hơn (3-5 ngày, đặc biệt ĐN); nguyên liệu địa phương đặt ngắn hơn (lead time 1-2 ngày); **[v1.2]** hàng outsource (Food/Retail/Merch) đặt theo tuần, lead time trung bình (2-4 ngày).
- **[v1]** Số lượng đặt hàng nên tương quan với tốc độ tiêu thụ trung bình gần đây của store đó (không random hoàn toàn) — để tồn kho không bị âm hoặc dư thừa vô lý.
- **[v1.2]** `fact_purchase_order_item` dùng CHECK constraint đảm bảo mỗi dòng chỉ điền đúng 1 trong 2 cột (`ingredient_id` HOẶC `variant_id`), không lẫn lộn 2 cơ chế nhập hàng.
- **[v2+]** Mô phỏng reorder point / safety stock chính thức thay vì đặt hàng theo lịch cố định.

### 6.4 Hao hụt (Wastage)
- **[v1]** Wastage xảy ra ngẫu nhiên nhưng có xu hướng cao hơn với nguyên liệu tươi sống (hạn sử dụng ngắn) và ở store có doanh thu thấp/tồn kho dư thừa (dự báo nhu cầu kém chính xác hơn) — đây chính là 1 business case điển hình: "store nào có wastage rate cao bất thường, vì sao?".

---

## 7. DOMAIN: HUMAN RESOURCES (Nhân sự)

### 7.1 Cơ cấu nhân sự
- **[v1]** Số lượng nhân viên/store **thay đổi theo quy mô cửa hàng** (diện tích, doanh thu kỳ vọng) — không cố định giống nhau cho cả 25 store, tương tự logic không phân tầng ở Domain Store.
- **[v1]** Vị trí công việc tối thiểu: Quản lý (1/store), Pha chế (2-4 tùy quy mô), Thu ngân/Phục vụ (2-5 tùy quy mô) — tỷ lệ pha chế:phục vụ có thể khác nhau tùy tỷ trọng kênh giao hàng (store nhiều đơn giao hàng cần nhiều pha chế hơn phục vụ tại bàn).
- **[v1]** Có turnover (nghỉ việc) — `dim_employee.termination_date` không NULL cho 1 phần nhân viên, với tỷ lệ turnover hợp lý theo ngành F&B (thường khá cao, có thể 30-50%/năm cho vị trí nhân viên thời vụ) — đây là nguồn business case về chi phí tuyển dụng/đào tạo lại.

### 7.2 Ca làm & chấm công
- **[v1]** `dim_shift` định nghĩa các ca chuẩn (VD: Ca sáng 6h-14h, Ca chiều 14h-22h, có thể thêm Ca gãy/part-time cho sinh viên giờ cao điểm) với lương/giờ hoặc lương/ca cố định + bonus (ca đêm muộn, ngày lễ).
- **[v1]** `fact_employee_shift` ghi nhận check-in/check-out **thực tế**, cho phép lệch so với giờ chuẩn của `dim_shift` (đi trễ, về sớm, hoặc làm thêm giờ - overtime) — tỷ lệ đi trễ nên có biến động hợp lý (VD: cao hơn vào thứ 2 đầu tuần, sau kỳ nghỉ lễ, hoặc ở 1 số store cụ thể để tạo pattern phân tích được).
- **[v1]** `fact_payroll` tổng hợp theo tháng từ `fact_employee_shift` + `dim_shift` (lương cơ bản theo số ca/giờ thực làm) + phụ cấp/thưởng (có thể gắn với KPI doanh thu store, hoặc thưởng lễ Tết) — **[DERIVED]**.
- **[v2+]** Phạt/trừ lương do vi phạm (đi trễ quá số lần cho phép) — tăng độ phức tạp chính sách nhân sự nếu cần.

---

## 8. DOMAIN: FINANCE (Tài chính & P&L)

### 8.1 Cấu trúc P&L theo store/tháng — **[DERIVED]**
- **[v1]** `fact_store_pnl_monthly` được tính (không sinh độc lập) từ:
  - Doanh thu = tổng `fact_order.net_amount` (đã trừ discount) của các đơn `completed` trong tháng, theo store.
  - COGS (giá vốn hàng bán) = tổng chi phí nguyên liệu tiêu hao, suy ra từ `fact_inventory` loại `stock_out_sales` × giá nhập nguyên liệu tương ứng (giá vốn trung bình hoặc giá nhập gần nhất — cần chọn phương pháp tính giá vốn nhất quán, đề xuất weighted average).
  - Chi phí lương = tổng `fact_payroll` của nhân viên thuộc store trong tháng.
  - Chi phí thuê = `store_lease.monthly_rent` áp dụng cho tháng đó.
  - Chi phí vận hành khác = tổng `fact_store_expense` trong tháng (điện nước, marketing local, bảo trì...).
  - Lợi nhuận = Doanh thu − COGS − Lương − Thuê − Chi phí khác.
- **[v1]** Bảng này chính là **sản phẩm đầu ra của pipeline ETL thực hành** (theo mong muốn của bạn) — sẽ viết thành script/module Python riêng chạy tổng hợp định kỳ (mô phỏng batch job cuối tháng), không phải sinh ngẫu nhiên.

### 8.2 Chi phí vận hành khác
- **[v1]** `dim_expense_category` tối thiểu gồm: điện nước, marketing chi phí địa phương (POSM, banner), bảo trì thiết bị, chi phí khác — mỗi khoản có tính chất cố định hoặc biến đổi nhẹ theo tháng (không cần quá phức tạp ở v1).

### 8.3 Giá trị đặc biệt cần lưu ý
- **[v1]** Vì có store outlier (nhỏ nhưng vị trí đẹp, rent cao), P&L của các store này cần thể hiện rõ **biên lợi nhuận mỏng hơn dù doanh thu không thấp** — đây là insight quan trọng nhất mà toàn bộ chuỗi logic Store Profile → Rent → P&L phải nhất quán tạo ra được.

---

## 9. DOMAIN: KPI & ANALYTICS SUPPORT

### 9.1 Date Dimension
- **[v1]** `dim_date` bao phủ toàn bộ khung thời gian dữ liệu (và nên mở rộng thêm biên trước/sau vài tháng để tính rolling metrics không bị thiếu) — đánh dấu ngày lễ/Tết Việt Nam (dùng để driver seasonality ở Domain Sales).

### 9.2 KPI tổng hợp hàng ngày — **[DERIVED]**
- **[v1]** `fact_kpi_daily_store` tối thiểu gồm: doanh thu, số đơn, AOV (giá trị đơn trung bình), số khách mới (customer đăng ký lần đầu hôm đó), food cost % (COGS/doanh thu ngày đó) — cũng là sản phẩm của pipeline tổng hợp, tương tự P&L nhưng ở tần suất ngày.
- **[v2+]** Thêm các KPI nâng cao: customer retention rate, repeat purchase rate, employee productivity (doanh thu/nhân viên), inventory turnover — khi entity đã mở rộng đủ dữ liệu hỗ trợ.

---

## 10. RÀNG BUỘC LIÊN DOMAIN (Cross-domain Consistency Rules)

Đây là các rule đảm bảo dữ liệu giữa các domain **khớp logic với nhau** — quan trọng nhất khi viết Data Generation Engine, vì sinh độc lập từng bảng sẽ dễ tạo ra dữ liệu vô lý.

1. **[v1]** Order chỉ được sinh trong khung giờ hoạt động của store (Domain 1 ↔ Domain 4).
2. **[v1]** Mỗi `fact_order_item` phải kích hoạt tiêu hao nguyên liệu tương ứng theo `dim_recipe` (điều chỉnh theo modifier) → cộng dồn vào `fact_inventory` (grain ngày) của store đó (Domain 2 ↔ Domain 4 ↔ Domain 6).
3. **[v1]** Đơn `canceled` KHÔNG được trừ kho, KHÔNG cộng điểm loyalty, KHÔNG tính vào doanh thu P&L. Đơn `refunded` phải có logic đảo ngược (hoàn điểm nếu đã cộng, không hoàn nguyên liệu đã tiêu hao thực tế nhưng trừ doanh thu) (Domain 4 ↔ Domain 3 ↔ Domain 8).
4. **[v1]** Nhân sự (`dim_employee.store_id`) phải tồn tại trước khi store có thể vận hành sinh order (không thể có order tại store chưa có nhân viên nào active).
5. **[v1]** Campaign đang hiệu lực → tăng order volume tại phạm vi áp dụng (Domain 5 ↔ Domain 4), đồng thời discount tương ứng phải xuất hiện trong `fact_order_discount`.
6. **[v1]** Store mới mở (trong vòng vài tháng đầu `open_date`) nên có doanh thu thấp hơn baseline dài hạn rồi tăng dần (ramp-up curve), phản ánh giai đoạn xây dựng khách hàng — không nên có doanh thu ổn định ngay từ ngày đầu.
7. **[v1]** Giai đoạn "chững lại" của toàn công ty (theo bối cảnh mục 0) cần thể hiện rõ ở **hầu hết store cũ** trong 6-12 tháng gần nhất của khung thời gian — tăng trưởng doanh thu chậm/đi ngang so với cùng kỳ năm trước, không phải tăng đều đặn suốt 3 năm.
8. **[v2+]** Liên kết `fact_employee_shift` (năng suất nhân viên thực tế) với KPI doanh thu store theo ca — phân tích năng suất lao động theo ca/theo nhân viên.

---

## 11. TỔNG HỢP CÁC RULE [v2+] — DANH SÁCH NÂNG CẤP CHO PHIÊN BẢN SAU

Ghi chú lại toàn bộ để không mất khi mở rộng entity list sang v2/v3:

| # | Rule nâng cấp | Domain liên quan | Entity mới cần bổ sung (nếu có) |
|---|---|---|---|
| 1 | `dim_recipe_modifier_impact` chuẩn hóa ảnh hưởng modifier→nguyên liệu vào DB thay vì hard-code | Product | `dim_recipe_modifier_impact` (đã có trong entity list P2) |
| 2 | `fact_campaign_performance` lưu kết quả campaign chính thức, không tính lại mỗi lần | Marketing | `fact_campaign_performance` (đã có, P2) |
| 3 | Mô phỏng hiệu ứng cannibalization của campaign lên giai đoạn liền sau | Marketing | — (logic trong engine) |
| 4 | Phí hoa hồng (commission %) khác nhau theo từng platform giao hàng | Sales | Thêm cột vào `dim_sales_channel` hoặc bảng `dim_channel_commission` |
| 5 | Cơ chế điểm loyalty hết hạn (expiry) | Customer | Thêm cột expiry vào `fact_loyalty_point_transaction` |
| 6 | Reorder point / safety stock tự động thay vì lịch đặt hàng cố định | Inventory | Thêm cột vào `dim_ingredient` hoặc bảng riêng `dim_reorder_policy` |
| 7 | `fact_inventory_snapshot` cuối ngày để tăng tốc truy vấn | Inventory | `fact_inventory_snapshot` (đã có, P2) |
| 8 | Phạt/trừ lương do vi phạm giờ giấc | HR | Thêm cột policy vào `dim_position` hoặc bảng `dim_hr_policy` |
| 9 | KPI nâng cao: retention, repeat purchase rate, employee productivity, inventory turnover | KPI/Analytics | Mở rộng `fact_kpi_daily_store` hoặc thêm bảng KPI chuyên biệt |
| 10 | Domain hoàn toàn mới: quản lý tài sản/thiết bị cửa hàng (máy pha cà phê, tủ lạnh...) — bảo trì, khấu hao | Mới | `dim_asset`, `fact_asset_maintenance` |
| 11 | Domain hoàn toàn mới: feedback/review khách hàng (rating, comment theo đơn hàng) | Mới | `fact_customer_review` |
| 12 | Modifier mở rộng cho Food (topping bánh, nóng/lạnh) | Product | Mở rộng `dim_modifier` phạm vi áp dụng |
| 13 | Landlord type / điều khoản phạt hợp đồng thuê | Store | Mở rộng `store_lease` |
| 14 | Đóng góp doanh thu theo nguồn "đặc biệt" cho store outlier (VD: sự kiện, đối tác gần đó) | Store/Sales | Có thể cần `fact_store_special_revenue_source` |

---
