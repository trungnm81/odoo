# Hướng dẫn: Khi nào tạo Lead, khi nào tạo Opportunity

## Quy tắc quyết định nhanh

```
Biết KH + biết nhu cầu  →  Opportunity
Chưa biết 1 trong 2     →  Lead
```

---

## Tạo Lead khi...

Chưa biết rõ khách hàng là ai **hoặc** nhu cầu chưa được xác nhận.

| Tình huống | Ví dụ cụ thể |
|------------|--------------|
| Khách hàng mới liên hệ lần đầu | Điền form website, gửi email hỏi thông tin, nhắn Zalo OA |
| Danh sách tiềm năng chưa qualify | Import từ hội thảo, data mua ngoài, referral chưa xác nhận |
| Chưa xác định được nhu cầu | Khách hỏi chung "lãi suất ngân hàng thế nào?" |
| Chưa nói chuyện trực tiếp | Số điện thoại từ sự kiện, chưa gọi lần nào |
| Cần sàng lọc trước khi giao nhân viên | Manager nhận batch KH, cần pre-qualify rồi mới assign |

---

## Tạo Opportunity khi...

Đã xác định được khách hàng cụ thể **và** nhu cầu rõ ràng.

| Tình huống | Ví dụ cụ thể |
|------------|--------------|
| Hội sở đẩy khách hiện hữu xuống chi nhánh | KH đã có trong hệ thống, hội sở xác định sản phẩm cross-sell/upsell |
| Khách cũ quay lại với nhu cầu mới | KH đang có tài khoản thanh toán, muốn vay mua nhà |
| Nhân viên qualify Lead thành công | Đã gọi, KH xác nhận có nhu cầu, đúng đối tượng |
| Referral đã được giới thiệu cụ thể | Bạn bè giới thiệu, biết rõ tên, nhu cầu, thu nhập |
| Khách đến chi nhánh trực tiếp | Gặp mặt, trao đổi xong, có nhu cầu rõ ràng |

---

## Quy trình chuyển đổi

```
[LEAD]
  Khách mới, chưa rõ
  partner_id: trống hoặc sơ bộ
  probability: 0%
  stage: New / Tiếp cận
        │
        │ Nhân viên gọi điện / Zalo
        │ → Xác nhận: đúng người, có nhu cầu
        ↓
[OPPORTUNITY]
  Đã có partner_id
  Gán stage, product_type, expected_revenue
  Theo dõi: Tiếp cận → Báo giá → Đàm phán → Thắng / Thua
```

---

## Thông tin cần điền khi tạo Opportunity từ hội sở

| Trường | Giá trị |
|--------|---------|
| `partner_id` | Khách hàng hiện hữu (đã có trong hệ thống) |
| `product_type` | Sản phẩm hội sở muốn cross-sell/upsell |
| `source_id` | "Hội sở đẩy xuống" (để báo cáo riêng) |
| `user_id` | Nhân viên chi nhánh được giao |
| `team_id` | Chi nhánh nhận |
| `description` | Ghi chú từ hội sở: lý do chọn KH, thông tin nền |
| `stage_id` | "Mới nhận" hoặc "Tiếp cận" |

---

## Lưu ý kỹ thuật

- Lead và Opportunity **dùng chung bảng** `crm.lead`, phân biệt bằng trường `type`.
- Khi chuyển Lead → Opportunity: Odoo chỉ đổi `type='opportunity'`, gán `date_open` và `date_conversion` — **không tạo bản ghi mới**.
- Với module CRM AI Banking: tạo Opportunity trực tiếp giúp **Customer 360** và **Next Best Action (NBA)** có đủ context để hoạt động ngay.
