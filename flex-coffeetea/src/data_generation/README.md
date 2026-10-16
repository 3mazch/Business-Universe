# Data generation

Scripts trong thư mục này tạo dimension và mô phỏng dữ liệu Sale/Orders cho Flex Coffee & Tea. Generator xuất file; không kết nối hay nạp dữ liệu vào SQL Server.

## Các pipeline

- `run_dimensions.py`: chạy lần lượt sáu script trong `dimension/` để tạo các dimension, file trung gian và hồ sơ cửa hàng.
- `run_generation.py`: tạo Sale/Orders theo dimension đầy đủ, ghi CSV phân vùng theo cửa hàng/tháng cùng manifest vào `data/synthetic/sale_orders/`.
- `merge_check.py`: kiểm tra manifest của một lần chạy đầy đủ; không gộp các phân vùng thành một file.

Dimension được ghi vào `data/dimension/full/`, `data/dimension/sample/` (tối đa 100 dòng mỗi file) và `data/dimension/temp/`. Hồ sơ cửa hàng dạng JSON được ghi vào `data/dictionary/`.

## Cài đặt và chạy

Từ thư mục `flex-coffeetea`, cài Python 3 cùng dependencies:

```powershell
python -m pip install pandas numpy
```

Sinh dimension trước. Sale/Orders yêu cầu các CSV đầy đủ trong `data/dimension/full/`:

```powershell
python src\data_generation\run_dimensions.py
python src\data_generation\run_generation.py
```

Có thể giới hạn lần chạy theo năm/tháng hoặc store:

```powershell
python src\data_generation\run_generation.py --year 2025 --month 1
python src\data_generation\run_generation.py --store 1 2
```

Xem toàn bộ tùy chọn bằng `python src\data_generation\run_generation.py --help`. Chạy lại dimensions sẽ tạo lại đầu ra; Sale/Orders hỗ trợ kiểm tra trước và giới hạn phạm vi, còn `merge_check.py` chỉ chấp nhận manifest của lần chạy toàn phạm vi.
