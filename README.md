# Business Universe

Business Universe là một dự án mô phỏng dữ liệu doanh nghiệp theo hướng sát với thực tế vận hành. Dự án hướng tới việc xây dựng nhiều "vũ trụ" dữ liệu cho các ngành nghề khác nhau, trong đó mỗi vũ trụ phản ánh một doanh nghiệp với bối cảnh kinh doanh, quy tắc nghiệp vụ, vòng đời vận hành và các tình huống thực tế riêng.

Thay vì chỉ tạo ra các bộ dữ liệu ngẫu nhiên, Business Universe mô phỏng cách một doanh nghiệp thực sự hoạt động: tài sản và đơn vị kinh doanh hình thành, sản phẩm hoặc dịch vụ có vòng đời, khách hàng có hành vi khác nhau, giao dịch phát sinh theo thời gian, nguồn lực biến động, và chi phí ảnh hưởng đến kết quả kinh doanh. Dữ liệu được thiết kế để có thể dùng xuyên suốt trong các bài toán Data Analysis, Data Engineering, Analytics Engineering và Business Intelligence.

## Tầm nhìn

Business Universe sẽ phát triển thành một tập hợp các mô hình doanh nghiệp có thể dùng để học tập, nghiên cứu và thử nghiệm các hệ thống dữ liệu. Mục tiêu không phải là tạo ra dữ liệu lớn một cách máy móc, mà là tạo ra dữ liệu có ngữ cảnh, có nguyên nhân và đủ chiều sâu để trả lời các câu hỏi kinh doanh.

Mỗi ngành nghề được xem như một business universe độc lập, nhưng vẫn chia sẻ cách tiếp cận chung:

- Mô tả bối cảnh, mô hình vận hành và các giả định của doanh nghiệp.
- Xác định domain, entity, quan hệ và grain của dữ liệu.
- Thiết kế data warehouse phù hợp với nghiệp vụ.
- Sinh dữ liệu master và dữ liệu giao dịch có tương quan theo thời gian.
- Tạo business cases, ngoại lệ và biến động đủ thực tế để phân tích.
- Xây dựng các lớp ETL, dữ liệu derived, chỉ số và báo cáo phục vụ quyết định kinh doanh.

## Các vũ trụ trong dự án

Dự án được mở rộng dần theo từng ngành nghề. **Flex Coffee & Tea** hiện là vũ trụ đầu tiên, dùng để xây dựng và kiểm chứng phương pháp mô phỏng cho một doanh nghiệp F&B. Các ngành nghề khác sẽ được bổ sung trong tương lai và được tổ chức thành các thư mục hoặc module riêng, với tài liệu nghiệp vụ và mô hình dữ liệu tương ứng.

## Nguyên tắc xây dựng

- **Business-first**: bắt đầu từ bối cảnh và quy tắc vận hành, sau đó mới thiết kế entity, schema và dữ liệu.
- **Nhất quán theo thời gian**: dữ liệu phản ánh vòng đời của cửa hàng, sản phẩm, khách hàng, hợp đồng và các sự kiện vận hành.
- **Có tương quan và ngoại lệ**: các chỉ số không độc lập hoàn toàn; đồng thời vẫn có outlier và tình huống bất thường để phân tích.
- **Có thể truy nguyên**: dữ liệu được tổ chức theo domain, có quan hệ rõ ràng và phân biệt dữ liệu sinh trực tiếp với dữ liệu derived.
- **Có khả năng mở rộng**: mỗi ngành nghề có thể trở thành một vũ trụ riêng nhưng vẫn tuân theo cách tổ chức và tư duy chung của dự án.

## Cấu trúc repository

```text
Business-Universe/
├── <industry-universe>/  # Một vũ trụ mô phỏng theo ngành nghề
│   ├── business/         # Business requirements, entity và business rules
│   └── data_warehouse/   # Schema SQL, data dictionary, tương tác với hệ thống quản 
|   |                       trị dữ liệu
│   └── data/             # Dữ liệu mô phỏng sinh ra
│   └── src/              # Source code
|   └── .../
├── flex-coffeetea/       # Vũ trụ F&B đầu tiên
└── README.md             # Định hướng chung của dự án
```

## Lộ trình dự kiến

### Mỗi business universe

1. Hoàn thiện business foundation, entity list và data warehouse schema.
2. Sinh dimension và master data cho các domain chính.
3. Sinh dữ liệu ứng với từng domain đã xây dựng.
4. Xây dựng ETL, các bảng derived và bộ chỉ số phục vụ phân tích.
5. Bổ sung các bài toán phân tích, dashboard và use case mẫu.

### Mở rộng dự án

Tiếp tục bổ sung các mô hình doanh nghiệp mới, đồng thời hoàn thiện các thành phần dùng chung như quy trình sinh dữ liệu, tiêu chuẩn tài liệu, kiểm tra chất lượng dữ liệu và các phương pháp phân tích xuyên ngành.

## Bắt đầu từ đâu?

Để tìm hiểu một vũ trụ cụ thể, bắt đầu từ README trong thư mục của ngành đó, sau đó đọc tài liệu business, thiết kế data warehouse tương ứng,... Hiện tại, có thể tham khảo vũ trụ [`flex-coffeetea/`] như một triển khai mẫu đầu tiên.