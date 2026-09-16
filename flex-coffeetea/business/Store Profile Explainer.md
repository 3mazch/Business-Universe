# FLEX COFFEE & TEA — STORE PROFILE LOGIC (Bước 1)

---

## 1. Ý tưởng cốt lõi

Không gán nhãn Flagship/Standard/Kiosk. Mỗi store có 3 thuộc tính **đầu vào độc lập**:
`city` (thành phố) × `location_tier` (vị trí) × `size_m2` (diện tích)

Từ tổ hợp 3 biến này, các thuộc tính **đầu ra (derived)** được tính bằng công thức có nhiễu ngẫu nhiên:
`monthly_rent` → `monthly_revenue_baseline` → `staff_count` → `channel_mix`

## 2. Chi tiết từng thuộc tính

### 2.1 Vị trí (`location_tier`)
| Tier | Ý nghĩa | Hệ số rent | Hệ số doanh thu/m2 | Tỷ trọng trong 25 store |
|---|---|---|---|---|
| `prime` | Mặt phố lớn, trung tâm, đông người qua lại | ×2.3 | ×1.6 | ~24% |
| `standard` | Mặt phố nhỏ / khu dân cư đông | ×1.3 | ×1.15 | ~48% |
| `secondary` | Hẻm / xa trung tâm / khu mới phát triển | ×0.75 | ×0.80 | ~28% |

→ Vị trí đẹp thì rent cao NHƯNG doanh thu/m2 cũng cao hơn tương ứng — logic này đúng thực tế (không phải cứ đẹp là lời hơn, mà là đánh đổi).

### 2.2 Thành phố (`city`)
| Thành phố | Hệ số rent | Hệ số doanh thu | Kho phục vụ |
|---|---|---|---|
| Hà Nội | ×1.15 | ×1.05 | Kho miền Bắc |
| TP.HCM | ×1.20 | ×1.10 | Kho miền Nam |
| Đà Nẵng | ×0.85 | ×0.80 | Kho miền Nam (xa hơn — lead time dài hơn) |

### 2.3 Rent — công thức
```
monthly_rent = size_m2 × 550,000đ × city_rent_index × location_tier_multiplier × noise(0.85–1.15)
```
KHÔNG tuyến tính đơn giản với diện tích — vì nhân thêm 2 hệ số độc lập (thành phố, vị trí) + nhiễu ngẫu nhiên, nên 2 store cùng diện tích có thể lệch rent 2-3 lần.

### 2.4 Doanh thu baseline — công thức
```
revenue_per_m2 = 9,500,000đ × city_revenue_index × location_footfall_multiplier × noise(0.88–1.12)
monthly_revenue_baseline = revenue_per_m2 × size_m2
```
Đây là **doanh thu baseline khi store đã ổn định** (chưa gồm seasonality/campaign/ramp-up — sẽ áp dụng ở bước sinh transaction data).

### 2.5 Outlier có chủ đích (nhỏ + vị trí đẹp)
- Điều kiện: `location_tier = prime` VÀ `size_m2 ≤ 90`.
- Nếu được chọn làm outlier: nhân thêm hệ số rent ×1.3–1.6 (rent cao bất thường so với diện tích) VÀ hệ số doanh thu/m2 ×1.4–1.8 (bù lại bằng lưu lượng khách cao), đồng thời **giảm tỷ trọng dine-in, tăng app/giao hàng** (do ít chỗ ngồi).
- Kết quả trong 25 store: **2 store outlier** — HN-02 và HN-04 (đều Hà Nội, prime, ~75m², rent/m2 và doanh thu/m2 cao vượt trội các store cùng thành phố).
- Ý nghĩa phân tích: đây là case "doanh thu cao nhưng biên lợi nhuận mỏng vì rent chiếm tỷ trọng lớn" — business case điển hình cho P&L sau này.

### 2.6 Nhân sự (`staff_count_baseline`)
```
base_staff = size_m2 / 11.5
staff_count = base_staff × (0.7 + 0.3 × revenue_factor)   [giới hạn 8–24 người]
```
→ Không chỉ phụ thuộc diện tích mà còn điều chỉnh theo doanh thu kỳ vọng — store outlier nhỏ nhưng doanh thu cao vẫn có staff tương đối cao so với diện tích (phản ánh mật độ phục vụ dày hơn).

