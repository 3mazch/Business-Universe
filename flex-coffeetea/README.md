# Flex Coffee & Tea — Mô phỏng Phân tích Dữ liệu F&B

Flex Coffee & Tea là một hệ sinh thái dữ liệu giả lập end-to-end cho một chuỗi F&B quy mô vừa. Dự án được xây dựng như một sandbox thực hành cho Data Analyst, Data Engineer và Analytics Engineer trong các bài toán mô hình hóa dữ liệu, data generation, ETL và Business Intelligence.

## Trạng thái hiện tại: Step 1 — Foundation

Step 1 xác lập “vũ trụ” vận hành của Flex Coffee & Tea trước khi sinh dữ liệu. Ở giai đoạn này, repository đã có:

- Bộ business rules và các giả định vận hành của doanh nghiệp.
- Danh sách entity, quan hệ giữa các domain và grain của các fact table.
- Schema SQL Server/T-SQL gồm **39 bảng trên 9 domain**.
- Data dictionary được sinh dựa trên DDL để tra cứu cột, khóa, kiểu dữ liệu và ràng buộc.

Chưa có dữ liệu dimension, transaction hay engine sinh dữ liệu trong phạm vi Step 1. Các bảng derived như P&L theo tháng và KPI theo ngày đã được chuẩn bị trong schema để phục vụ các bước ETL sau này.

## Bối cảnh mô phỏng

Flex Coffee & Tea là chuỗi 100% công ty tự vận hành, kinh doanh cà phê, trà, đồ uống đá xay, sản phẩm theo mùa (LTO), food, retail đóng gói và merchandise.

- **25 cửa hàng**: Hà Nội 10, TP.HCM 10, Đà Nẵng 5.
- **Khung dữ liệu mục tiêu**: khoảng 3 năm, từ 08/2023 đến 07/2026.
- **Mô hình cửa hàng**: không gán nhãn Flagship/Standard/Kiosk cứng; doanh thu, tiền thuê, nhân sự và cơ cấu kênh được suy ra từ thành phố, vị trí và diện tích.
- **Business cases chính**: store outlier nhỏ nhưng ở vị trí prime, giai đoạn tăng trưởng chững lại, store đóng tạm/đóng hẳn, seasonality, campaign, tồn kho và P&L.

## Nội dung repository

### 1. Business documentation

Thư mục [`business/`] chứa các quy tắc nghiệp vụ làm nguồn tham chiếu cho schema và các engine ở bước sau:

- [`Business_Requirements_Specification_(BRS).md`] đặc tả mô hình kinh doanh, sản phẩm, cửa hàng, khách hàng, bán hàng, marketing, tồn kho, nhân sự và tài chính.
- [`Entity_List.md`]: danh sách 39 entity, phân theo 9 domain, cùng các quan hệ và ước tính khối lượng dữ liệu.
- [`Store Profile Explainer.md`] logic tạo profile cho 25 cửa hàng, gồm rent, doanh thu baseline, staffing, channel mix và các lifecycle event.

### 2. Data warehouse

Thư mục [`data_warehouse/`] chứa thiết kế database:

- [`/schema/create_schema.sql`] DDL SQL Server/T-SQL, tự tạo database `FlexCoffeeTea` nếu database chưa tồn tại.
- [`data_dictionary.md`] tra cứu chi tiết từng bảng và cột.
- [`data_warehouse/README.md`] hướng dẫn chạy schema và các quyết định thiết kế quan trọng.

## Cách sử dụng ở Step 1

1. Đọc [`BRS`] để nắm rule nghiệp vụ và phạm vi mô phỏng.
2. Đọc [`Entity List`] để hiểu entity, quan hệ và grain dữ liệu.
3. Đọc [`Store Profile Explainer`] để hiểu cách profile cửa hàng tác động đến rent, doanh thu và nhân sự.
4. Mở SQL Server Management Studio hoặc Azure Data Studio, kết nối tới SQL Server và chạy toàn bộ [`create_schema.sql`] để có được database đúng với schema đã có (không bao gồm P2).


## Lộ trình dự kiến tiếp theo

- **Step 2 — Dimension Generation**: sinh và nạp master data cho store, product, customer, employee, supplier và các dimension liên quan vào database.
- **Step 3 — Fact Transaction Simulation**: sinh order, payment, inventory, payroll, expense và các sự kiện theo ngày; sau đó nạp dữ liệu vào database.
- **Các bước ETL tiếp theo**
