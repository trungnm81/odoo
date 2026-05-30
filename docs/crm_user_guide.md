# Hướng dẫn sử dụng Odoo CRM

> Phiên bản: Odoo 18 (CRM module v1.9)

---

## Mục lục

1. [Giới thiệu](#1-giới-thiệu)
2. [Các khái niệm cơ bản](#2-các-khái-niệm-cơ-bản)
3. [Bắt đầu sử dụng](#3-bắt-đầu-sử-dụng)
4. [Quản lý Lead](#4-quản-lý-lead)
5. [Quản lý Pipeline (Opportunity)](#5-quản-lý-pipeline-opportunity)
6. [Convert Lead thành Opportunity](#6-convert-lead-thành-opportunity)
7. [Merge Lead/Opportunity](#7-merge-leadopportunity)
8. [Quản lý Sales Team & Phân công](#8-quản-lý-sales-team--phân-công)
9. [Tích hợp Email](#9-tích-hợp-email)
10. [Lên lịch họp (Calendar)](#10-lên-lịch-họp-calendar)
11. [Dự báo doanh thu (Forecast)](#11-dự-báo-doanh-thu-forecast)
12. [Báo cáo & Phân tích](#12-báo-cáo--phân-tích)
13. [Mẹo & Thực hành tốt nhất](#13-mẹo--thực-hành-tốt-nhất)

---

## 1. Giới thiệu

Odoo CRM là module quản lý quan hệ khách hàng, giúp doanh nghiệp theo dõi toàn bộ quá trình từ **tiếp nhận khách hàng tiềm năng (Lead)** đến **chốt giao dịch (Won Deal)**. Module này được tích hợp chặt chẽ với:

- **Email**: Tạo lead tự động từ email
- **Calendar**: Lên lịch họp với khách hàng
- **Sales Team**: Phân công và quản lý đội bán hàng
- **Marketing (UTM)**: Theo dõi hiệu quả chiến dịch quảng cáo
- **Predictive Scoring**: AI tự động tính xác suất chốt deal

---

## 2. Các khái niệm cơ bản

### Lead (Khách hàng tiềm năng)
Là thông tin khách hàng chưa được xác thực, cần được phân loại và đánh giá. Lead thường đến từ:
- Form đăng ký trên website
- Email gửi đến
- Danh sách mua từ bên thứ ba
- Nhập liệu thủ công

### Opportunity (Cơ hội bán hàng)
Là lead đã được xác thực và chuyển vào pipeline bán hàng. Mỗi opportunity đi qua các **stage** (giai đoạn) để tiến tới chốt deal.

### Stage (Giai đoạn)
Các giai đoạn trong pipeline, ví dụ:
- **New**: Mới tiếp nhận
- **Qualified**: Đã xác thực
- **Proposition**: Đã gửi báo giá
- **Negociation**: Đang thương lượng
- **Won**: Đã chốt
- **Lost**: Mất deal

### Sales Team
Nhóm bán hàng bao gồm:
- **Team Leader**: Người quản lý nhóm
- **Members**: Các salesperson trong nhóm

### Probability (Xác suất)
Tỷ lệ phần trăm (%) thể hiện khả năng chốt deal. Có thể được:
- **Tự động tính toán**: Bằng thuật toán Predictive Lead Scoring (PLS)
- **Chỉnh sửa thủ công**: Người dùng tự điều chỉnh

### Expected Revenue (Doanh thu kỳ vọng)
Số tiền dự kiến thu được từ opportunity.

---

## 3. Bắt đầu sử dụng

### 3.1. Truy cập module CRM
1. Đăng nhập Odoo
2. Vào menu **Sales → CRM** (hoặc **CRM** nếu là app riêng)

### 3.2. Giao diện chính
Giao diện CRM gồm các chế độ xem:

| Chế độ xem | Mô tả |
|---|---|
| **Kanban** | Xem pipeline dạng thẻ kéo-thả |
| **List** | Xem danh sách dạng bảng |
| **Calendar** | Xem lịch họp theo lead/opportunity |
| **Graph/Pivot** | Xem báo cáo và phân tích |
| **Forecast** | Xem dự báo doanh thu |

### 3.3. Cấu hình ban đầu
Vào **CRM → Configuration → Settings** để cấu hình:
- **Lead & Pipeline**: Bật/tắt sử dụng lead, pipeline
- **Predictive Lead Scoring**: Bật tính năng AI dự đoán
- **Auto Assignment**: Bật tự động gán lead cho salesperson
- **Email Alias**: Cấu hình email cho từng team

---

## 4. Quản lý Lead

### 4.1. Tạo Lead mới

**Cách 1 – Tạo thủ công:**
1. Vào **CRM → Leads**
2. Nhấn nút **Create**
3. Nhập thông tin:
   - **Opportunity Name**: Tên cơ hội
   - **Contact Name**: Tên người liên hệ
   - **Company Name**: Tên công ty
   - **Email**: Địa chỉ email
   - **Phone**: Số điện thoại
   - **Expected Revenue**: Doanh thu kỳ vọng
   - **Tags**: Phân loại (VD: Training, Service, v.v.)
   - **Salesperson**: Người phụ trách (có thể để trống để gán sau)
   - **Sales Team**: Team bán hàng
   - **Source**: Nguồn đến (Website, Facebook, Google, v.v.)
4. Nhấn **Save**

**Cách 2 – Từ Email:**
- Gửi email đến địa chỉ alias của team (VD: `crm-team@company.odoo.com`)
- Hệ thống tự động tạo lead với thông tin từ email
- Xem thêm mục [Tích hợp Email](#9-tích-hợp-email)

**Cách 3 – Import từ file:**
1. Vào **CRM → Favorites → Import**
2. Tải file mẫu (Import Template)
3. Điền thông tin lead vào file
4. Upload và import

### 4.2. Xem danh sách Lead
- **Kanban View**: Kéo-thả lead giữa các stage
- **List View**: Sắp xếp, lọc, nhóm theo các tiêu chí
- **Sử dụng Filters**:
  - **My Leads**: Lead của tôi
  - **Unassigned**: Lead chưa có người phụ trách
  - **New This Week**: Lead mới trong tuần
  - **High Priority**: Lead ưu tiên cao

### 4.3. Cập nhật thông tin Lead
- Click vào lead để mở form chi tiết
- Cập nhật các trường thông tin
- Sử dụng **Chatter** để ghi chú, gửi email nội bộ
- **Log note**: Ghi lại hoạt động (đã gọi điện, đã gửi email, v.v.)

### 4.4. Phát hiện trùng lặp
Hệ thống tự động phát hiện lead trùng lặp dựa trên:
- **Email domain**: Cùng tên miền email
- **Số điện thoại**: Cùng số điện thoại
- **Partner**: Cùng khách hàng

Trên form lead, bạn sẽ thấy **Potential Duplicate Lead Count** – nhấn vào để xem danh sách lead trùng.

### 4.5. Gán Lead cho Salesperson
1. Mở lead cần gán
2. Trường **Salesperson**: Chọn người phụ trách
3. Hệ thống tự động gán team dựa trên salesperson

Hoặc sử dụng **Assign Manually** (chọn nhiều lead):
1. Chọn các lead trong list view
2. Action → **Assign Salesmen**
3. Chọn salesperson và team

### 4.6. Xóa/Merge Lead
- **Xóa**: Chọn lead → Action → Delete
- **Merge**: Chọn 2-5 lead → Action → Merge (xem mục [Merge](#7-merge-leadopportunity))

---

## 5. Quản lý Pipeline (Opportunity)

### 5.1. Xem Pipeline
Vào **CRM → Pipeline** để xem tất cả opportunity.
- Dạng **Kanban**: Trực quan nhất – kéo-thả opportunity qua các stage
- Mỗi cột là một stage
- Mỗi thẻ là một opportunity

### 5.2. Thông tin trên thẻ Kanban
Mỗi thẻ opportunity hiển thị:
- **Tên opportunity**
- **Expected Revenue** (doanh thu kỳ vọng)
- **Probability** (xác suất)
- **Salesperson** và **Team**
- **Tags** và **Priority**
- **Ngày hết hạn (Expected Closing)**

### 5.3. Kéo-thả Opportunity
- Kéo thẻ từ stage này sang stage khác
- Hệ thống tự động cập nhật:
  - `date_last_stage_update`: Ngày cập nhật stage
  - `probability` (nếu bật tự động): Xác suất được tính lại

### 5.4. Chỉnh sửa nhanh
Click vào thẻ Kanban để mở form chi tiết, hoặc:
- Click vào các trường trên thẻ để chỉnh sửa inline
- Sử dụng **Edit** button để mở form đầy đủ

### 5.5. Stage & Probability
- Mỗi stage có thể được cấu hình **is_won** (stage chốt deal)
- Khi kéo vào stage Won:
  - `probability` tự động set = 100%
  - `date_closed` được ghi nhận
  - Hiệu ứng **Rainbowman** chúc mừng
- Khi đánh dấu **Lost**:
  - `probability` = 0%
  - Lead bị archive
  - Yêu cầu chọn **Lost Reason**

### 5.6. Predictive Lead Scoring (PLS)
PLS tự động tính toán xác suất dựa trên dữ liệu lịch sử:
- Mỗi lần won/lost, hệ thống ghi nhận tần suất
- Các yếu tố ảnh hưởng: source, country, team, priority, v.v.
- **Tự động cập nhật**: Mỗi khi stage thay đổi
- **Manual sync**: Nhấn **Set Automated Probability** để đồng bộ

### 5.7. Đánh dấu Won/Lost

**Mark as Won:**
1. Mở opportunity
2. Nhấn **Mark Won** (hoặc kéo vào stage Won)
3. 🎉 Rainbowman effect hiển thị (nếu đạt thành tích đặc biệt)

**Mark as Lost:**
1. Mở opportunity
2. Nhấn **Mark Lost**
3. Chọn **Lost Reason** (VD: Budget too high, Competitor, No need, v.v.)
4. Xác nhận → opportunity bị archive

**Restore Lost Deal:**
1. Bật **Archived** filter để thấy lead đã lost
2. Mở lead → Action → **Restore**
3. Lead được active trở lại với probability tự động

---

## 6. Convert Lead thành Opportunity

### 6.1. Chuyển đổi thủ công
1. Mở lead cần convert
2. Nhấn **Convert to Opportunity**
3. Chọn hoặc tạo mới **Customer** (partner)
4. Chọn **Salesperson** (nếu cần thay đổi)
5. Chọn **Sales Team** (nếu cần thay đổi)
6. Nhấn **Convert**

Kết quả:
- Lead type chuyển từ `lead` → `opportunity`
- `date_conversion` được ghi nhận
- Partner được tạo hoặc gán
- Lead xuất hiện trong pipeline

### 6.2. Tạo khách hàng (Partner) từ Lead
Khi convert, hệ thống tự động tạo partner từ thông tin lead:
- **Tên công ty** → Company partner
- **Tên liên hệ** → Contact partner (con của company)
- **Email, Phone, Address** → Đồng bộ từ lead

Lưu ý: Nếu email/phone của lead khác với partner, hệ thống sẽ hiển thị cảnh báo (ribbon) và cho phép đồng bộ.

### 6.3. Mass Convert
1. Chọn nhiều lead trong list view
2. Action → **Convert to Opportunity**
3. Chọn salesperson, team
4. Hệ thống tự động tạo partner cho từng lead

---

## 7. Merge Lead/Opportunity

### 7.1. Khi nào nên Merge?
- Phát hiện nhiều lead của cùng một khách hàng
- Cùng một khách hàng gửi nhiều yêu cầu
- Dữ liệu bị trùng lặp do import

### 7.2. Cách Merge
1. Chọn 2-5 lead/opportunity (giữ Ctrl/Cmd để chọn nhiều)
2. Action → **Merge**
3. Hệ thống tự động:
   - Sắp xếp theo confidence level (opportunity > lead, stage cao hơn)
   - Hợp nhất dữ liệu: lấy giá trị đầu tiên không null
   - Hợp nhất: tags, notes, followers, messages, attachments, calendar events
   - Xóa các lead phụ

### 7.3. Quy tắc Merge
| Loại dữ liệu | Cách xử lý |
|---|---|
| Text fields (description) | Nối với nhau bằng `<br/>` |
| Priority | Lấy giá trị cao nhất |
| Tags | Gộp tất cả tags |
| Many2one (partner, user) | Lấy giá trị đầu tiên không null |
| Many2many, One2many | Bỏ qua (không merge) |
| Address fields | Lấy lead có nhiều thông tin địa chỉ nhất |
| Lost Reason | Reset nếu lead đầu không bị lost |
| Messages & Activities | Chuyển sang lead chính |
| Attachments | Chuyển kèm nhãn gốc |

---

## 8. Quản lý Sales Team & Phân công

### 8.1. Tạo Sales Team
1. Vào **CRM → Configuration → Sales Teams**
2. Nhấn **Create**
3. Nhập:
   - **Team Name**: Tên team
   - **Team Leader**: Trưởng nhóm
   - **Members**: Thành viên
   - **Use Leads**: Bật nếu team xử lý lead
   - **Use Pipeline**: Bật nếu team quản lý opportunity
   - **Email Alias**: Địa chỉ email riêng của team

### 8.2. Thêm thành viên
1. Mở Sales Team
2. Tab **Members**
3. Thêm salesperson và cấu hình:
   - **Assignment Max**: Số lead tối đa mỗi tháng
   - **Lead Monthly Count**: Số lead đã nhận trong tháng

### 8.3. Phân công Lead

**Tự động (Auto Assignment):**
1. Vào **CRM → Settings → Lead Auto Assignment**
2. Bật tính năng
3. Cấu hình cron chạy định kỳ
4. Lead mới không có salesperson sẽ tự động được gán

**Cơ chế Round-robin:**
- Lead được phân bổ đều cho các thành viên
- VD: 4 salesperson (S1, S2, S3, S4) cho 6 lead:
  - L1 → S1, L2 → S2, L3 → S3, L4 → S4
  - L5 → S1, L6 → S2

**Thủ công:**
1. Chọn lead trong list view
2. Action → **Assign Salesmen**
3. Chọn salesperson và team

### 8.4. Email Alias cho Team
Mỗi team có thể có email alias riêng:
- Email gửi đến alias → tự động tạo lead mới
- Lead được gán cho team đó
- Hữu ích khi có nhiều team nhận lead từ nhiều nguồn khác nhau

---

## 9. Tích hợp Email

### 9.1. Email Gateway
CRM có thể nhận email và tự động tạo lead:
- Cấu hình **Email Alias** cho mỗi team
- Aliases phải được cấu hình trên server email
- Email đến → Parse thông tin → Tạo lead mới

### 9.2. Gửi email từ CRM
Trong form lead/opportunity:
- Sử dụng **Send Email** từ chatter
- Email được log trong lịch sử
- Có thể gửi template email có sẵn

### 9.3. Reply-To Alias
Khi gửi email từ lead/opportunity:
- Reply-To được set = Email Alias của team
- Khách hàng reply → email vào đúng lead

---

## 10. Lên lịch họp (Calendar)

### 10.1. Schedule Meeting
1. Mở lead/opportunity
2. Nhấn **Schedule Meeting** (trên header hoặc trong chatter)
3. Nhập:
   - **Subject**: Chủ đề (tự động điền tên opportunity)
   - **Date & Time**: Thời gian
   - **Duration**: Thời lượng
   - **Attendees**: Khách mời (tự động thêm salesperson và customer)
4. Nhấn **Save**

### 10.2. Xem lịch sử họp
Trên form lead/opportunity:
- **Next Meeting**: Hiển thị cuộc họp sắp tới
- **Last Meeting**: Hiển thị cuộc họp gần nhất
- Click vào để xem chi tiết hoặc reschedule

### 10.3. Smart Calendar View
Khi xem lịch họp từ opportunity:
- Tự động chọn **Week** view nếu có 1 cuộc họp
- Chọn **Month** view nếu nhiều cuộc họp trải dài
- Target vào ngày có cuộc họp gần nhất

---

## 11. Dự báo doanh thu (Forecast)

### 11.1. Các chỉ số doanh thu

| Chỉ số | Công thức | Ý nghĩa |
|---|---|---|
| Expected Revenue | Nhập thủ công | Doanh thu kỳ vọng |
| Prorated Revenue | Expected × Probability | Doanh thu điều chỉnh theo rủi ro |
| Recurring Revenue | Nhập thủ công | Doanh thu định kỳ |
| MRR | Recurring / Số tháng | Doanh thu định kỳ hàng tháng |
| Prorated MRR | MRR × Probability | MRR điều chỉnh theo rủi ro |

### 11.2. Xem Forecast
Vào **CRM → Forecasting**:
- **Forecast Graph**: Biểu đồ dự báo (load lazy để tối ưu tốc độ)
- **Forecast Pivot**: Bảng phân tích dự báo (load lazy)
- Có thể lọc theo team, salesperson, thời gian

### 11.3. Recurring Plan
Cấu hình các gói định kỳ:
- **Monthly**: 1 tháng
- **Quarterly**: 3 tháng
- **Yearly**: 12 tháng

Khi chọn recurring plan cho opportunity:
- MRR tự động tính
- Prorated MRR tự động cập nhật

---

## 12. Báo cáo & Phân tích

### 12.1. Activity Report
Vào **CRM → Reporting → Activities**
- Xem hoạt động theo salesperson, team
- Phân tích: số cuộc họp, số email, số ghi chú
- Lọc theo thời gian, stage, loại hoạt động

### 12.2. Opportunity Report
Vào **CRM → Reporting → Opportunities**
- Doanh thu theo team, salesperson
- Xác suất trung bình
- Số lượng opportunity theo stage
- Thời gian chốt deal trung bình (Days to Close)

### 12.3. Digest (Bản tin định kỳ)
- Cấu hình trong **Settings → Digest**
- Gửi email tóm tắt hàng tuần/tháng
- Nội dung: số lead mới, số deal won, doanh thu, v.v.

### 12.4. Custom Filters & Measures
Trong các báo cáo Pivot/Graph:
- Thêm **Measures**: Đếm, tổng doanh thu, trung bình xác suất
- Thêm **Filters**: Lọc theo team, salesperson, stage, thời gian
- **Drill-down**: Click vào số liệu để xem chi tiết

---

## 13. Mẹo & Thực hành tốt nhất

### 13.1. Quản lý Pipeline hiệu quả
- ✅ **Cập nhật stage kịp thời**: Kéo thẻ khi có tiến triển thực tế
- ✅ **Cập nhật Expected Revenue**: Số liệu càng chính xác, forecast càng đúng
- ✅ **Ghi chú trong Chatter**: Log mọi tương tác với khách hàng
- ✅ **Đặt Expected Closing**: Giúp ưu tiên deal sắp hết hạn
- ✅ **Sử dụng Tags**: Phân loại để lọc và báo cáo dễ dàng

### 13.2. Tận dụng PLS (AI Scoring)
- ✅ **Xác thực dữ liệu đầu vào**: Email, phone, country đúng chuẩn
- ✅ **Không chỉnh sửa probability thủ công trừ khi cần**: Để AI học chính xác
- ✅ **Cập nhật Lost Reason**: Giúp AI phân tích nguyên nhân thất bại
- ✅ **Đánh dấu Won/Lost đầy đủ**: Càng nhiều dữ liệu, AI càng chính xác

### 13.3. Phân công thông minh
- ✅ **Cấu hình Assignment Max** cho mỗi salesperson
- ✅ **Bật Auto Assignment** cho lead từ email/website
- ✅ **Sử dụng Assignment Domain** để lọc lead phù hợp (VD: chỉ lead từ Việt Nam)
- ✅ **Theo dõi Lead Unassigned Count** để tránh tồn đọng

### 13.4. Email Gateway
- ✅ **Tạo alias riêng cho mỗi team** (VD: team-sales@company.odoo.com)
- ✅ **Thiết lập mail server** để nhận email
- ✅ **Kiểm tra alias thường xuyên**: Đảm bảo email không bị mất

### 13.5. Merge & Dedup
- ✅ **Kiểm tra trùng lặp định kỳ**: Sử dụng Duplicate Lead Count
- ✅ **Merge thay vì xóa**: Giữ lại lịch sử và dữ liệu
- ✅ **Merge tối đa 5 lead/lần**: Tránh mất dữ liệu

### 13.6. Shortcuts & Tips
- 🎯 **Double-click vào Kanban card**: Mở form chi tiết nhanh
- 🎯 **Ctrl+Enter**: Lưu form nhanh
- 🎯 **Favorites → Import**: Import hàng loạt lead từ Excel
- 🎯 **Favorites → Export**: Export dữ liệu để phân tích ngoài
- 🎯 **Sử dụng Group By**: Nhóm theo team, stage, salesperson để có cái nhìn tổng quan

---

## Phụ lục: Bảng thuật ngữ

| Thuật ngữ | Giải thích |
|---|---|
| Lead | Khách hàng tiềm năng chưa xác thực |
| Opportunity | Cơ hội bán hàng đã xác thực |
| Stage | Giai đoạn trong pipeline |
| Pipeline | Quy trình bán hàng qua các stage |
| PLS | Predictive Lead Scoring – AI tính xác suất |
| MRR | Monthly Recurring Revenue |
| UTM | Tham số theo dõi chiến dịch marketing |
| Alias | Địa chỉ email tạo lead tự động |
| Rainbowman | Hiệu ứng chúc mừng khi chốt deal |
| Round-robin | Cơ chế phân bổ đều |
| Chatter | Khu vực trao đổi, ghi chú trên mỗi record |
| Lost Reason | Lý do mất deal |
| Expected Revenue | Doanh thu kỳ vọng |
| Prorated Revenue | Doanh thu điều chỉnh theo xác suất |

---

> Tài liệu được tạo cho Odoo CRM v1.9 – Module CRM thuộc Odoo 18.
> Mọi thắc mắc hoặc góp ý vui lòng liên hệ quản trị viên hệ thống.