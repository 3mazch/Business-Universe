# Data

Thư mục chứa sample đã lưu trong repository và các file được tạo bởi pipeline:

| Đường dẫn | Nội dung |
|---|---|
| `dimension/sample/` | CSV mẫu cho các dimension, tối đa 100 dòng mỗi file |
| `dictionary/store_profiles_v1.json` | Hồ sơ mô phỏng của các cửa hàng |
| `dimension/full/` | CSV dimension đầy đủ, được tạo khi chạy pipeline |
| `dimension/temp/` | CSV trung gian trong quá trình sinh dimension |
| `synthetic/sale_orders/full/` | Sale/Orders CSV phân vùng theo cửa hàng/tháng và      batch_manifest thống kê |
| `synthetic/sale_orders/sample/` | CSV cho 1 store mẫu|

Các thư mục con bên trong `dimension/` và `synthetic/sale_orders` được tạo ra đầy đủ khi chạy generator và không có sẵn trong repository. Từ thư mục `flex-coffeetea`, chạy dimension trước rồi mới chạy Sale/Orders:

```powershell
python src\data_generation\run_dimensions.py
python src\data_generation\run_generation.py
```

Xem [hướng dẫn data generation](../src/data_generation/README.md) để biết dependencies, đầu vào và tùy chọn chạy.
