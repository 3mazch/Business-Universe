# Data Generation

Thư mục này chứa các script Python tạo dữ liệu dimension giả lập cho Flex Coffee & Tea. `run_dimensions.py` chạy lần lượt sáu script trong `dimension/`:

- `generate_store_profile.py`: tạo 25 cửa hàng và hồ sơ cửa hàng.
- `generate_baverage_dimensions.py`: tạo dimension sản phẩm đồ uống, nguyên liệu, công thức và modifier.
- `generate_food_retail_merch.py`: tạo sản phẩm food, retail, merchandise và nhà cung cấp outsource.
- `generate_hr_dimensions.py`: tạo vị trí, ca làm và nhân viên dựa trên dữ liệu cửa hàng.
- `generate_minor_dimensions.py`: tạo ngày, kênh bán hàng, campaign và khách hàng.
- `generate_missing_dimensions.py`: hợp nhất/cập nhật các dimension còn lại như sản phẩm, kho, nhà cung cấp, membership, reward, lease và giờ hoạt động cửa hàng.

Các hàm dùng chung nằm trong `config.py`, gồm seed ngẫu nhiên và đường dẫn lưu dữ liệu. CSV đầy đủ được ghi vào `data/dimension/full/`; các file trung gian vào `data/dimension/temp/`; bản mẫu tối đa 100 dòng vào `data/dimension/sample/`. Hồ sơ cửa hàng dạng JSON được ghi vào `data/dictionary/`. Chạy lại script sẽ tạo hoặc ghi đè các file đầu ra. Pipeline chỉ sinh file, không kết nối hay nạp dữ liệu vào SQL Server.

## Cài đặt và chạy

Cần cài Python 3 và hai thư viện `pandas`, `numpy`. Mở PowerShell tại thư mục `flex-coffeetea` rồi chạy:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install pandas numpy
python src\data_generation\run_dimensions.py
```

Sau khi chạy thành công, xem dữ liệu đầy đủ trong `data/dimension/full/` (Hiện tại chỉ show bản sample). Nếu PowerShell không cho phép kích hoạt virtual environment, có thể bỏ qua dòng Activate và gọi trực tiếp `.\.venv\Scripts\python.exe` thay cho `python` ở hai lệnh cuối.