### 2.7 Cơ cấu kênh bán (`channel_mix`)
Baseline hệ thống: Dine-in 50% / App 20% / Delivery 30%.
- `prime`: dine-in & app nhích lên (khách văn phòng, khách vãng lai order tại chỗ nhiều).
- `secondary`: delivery nhích lên (xa, khách ở nhà đặt online nhiều hơn).
- Outlier nhỏ+đẹp: dine-in giảm mạnh hơn nữa (ít chỗ ngồi), bù bằng app + delivery.

### 2.8 Vòng đời cửa hàng (mở cửa theo làn sóng)
4 làn sóng mở cửa (2020–2024), mật độ giảm dần về sau — phản ánh đúng "tăng trưởng nóng rồi chững lại":
| Làn sóng | Thời gian | Tỷ trọng số store mở |
|---|---|---|
| 1 | 06/2020–03/2021 | 24% |
| 2 | 06/2021–06/2022 | 36% (đỉnh điểm mở rộng) |
| 3 | 09/2022–06/2023 | 28% (mở rộng sang ĐN) |
| 4 | 09/2023–03/2024 | 12% (chậm lại rõ rệt) |

### 2.9 Sự kiện vòng đời đặc biệt (lifecycle events)
Để phản ánh giai đoạn "chững lại", chọn ngẫu nhiên trong nhóm store có doanh thu/m² thấp nhất (không phải outlier tốt):
- **1 store đóng tạm** (`temporarily_closed_recent`) trong ~45–75 ngày, gần cuối khung dữ liệu (sửa chữa/đổi mặt bằng) → kết quả: **DN-05**.
- **1 store đóng hẳn** (`closed`) khoảng 200–400 ngày trước cuối khung dữ liệu (hiệu quả kém, công ty quyết định rút lui) → kết quả: **HCM-02**.

---

## 3. Kết quả tổng quan 25 store

| Chỉ số | Giá trị |
|---|---|
| Tổng số store | 25 (HN 10 / HCM 10 / ĐN 5) |
| Store outlier (nhỏ+đẹp) | 2 (HN-02, HN-04) |
| Store đóng hẳn | 1 (HCM-02) |
| Store đóng tạm gần đây | 1 (DN-05) |
| Rent trung bình/tháng | ~105 triệu đ (dao động 48tr–185tr) |
| Doanh thu baseline trung bình/tháng | ~1.45 tỷ đ (dao động 800tr–2.2 tỷ) |
| Staff trung bình | ~13 người/store (dao động 8–21) |

**Nhận xét nhanh (sanity check)**: TP.HCM có doanh thu baseline trung bình cao nhất (city_revenue_index cao nhất), Đà Nẵng thấp nhất — khớp kỳ vọng thực tế. 2 store outlier có `revenue_per_m2` cao gấp ~2 lần store thường cùng thành phố nhưng `rent` cũng cao tương ứng — đúng mục tiêu "biên lợi nhuận mỏng dù doanh thu tốt".

---

## 4. Các trường dữ liệu output (dùng làm input cho Bước 3 — sinh Dimension data)

| Cột | Ý nghĩa | Dùng ở bước nào tiếp theo |
|---|---|---|
| `store_id`, `store_code`, `store_name` | Định danh | `dim_store` |
| `city`, `warehouse_region` | Vị trí địa lý, kho phục vụ | `dim_store`, liên kết `fact_purchase_order` |
| `location_tier`, `size_m2` | Thuộc tính vật lý | `dim_store`, input tính rent/doanh thu |
| `open_date`, `status`, `closed_date`, `temp_closed_period` | Vòng đời | `dim_store`, điều kiện sinh order theo thời gian |
| `is_outlier_small_prime` | Cờ đánh dấu outlier | Dùng để kiểm tra/validate business case ở Bước 6 |
| `monthly_rent_vnd` | Baseline rent | `store_lease.monthly_rent` (có thể thêm escalation theo chu kỳ tái ký ở bước sau) |
| `monthly_revenue_baseline_vnd`, `revenue_per_m2_vnd` | Baseline doanh thu | Input chính cho engine sinh `fact_order` (Bước 4) — áp thêm seasonality/ramp-up/campaign lên baseline này |
| `staff_count_baseline` | Số nhân sự mục tiêu | Input sinh `dim_employee` (Bước 3) |
| `channel_mix_*` | Tỷ trọng kênh | Input phân bổ `fact_order.channel_id` khi sinh transaction (Bước 4) |

---

