## Thư mục `data`

Thư mục này chứa các dữ liệu phục vụ cho hệ thống Flex CoffeeTea. Nội dung được phân chia theo loại dữ liệu:

- `dimension/`: chứa các bảng dimension, hiện bao gồm dữ liệu mẫu cho các thực thể như cửa hàng, sản phẩm, khách hàng, nhân viên và các danh mục liên quan.
- Sẽ có `fact/`: dự kiến sẽ được bổ sung trong tương lai để chứa các bảng fact khi đã có dữ liệu nghiệp vụ phù hợp.

## Lưu ý

Các file trong `data/dimension/` hiện chỉ chứa **sample data**, mỗi file gồm 100 bản ghi mẫu. Để tạo đầy đủ dữ liệu dimension, hãy chạy script sau từ thư mục gốc của project:

```bash
python src/data_generation/run_dimensions.py
```
