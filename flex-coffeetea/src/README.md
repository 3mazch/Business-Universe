# Source Code (`src/`)

Thư mục `src/` chứa mã nguồn tạo và xử lý dữ liệu cho dự án Flex Coffee & Tea. Hiện tại, thư mục này có `data_generation/`, dùng để sinh các dimension giả lập và các file CSV/JSON phục vụ những bước tiếp theo. Xem [hướng dẫn data_generation](data_generation/README.md) để biết nội dung pipeline và cách chạy.

## Định hướng mở rộng

Khi dự án phát triển, có thể bổ sung các module theo trách nhiệm:

- `utils/`: các hàm dùng chung như đọc/ghi file, cấu hình, logging và tiện ích dữ liệu; chỉ đưa vào đây logic thực sự được nhiều module dùng chung.
- `validation/`: kiểm tra cấu trúc cột, kiểu dữ liệu, khóa, tính duy nhất, quan hệ tham chiếu và các quy tắc nghiệp vụ trước khi nạp dữ liệu.
- `fact_generation/`: mô phỏng giao dịch và sự kiện theo thời gian như order, payment, inventory, payroll và expense.
- `data_loading/` hoặc `etl/`: nạp dữ liệu vào SQL Server và điều phối các bước biến đổi khi pipeline ETL được triển khai.

Các module trên là định hướng, chưa có trong `src/` hiện tại. Mục tiêu là phát triển nguồn dữ liệu có thể tái lập, kiểm tra được và phù hợp schema/data dictionary, từ dimension generation đến mô phỏng fact và phân tích BI.
