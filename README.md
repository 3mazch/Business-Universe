# Business Universe

Business Universe là dự án mô phỏng dữ liệu doanh nghiệp theo ngành, với ngữ cảnh vận hành và quy tắc nghiệp vụ để thực hành Data Analysis, Data Engineering, Analytics Engineering và BI.

## Vũ trụ hiện có

- [Flex Coffee & Tea](flex-coffeetea/README.md): mô phỏng chuỗi F&B, gồm tài liệu nghiệp vụ, schema SQL Server, sinh dimension và mô phỏng dữ liệu Sale/Orders.

## Nguyên tắc

- Bắt đầu từ mô hình và quy tắc kinh doanh, sau đó thiết kế entity, grain và schema.
- Sinh dữ liệu nhất quán theo quan hệ và thời gian, có cả biến động và tình huống ngoại lệ.
- Tách dữ liệu gốc khỏi dữ liệu derived để hỗ trợ truy nguyên và phân tích.
- Tổ chức mỗi ngành thành một business universe độc lập, có thể mở rộng.

## Cấu trúc

```text
Business-Universe/
├── README.md
└── flex-coffeetea/
    ├── business/         # Quy tắc và mô hình nghiệp vụ
    ├── data/             # Sample và dữ liệu được sinh
    ├── data_warehouse/   # Schema, data dictionary, loader
    └── src/              # Data generation và tiện ích dùng chung
```

## Bắt đầu

Đọc [README của Flex Coffee & Tea](flex-coffeetea/README.md) để xem phạm vi hiện tại, cấu trúc và hướng dẫn chạy các pipeline.
