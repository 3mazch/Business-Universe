# data_warehouse/

Schema database (SQL Server / T-SQL) cho dự án **Flex Coffee & Tea** — chuỗi F&B giả lập dùng để luyện phân tích dữ liệu end-to-end (thiết kế DDL → sinh dữ liệu → ETL → dashboard).

> Đây là README riêng cho folder schema. Rule nghiệp vụ đứng sau các bảng nằm ở `../business/`; README tổng quan toàn dự án nằm ở gốc repo.

---

## Nội dung folder

| File | Mô tả |
|---|---|
| `create_schema.sql` | DDL đầy đủ — 39 bảng trên 9 domain, chạy 1 lần để dựng toàn bộ database |
| `data_dictionary.md` | Tra cứu chi tiết từng bảng/cột: kiểu dữ liệu, khóa, ràng buộc, giá trị hợp lệ — sinh trực tiếp từ DDL |

## Cách chạy

1. Mở SSMS hoặc Azure Data Studio, kết nối tới SQL Server instance.
2. Chạy toàn bộ `create_schema.sql` (F5). Script tự tạo database `FlexCoffeeTea` nếu chưa tồn tại.
3. Nạp dữ liệu theo đúng thứ tự phụ thuộc khóa ngoại: **Dimension trước, Fact sau** (VD: `dim_store` → `dim_product_variant` → `dim_recipe` → `fact_order` → ...). Script sinh dữ liệu nằm ở folder khác của repo.

## Kiến trúc schema — 9 domain, 39 bảng

```
1. Store                    3 bảng   — dim_store, store_lease, store_operating_hours
2. Product                  6 bảng   — category → product → variant, modifier, recipe (BOM)
3. Customer & Membership    6 bảng   — customer, membership tier, loyalty points
4. Sales / Order            6 bảng   — order, order_item, payment, discount
5. Marketing & Campaign     2 bảng   — campaign, campaign product scope
6. Inventory & Supply Chain 6 bảng   — ingredient, supplier, warehouse, PO, inventory ledger
7. Human Resources          5 bảng   — position, shift, employee, payroll
8. Finance                  3 bảng   — expense, P&L theo tháng (derived)
9. KPI & Analytics Support  2 bảng   — date dimension, KPI theo ngày (derived)
```

Chi tiết từng bảng/cột: xem `data_dictionary.md`.

## Vài quyết định thiết kế đáng chú ý

- **`dim_store` không có cột phân loại Flagship/Standard/Kiosk.** Quy mô, doanh thu, nhân sự của mỗi store là *kết quả suy ra* từ tổ hợp `city × location_tier × size_m2` (xem Store Profile Logic), không gán nhãn cứng trước — để phản ánh đúng cách một chuỗi F&B thật vận hành.
- **Ledger tồn kho dual-grain.** `fact_inventory_transaction` dùng chung 1 cấu trúc ledger cho 2 nhánh khác nhau: đồ uống pha chế theo BOM (`ingredient_id`) và Food/Retail/Merchandise nhập nguyên SKU (`variant_id`) — CHECK constraint đảm bảo mỗi dòng chỉ dùng đúng 1 cơ chế.
- **Slowly-changing theo nhu cầu thực tế**, không SCD hóa toàn bộ: `store_lease` tách khỏi `dim_store` vì rent đổi theo chu kỳ tái ký; `dim_product_variant` có `effective_from/to` vì giá bán đổi theo thời gian; `fact_customer_membership_history` lưu lịch sử đổi hạng thay vì ghi đè.
- **Bảng derived là bảng vật lý, không phải view.** `fact_store_pnl_monthly` và `fact_kpi_daily_store` được tính từ các fact khác nhưng lưu riêng — mô phỏng đúng 1 pipeline ETL/batch job thực tế thay vì tính lại mỗi lần truy vấn.

## Liên kết

- Rule nghiệp vụ đầy đủ: `../business/Business_Requirements_Specification.md`
- Mô tả entity & quan hệ ở mức khái niệm: `../business/Entity_List.md`
- Logic sinh 25 store (rent, doanh thu, nhân sự, outlier): `../business/Store Profile Explainer.md`
