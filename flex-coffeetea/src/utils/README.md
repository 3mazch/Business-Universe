# Shared utilities

`utils/` chứa các module dùng chung cho engine sinh dữ liệu; đây không phải pipeline chạy độc lập.

| Module | Vai trò |
|---|---|
| `constants.py` | Cửa sổ mô phỏng, tham số nghiệp vụ và đường dẫn dữ liệu đầu vào/đầu ra |
| `date_utils.py` | Duyệt tháng, tính ngày, lịch mùa vụ và thời điểm đơn hàng |
| `seed_utils.py` | Tạo random generator có seed tái lập, theo cửa hàng và tháng hoặc dùng chung |
| `store_utils.py` | Đọc store/operating hours; tính trạng thái, độ trưởng thành và doanh thu cửa hàng |

Engine Sale/Orders dùng các tiện ích này để giữ cấu hình và logic nhất quán. Chạy pipeline từ [`data_generation/`](../data_generation/README.md); các module trong `utils/` không cần chạy trực tiếp.
