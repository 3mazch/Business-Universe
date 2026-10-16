# Flex Coffee & Tea

Flex Coffee & Tea là một business universe F&B giả lập để thực hành data generation, data warehousing và phân tích. Mô hình gồm 25 cửa hàng tại Hà Nội, TP.HCM và Đà Nẵng; khoảng thời gian mô phỏng từ 08/2023 đến 07/2026.

## Hiện có

- Tài liệu nghiệp vụ và mô hình 39 bảng trên 9 domain.
- SQL Server schema và data dictionary.
- Pipeline sinh 23 dimension, cùng engine mô phỏng dữ liệu Sale/Orders theo thời gian.
- Sample CSV cho dimension và JSON hồ sơ cửa hàng; dữ liệu đầy đủ được sinh tại chỗ, không lưu trong repository.
- Loader SQL Server hiện hỗ trợ nạp dimension; Sale/Orders được xuất thành file CSV, chưa có loader fact trong thư mục này.

## Cấu trúc

| Thư mục | Nội dung |
|---|---|
| [`business/`](business/) | Business requirements, entity list, store profile |
| [`data/`](data/) | Sample dimensions, store profiles và dữ liệu sinh ra |
| [`data_warehouse/`](data_warehouse/) | SQL schema, data dictionary và loader |
| [`src/data_generation/`](src/data_generation/README.md) | Sinh dimension và Sale/Orders |
| [`src/utils/`](src/utils/README.md) | Cấu hình và hàm dùng chung cho sinh dữ liệu |

## Chạy pipeline

Từ thư mục `flex-coffeetea`, tạo môi trường và cài dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install pandas numpy
```

Sinh dimension trước, sau đó mới mô phỏng Sale/Orders:

```powershell
python src\data_generation\run_dimensions.py
python src\data_generation\run_generation.py
```

Các lệnh này tạo dữ liệu đầy đủ tại `data/dimension/full/` và Sale/Orders tại `data/synthetic/sale_orders/`. Hướng dẫn chi tiết và các tùy chọn có trong [README data generation](src/data_generation/README.md).

## Database

Chạy [`data_warehouse/schema/create_schema.sql`](data_warehouse/schema/create_schema.sql) trong SSMS hoặc Azure Data Studio để tạo schema. Để nạp dimension vào SQL Server, xem [hướng dẫn db_loader](data_warehouse/db_loader/README.md).

## Tài liệu nghiệp vụ

- [Business Requirements Specification](business/Business_Requirements_Specification_(BRS).md)
- [Entity List](business/Entity_List.md)
- [Store Profile Explainer](business/Store%20Profile%20Explainer.md)
