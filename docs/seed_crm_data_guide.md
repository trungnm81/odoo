# Hướng dẫn dữ liệu giả lập CRM

## Cách chạy seed data

```bash
cd /Users/trung/projects/odoo
python3 odoo-bin shell -c odoo.conf -d odoo_dev < scripts/seed_crm_data.py
```

> **Lưu ý:** Script có kiểm tra trùng lặp (theo login), có thể chạy nhiều lần mà không tạo trùng.

---

## 1. Cấu trúc tổ chức

```
Giám đốc chi nhánh
├── Nguyễn Văn An (branch_director)
│
├── Phòng Kinh doanh Bán lẻ
│   ├── Trưởng phòng: Trần Thị Bình (retail_manager)
│   ├── Nhân viên: Phạm Thị Dung (retail_sale_1)
│   ├── Nhân viên: Hoàng Văn Em (retail_sale_2)
│   ├── Nhân viên: Đỗ Thị Phương (retail_sale_3)
│   └── Nhân viên: Vũ Văn Giang (retail_sale_4)
│
└── Phòng Kinh doanh Doanh nghiệp
    ├── Trưởng phòng: Lê Văn Cường (corp_manager)
    ├── Nhân viên: Bùi Thị Hạnh (corp_sale_1)
    ├── Nhân viên: Đinh Văn Ý (corp_sale_2)
    ├── Nhân viên: Ngô Thị Kim (corp_sale_3)
    ├── Nhân viên: Lý Văn Long (corp_sale_4)
    └── Nhân viên: Mai Thị Mai (corp_sale_5)
```

---

## 2. Danh sách tài khoản đăng nhập

Tất cả tài khoản đều có mật khẩu là **`123`**.  
Có thể đăng nhập tại: http://localhost:8069

### 2.1. Giám đốc chi nhánh

| Login | Tên | Vai trò | Quyền |
|-------|-----|---------|-------|
| `branch_director` | Nguyễn Văn An | Giám đốc chi nhánh | Sale Manager, CRM User |

### 2.2. Trưởng phòng

| Login | Tên | Phòng | Quyền |
|-------|-----|-------|-------|
| `retail_manager` | Trần Thị Bình | Kinh doanh Bán lẻ | Sale Manager, CRM User |
| `corp_manager` | Lê Văn Cường | Kinh doanh Doanh nghiệp | Sale Manager, CRM User |

### 2.3. Nhân viên kinh doanh

| Login | Tên | Phòng | Quyền |
|-------|-----|-------|-------|
| `retail_sale_1` | Phạm Thị Dung | Kinh doanh Bán lẻ | Salesman, CRM User |
| `retail_sale_2` | Hoàng Văn Em | Kinh doanh Bán lẻ | Salesman, CRM User |
| `retail_sale_3` | Đỗ Thị Phương | Kinh doanh Bán lẻ | Salesman, CRM User |
| `retail_sale_4` | Vũ Văn Giang | Kinh doanh Bán lẻ | Salesman, CRM User |
| `corp_sale_1` | Bùi Thị Hạnh | Kinh doanh Doanh nghiệp | Salesman, CRM User |
| `corp_sale_2` | Đinh Văn Ý | Kinh doanh Doanh nghiệp | Salesman, CRM User |
| `corp_sale_3` | Ngô Thị Kim | Kinh doanh Doanh nghiệp | Salesman, CRM User |
| `corp_sale_4` | Lý Văn Long | Kinh doanh Doanh nghiệp | Salesman, CRM User |
| `corp_sale_5` | Mai Thị Mai | Kinh doanh Doanh nghiệp | Salesman, CRM User |

---

## 3. Sales Teams (Phòng ban)

| Team | Leader | Số nhân viên |
|------|--------|-------------|
| Kinh doanh Bán lẻ | Trần Thị Bình | 4 |
| Kinh doanh Doanh nghiệp | Lê Văn Cường | 5 |

---

## 4. Danh sách khách hàng (Partners)

| STT | Tên khách hàng | Điện thoại | Thành phố |
|-----|----------------|------------|-----------|
| 1 | Công ty TNHH Thương Mại Sao Mai | 02838251234 | Hồ Chí Minh |
| 2 | Công ty CP Đầu Tư Phát Triển Nhà Đất | 02835261234 | Hồ Chí Minh |
| 3 | Ngân hàng TMCP Á Châu | 02838221234 | Hồ Chí Minh |
| 4 | Công ty TNHH Dịch Vụ Kỹ Thuật Số | 02438221234 | Hà Nội |
| 5 | Tập đoàn Bưu Chính Viễn Thông | 02438251234 | Hà Nội |
| 6 | Công ty CP Bán Lẻ Hiện Đại | 02836251234 | Hồ Chí Minh |
| 7 | Trường Đại Học Kinh Tế | 02838211234 | Hồ Chí Minh |
| 8 | Bệnh Viện Đa Khoa Trung Ương | 02438231234 | Hà Nội |
| 9 | Công ty CP Sữa Việt Nam | 02838271234 | Hồ Chí Minh |
| 10 | Công ty TNHH MTV Thương Mại Điện Tử | 02839251234 | Hồ Chí Minh |
| 11 | Khách sạn Sài Gòn Pearl | 02838281234 | Hồ Chí Minh |
| 12 | Công ty TNHH Sản Xuất & Thương Mại Gỗ | 027438251234 | Bình Dương |
| 13 | Công ty CP Giải Pháp Phần Mềm | 02438251234 | Hà Nội |
| 14 | Ngân hàng TMCP Ngoại Thương | 02438241234 | Hà Nội |
| 15 | Công ty TNHH Thời Trang & Phụ Kiện | 02838225234 | Hồ Chí Minh |

