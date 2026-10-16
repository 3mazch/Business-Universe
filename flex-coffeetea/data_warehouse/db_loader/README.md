# SQL Server dimension loader

Loader nạp 23 dimension CSV từ `data/dimension/full/` vào database `FlexCoffeeTea` theo thứ tự phụ thuộc khóa ngoại. Loader hiện chỉ nạp các dimensions thông qua `load_dimensions.py`.

## Điều kiện cần

- SQL Server và database `FlexCoffeeTea`; tạo database bằng [`schema/create_schema.sql`](../schema/create_schema.sql).
- CSV dimension đầy đủ; nếu chưa có, chạy `python src\data_generation\run_dimensions.py` từ thư mục `flex-coffeetea`.
- Microsoft ODBC Driver 17 hoặc 18 for SQL Server.
- Python packages:

```powershell
python -m pip install pandas pyodbc python-dotenv
```

## Cấu hình kết nối

Từ thư mục `flex-coffeetea`, sao chép template:

```powershell
Copy-Item data_warehouse\db_loader\.env.example data_warehouse\db_loader\.env
```

Thiết lập `DB_SERVER`, `DB_NAME` và `DB_TRUSTED=yes` để dùng Windows Authentication. Hoặc cấu hình `DB_USER` và `DB_PASSWORD` cho SQL Authentication. Để `DB_PORT` chưa đặt khi dùng default/named instance; không kết hợp port với tên named instance. Không commit file `.env`.

Kiểm tra kết nối:

```powershell
python data_warehouse\db_loader\db_config.py
```

## Chạy từ thư mục project

```powershell
# Nạp toàn bộ dimension
python data_warehouse\db_loader\load_dimensions.py

# Kiểm tra CSV, không ghi vào database
python data_warehouse\db_loader\load_dimensions.py --dry-run

# Xóa dữ liệu hiện có rồi nạp lại
python data_warehouse\db_loader\load_dimensions.py --truncate

# Chỉ nạp một bảng
python data_warehouse\db_loader\load_dimensions.py --table dim_store

# Kiểm tra sau khi nạp
python data_warehouse\db_loader\validate_dimensions.py
```

`--table` có thể không đáp ứng khóa ngoại nếu các bảng phụ thuộc chưa được nạp; lần nạp đầu nên chạy toàn bộ loader. Xem `.env.example` để biết các biến cấu hình được hỗ trợ.
