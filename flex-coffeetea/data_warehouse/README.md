# Data warehouse

Thư mục này chứa thiết kế SQL Server cho Flex Coffee & Tea: **39 bảng thuộc 9 domain**, từ Store, Product, Sales và Inventory đến Finance, KPI.

## Nội dung

- [`schema/create_schema.sql`](schema/create_schema.sql): DDL T-SQL tạo database `FlexCoffeeTea` nếu chưa tồn tại.
- [`data_dictionary.md`](data_dictionary.md): kiểu dữ liệu, khóa, ràng buộc và mô tả từng bảng/cột.
- [`db_loader/`](db_loader/README.md): cấu hình kết nối, nạp và kiểm tra data từ CSV.

## Tạo schema và nạp dữ liệu

1. Mở SQL Server Management Studio hoặc Azure Data Studio, kết nối SQL Server và chạy toàn bộ `schema/create_schema.sql`.
2. Tạo dữ liệu dimension đầy đủ bằng `src\data_generation\run_dimensions.py` từ thư mục `flex-coffeetea`.
3. Làm theo [hướng dẫn loader](db_loader/README.md) để cấu hình kết nối và nạp dimension theo thứ tự khóa ngoại.

Schema định nghĩa cả bảng dimension và fact; loader hiện có chỉ nạp dimension. Sale/Orders hiện được sinh thành CSV, không được nạp bởi loader này.

## Thiết kế nghiệp vụ

Schema phản ánh mô hình và quy tắc trong [Business Requirements Specification](../business/Business_Requirements_Specification_(BRS).md) và [Entity List](../business/Entity_List.md). Bảng P&L tháng và KPI ngày là bảng vật lý dành cho các bước ETL sau, không phải view.