---

## 5. Leads & Opportunities

### 5.1. Team Bán lẻ

| STT | Tên | Loại | Nhân viên | Doanh số dự kiến (VNĐ) | Xác suất | Giai đoạn |
|-----|-----|------|-----------|----------------------|---------|-----------|
| 1 | Mua 20 bộ bàn ghế văn phòng | Cơ hội | Phạm Thị Dung | 180.000.000 | 60% | Báo giá |
| 2 | Tư vấn nội thất showroom 200m2 | Cơ hội | Phạm Thị Dung | 250.000.000 | 30% | Đàm phán |
| 3 | Mua 5 kệ sách văn phòng | Lead | Phạm Thị Dung | 15.000.000 | 20% | Mới |
| 4 | Trang bị bàn ghế cho 30 nhân viên | Cơ hội | Hoàng Văn Em | 120.000.000 | 75% | Báo giá |
| 5 | Mua tủ hồ sơ di động | Cơ hội | Hoàng Văn Em | 45.000.000 | 40% | Đàm phán |
| 6 | Báo giá bàn làm việc đơn | Lead | Hoàng Văn Em | 8.500.000 | 15% | Mới |
| 7 | Nội thất phòng họp 50 chỗ | Cơ hội | Đỗ Thị Phương | 350.000.000 | 45% | Đàm phán |
| 8 | Ghế văn phòng cao cấp 15 cái | Lead | Đỗ Thị Phương | 45.000.000 | 25% | Mới |
| 9 | Thiết kế & thi công nội thất VP mới | Cơ hội | Vũ Văn Giang | 500.000.000 | 20% | Đàm phán |
| 10 | Bàn họp nhóm 10 cái | Lead | Vũ Văn Giang | 28.000.000 | 35% | Mới |

### 5.2. Team Doanh nghiệp

| STT | Tên | Loại | Nhân viên | Doanh số dự kiến (VNĐ) | Xác suất | Giai đoạn |
|-----|-----|------|-----------|----------------------|---------|-----------|
| 1 | Hợp đồng trang bị nội thất tòa nhà 20 tầng | Cơ hội | Bùi Thị Hạnh | 2.500.000.000 | 50% | Báo giá |
| 2 | Cung cấp bàn ghế cho dự án VP mới | Cơ hội | Bùi Thị Hạnh | 800.000.000 | 65% | Báo giá |
| 3 | Nội thất không gian làm việc chung | Cơ hội | Đinh Văn Ý | 980.000.000 | 35% | Đàm phán |
| 4 | Tư vấn thiết kế nội thất toàn bộ VP | Cơ hội | Đinh Văn Ý | 150.000.000 | 15% | Mới |
| 5 | Đấu thầu nội thất trụ sở mới | Cơ hội | Ngô Thị Kim | 5.200.000.000 | 25% | Đàm phán |
| 6 | Cung cấp ghế chờ cho sảnh bệnh viện | Cơ hội | Ngô Thị Kim | 350.000.000 | 70% | Báo giá |
| 7 | Hợp đồng khung nội thất cho 5 chi nhánh | Cơ hội | Lý Văn Long | 1.800.000.000 | 40% | Đàm phán |
| 8 | Bàn làm việc lập trình viên 100 cái | Lead | Lý Văn Long | 500.000.000 | 10% | Mới |
| 9 | Nội thất phòng họp và phòng GĐ các cấp | Cơ hội | Mai Thị Mai | 670.000.000 | 55% | Báo giá |
| 10 | Tư vấn thiết kế không gian mở | Lead | Mai Thị Mai | 85.000.000 | 20% | Mới |

---

## 6. Tổng quan dữ liệu đã seed

| Loại | Số lượng |
|------|---------|
| Người dùng (Users) | 12 |
| Phòng ban (Sales Teams) | 2 |
| Khách hàng (Partners) | 15 |
| Leads | 20 |
| Tổng doanh số dự kiến | ~13.8 tỷ VNĐ |

---

## 7. Yêu cầu trước khi chạy

- Database `odoo_dev` phải tồn tại và đã cài đầy đủ module CRM (`crm`, `sales_team`).
- Odoo server không cần chạy khi chạy script shell, nhưng cần restart server sau khi seed để thấy dữ liệu mới.