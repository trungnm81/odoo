# Quy trình CRM cho Ngân hàng – Phiên bản Tối giản cho NVKD

> Phiên bản: Odoo 18 (CRM module v1.9)  
> Mục tiêu: **NVKD ngân hàng chỉ cần kéo-thả, không cần nhập liệu thủ công**

---

## Mục lục

1. [Tổng quan luồng hoạt động](#1-tổng-quan-luồng-hoạt-động)
2. [So sánh: Luồng tối giản vs Luồng đầy đủ](#2-so-sánh)
3. [Hướng dẫn cấu hình (cho Admin)](#3-hướng-dẫn-cấu-hình)
   - 3.1. Bật tính năng Lead
   - 3.2. Cấu hình Email Alias cho từng chi nhánh/phòng
   - 3.3. Bật Lead Enrichment (IAP)
   - 3.4. Bật Auto Assignment
   - 3.5. Bật Predictive Lead Scoring
   - 3.6. Tạo Automation Rule tự động Convert Lead → Opportunity
   - 3.7. Ẩn menu Lead khỏi NVKD
   - 3.8. Cấu hình Digest – Báo cáo tự động
   - 3.9. Tùy chỉnh Stage cho ngân hàng
4. [Hướng dẫn cho NVKD (Chỉ 3 bước)](#4-hướng-dẫn-cho-nvkd)
5. [Hướng dẫn cho Quản lý](#5-hướng-dẫn-cho-quản-lý)
6. [Các kịch bản thực tế](#6-các-kịch-bản-thực-tế)
7. [Mẹo tối ưu cho ngân hàng](#7-mẹo-tối-ưu-cho-ngân-hàng)
8. [Phụ lục: Bảng phân quyền đề xuất](#8-phụ-lục)

---

## 1. Tổng quan luồng hoạt động

### Sơ đồ luồng

```
Khách hàng
    │
    ├── Gọi điện / Email ──→ Email Alias của team
    ├── Đến quầy ──→ NVKD nhập tối thiểu (tên + SĐT)
    └── Form website ──→ Tự động
                            │
                            ▼
                    ┌────────────────┐
                    │   LEAD (tự tạo) │ ← NVKD KHÔNG thấy menu này
                    └────────┬───────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
      IAP Enrich    Auto Assign     PLS tính xác suất
      (tự động)     (round-robin)   (tự động)
              │              │              │
              └──────┬───────┘──────────────┘
                     ▼
        ┌─────────────────────────┐
        │ Automation Rule         │
        │ (Tự động Convert Lead   │
        │  → Opportunity)         │
        └────────┬────────────────┘
                 ▼
        ┌─────────────────────────┐
        │   OPPORTUNITY           │ ← NVKD thấy ở Pipeline
        │   (Trong pipeline)       │
        └────────┬────────────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
  Stage 1    Stage 2   ...  Won/Lost
  (New)    (Qualified)     (Kéo thả)
```

### Nguyên tắc thiết kế

| Nguyên tắc | Mô tả |
|---|---|
| **Tự động hóa tối đa** | Mọi thứ có thể tự động đều tự động: tạo lead, gán người, làm giàu dữ liệu, tính xác suất, convert sang opportunity |
| **NVKD không thấy Lead** | Lead là bước "hậu trường" cho compliance, audit. NVKD chỉ thấy Pipeline (Opportunity) |
| **Chỉ kéo-thả** | Thao tác chính của NVKD là kéo thẻ Kanban qua các stage |
| **Nhập tối thiểu** | Chỉ bắt buộc nhập Expected Revenue (số tiền) – mọi thứ khác đã tự động |

---

## 2. So sánh: Luồng tối giản vs Luồng đầy đủ

### Luồng A – Đầy đủ (Có Lead, NVKD thấy Lead)

```
Lead → Convert thủ công → Opportunity → Pipeline → Won/Lost
```

### Luồng B – Tối giản cho ngân hàng (Có Lead, NHƯNG ẩn khỏi NVKD)

```
Lead (tự động) → Auto Convert → Opportunity → Pipeline → Won/Lost
```

### Bảng so sánh

| Tiêu chí | Luồng A (Có Lead – thủ công) | Luồng B (Có Lead – tự động) |
|---|---|---|
| **Số bước NVKD cần làm** | 4 bước | **2 bước** ✅ |
| **NVKD có thấy Lead?** | Có | **Không** – chỉ thấy Pipeline ✅ |
| **NVKD có phải Convert?** | Có (bấm nút, chọn partner) | **Không** – tự động ✅ |
| **NVKD có phải nhập thông tin?** | Nhiều (tên, email, phone, company) | **Tối thiểu** (chỉ số tiền) ✅ |
| **Compliance / Audit trail** | **Tốt** ✅ | **Tốt** ✅ (lead vẫn được track) |
| **Phân tích kênh marketing** | **Tốt** ✅ | **Tốt** ✅ |
| **KYC / AML support** | **Tốt** ✅ | **Tốt** ✅ |
| **Phù hợp NVKD lười nhập?** | Không | **Có** ✅ |

### Kết luận

> **Luồng B là lựa chọn tối ưu cho ngân hàng.**  
> Giữ được Lead cho compliance và audit, nhưng ẩn hoàn toàn khỏi NVKD – họ chỉ thấy Pipeline để kéo thả.

---

## 3. Hướng dẫn cấu hình (cho Admin)

> **Thời gian thực hiện:** 30-60 phút  
> **Người thực hiện:** Quản trị viên hệ thống (có quyền `Settings` và `Technical`)

---

### 3.1. Bật tính năng Lead

**Mục đích:** Giữ Lead cho compliance, audit, phân tích kênh.

1. Vào **CRM → Configuration → Settings**
2. Tìm mục **"Use leads"**
3. ✅ **Giữ nguyên tick** (bật)
4. Nhấn **Save**

> ⚠️ **Quan trọng:** Lead được bật nhưng sẽ ẩn khỏi menu của NVKD ở bước [3.7](#37-ẩn-menu-lead-khỏi-nvkd)

---

### 3.2. Cấu hình Email Alias cho từng chi nhánh/phòng

**Mục đích:** NVKD forward email khách vào alias → lead tự tạo, không cần nhập liệu.

1. Vào **CRM → Configuration → Sales Teams**
2. Chọn team (VD: "Chi nhánh Hà Nội", "Phòng Khách hàng Doanh nghiệp", v.v.)
3. Nhập **Email Alias**:
   - VD: `hn-crm@bank.odoo.com` (Chi nhánh Hà Nội)
   - VD: `hcm-crm@bank.odoo.com` (Chi nhánh HCM)
   - VD: `corp@bank.odoo.com` (Phòng Khách hàng Doanh nghiệp)
4. Đảm bảo **"Use Leads"** và **"Use Pipeline"** được bật
5. Nhấn **Save**

**Yêu cầu kỹ thuật:**
- Server email (mail gateway) phải được cấu hình để nhận email đến các alias này
- Xem hướng dẫn: Odoo Technical → Email Gateway

**Hướng dẫn NVKD:**
> "Khi khách hàng gửi email, anh/chị chỉ cần **forward** email đó đến địa chỉ `hn-crm@bank.odoo.com` là hệ thống tự động tạo lead. Không cần nhập gì thêm."

---

### 3.3. Bật Lead Enrichment (IAP)

**Mục đích:** Tự động làm giàu thông tin lead từ email (tên công ty, địa chỉ, ngành nghề, quy mô, v.v.).

1. Vào **CRM → Configuration → Settings**
2. Tìm mục **"Lead Enrichment"**
3. ✅ **Tick** "Enrich your leads with company data based on their email addresses"
4. Chọn chế độ **"Automatic enrichment"**
5. Nhấn **Save**

> 📌 Yêu cầu: Cần có tín dụng IAP (mua từ Odoo) để sử dụng tính năng này.

**Kết quả:**
- Khi lead được tạo từ email, hệ thống tự động tra cứu thông tin công ty từ email domain
- Các trường như `partner_name`, `website`, `country_id`, `city` được điền tự động
- NVKD không cần nhập các thông tin này

---

### 3.4. Bật Auto Assignment

**Mục đích:** Lead mới tự động gán cho NVKD theo cơ chế round-robin, không cần ai phân công.

1. Vào **CRM → Configuration → Settings**
2. Tìm mục **"Lead Assignment"**
3. ✅ **Tick** "Automatically assign leads to sales persons based on rules"
4. Chọn chế độ:
   - **Automatic** (chạy cron định kỳ) – khuyến nghị
   - **Manual** (chạy bằng tay) – nếu muốn kiểm soát
5. Cấu hình **"Repeat every"**: Chọn `1` `Days` (chạy hàng ngày)
6. Nhấn **Save**

**Cấu hình Assignment Max cho từng NVKD:**
1. Vào **CRM → Configuration → Sales Teams**
2. Chọn team → Tab **Members**
3. Mỗi thành viên có trường **"Assignment Max"**:
   - Số lead tối đa mỗi tháng mà NVKD có thể nhận
   - VD: `30` (lead/tháng)
4. Nhấn **Save**

**Cơ chế hoạt động:**
- Lead không có người phụ trách → cron chạy → gán cho NVKD có ít lead nhất trong tháng
- Nếu tất cả NVKD đã đạt `Assignment Max` → lead vẫn ở trạng thái unassigned → quản lý xử lý

---

### 3.5. Bật Predictive Lead Scoring (PLS)

**Mục đích:** AI tự động tính xác suất chốt deal (probability) – NVKD không cần nhập %.

1. Vào **CRM → Configuration → Settings**
2. Tìm mục **"Predictive Lead Scoring"**
3. ✅ **Bật** (tích vào)
4. Nhấn **"Update Probabilities"** để chạy lần đầu
5. Nhấn **Save**

**Các yếu tố PLS sử dụng (mặc định):**
- `source_id` (nguồn đến: website, giới thiệu, quầy, v.v.)
- `country_id` (quốc gia)
- `team_id` (team bán hàng)
- Có thể thêm/bớt các yếu tố trong **Technical → PLS Fields**

---

### 3.6. Tạo Automation Rule tự động Convert Lead → Opportunity

**Mục đích:** Khi lead đã có đủ thông tin, tự động convert thành opportunity – NVKD không cần bấm nút Convert.

#### Cách 1: Dùng Server Action + Automated Action (Khuyến nghị)

**Bước 1: Tạo Server Action**

1. Vào **Technical → Actions → Server Actions**
2. Nhấn **Create**
3. Nhập:
   - **Name**: `Auto Convert Lead to Opportunity`
   - **Model**: `crm.lead`
   - **Action Type**: `Execute Python Code`
4. **Python Code**:
   ```python
   for lead in records:
       if lead.type == 'lead' and lead.active and lead.won_status == 'pending':
           # Tìm partner từ email
           partner = lead._find_matching_partner()
           if not partner:
               partner = lead._create_customer()
           # Convert sang opportunity
           lead.convert_opportunity(partner.id)
   ```
5. Nhấn **Save**

**Bước 2: Tạo Automated Action**

1. Vào **Technical → Automation → Automated Actions**
2. Nhấn **Create**
3. Nhập:
   - **Name**: `Auto Convert: Enriched Lead → Opportunity`
   - **Model**: `crm.lead`
   - **Trigger**: `On Update` hoặc `On Creation`
   - **Trigger Fields**: Chọn `email_from`, `partner_name`, `phone`
   - **Domain**: `[('type', '=', 'lead'), ('active', '=', True), ('won_status', '=', 'pending')]`
   - **Server Action to Run**: Chọn `Auto Convert Lead to Opportunity` (đã tạo ở Bước 1)
4. Nhấn **Save**

> 📌 **Giải thích:**  
> - Khi lead được tạo hoặc cập nhật email/phone/tên công ty → tự động convert
> - NVKD không cần bấm nút Convert
> - Nếu lead chưa đủ thông tin → không convert → vẫn ở trạng thái lead
> - Quản lý có thể kiểm tra các lead chưa convert được trong menu "Lead" (chỉ quản lý thấy)

#### Cách 2: Dùng Automation Rule đơn giản hơn (nếu không muốn code)

Sử dụng tính năng **Base Automation** có sẵn của Odoo với action type "Add Followers" hoặc "Send Email" để thông báo cho quản lý khi có lead mới, và quản lý sẽ kiểm tra + convert thủ công.

Tuy nhiên, **Cách 1** (Python code) là tối ưu nhất cho mục tiêu zero-click của NVKD.

---

### 3.7. Ẩn menu Lead khỏi NVKD

**Mục đích:** NVKD chỉ thấy Pipeline (Opportunity), không thấy menu Lead – tránh nhầm lẫn và giảm thao tác.

Dựa trên phân tích file `crm_menu_views.xml` (dòng 49-56):
```xml
<menuitem
    id="crm_menu_leads"
    name="Leads"
    parent="crm_menu_root"
    action="crm.crm_lead_all_leads"
    groups="crm.group_use_lead"
    sequence="5"/>
```

Menu Lead chỉ hiển thị khi user thuộc nhóm `crm.group_use_lead`. Do đó:

#### Cách 1 (Dễ nhất): Gỡ nhóm `group_use_lead` khỏi NVKD

1. Vào **Settings → Users & Companies → Users**
2. Chọn từng NVKD
3. Tab **Access Rights**
4. Mở rộng mục **CRM**
5. **Bỏ tick** "Show Lead Menu"
6. Nhấn **Save**

**Kết quả:**
- NVKD mất quyền truy cập menu Lead
- Menu "Leads" (và "Sales → Leads") biến mất khỏi giao diện
- NVKD chỉ thấy: **My Pipeline**, **My Activities**, **Customers**, **Reporting**
- Quản lý vẫn thấy Lead (vì thuộc nhóm `group_sale_manager` hoặc được cấp riêng)

#### Cách 2 (Nâng cao): Tạo Security Group riêng

Nếu muốn lead hoàn toàn vô hình với NVKD (kể cả qua link trực tiếp), tạo group mới và gán record rule với domain `(1,'=',0)` (không ai thấy). Chỉ quản lý mới bypass được rule này.

---

### 3.8. Cấu hình Digest – Báo cáo tự động

**Mục đích:** Quản lý nhận báo cáo CRM qua email hàng tuần – không cần vào hệ thống.

1. Vào **Settings → Technical → Digest**
2. Chọn digest mặc định hoặc tạo mới
3. Cấu hình:
   - **Name**: `CRM Weekly Report`
   - **Periodicity**: `weekly`
   - **Next Send Date**: Chọn thứ Hai tuần tới
   - **KPI**: Chọn các chỉ số CRM:
     - ✅ CRM's won in analysis period (số deal won)
     - ✅ CRM's pipeline (giá trị pipeline)
     - ✅ CRM's leads (số lead mới)
     - ✅ CRM's opportunities (số opportunity mới)
4. Tab **Recipients**: Thêm email của quản lý, giám đốc kinh doanh
5. Nhấn **Save**

---

### 3.9. Tùy chỉnh Stage cho ngân hàng

**Mục đích:** Stage phù hợp với quy trình nghiệp vụ ngân hàng.

Vào **CRM → Configuration → Pipeline → Stages** và tạo các stage sau:

| Stage | Mô tả | Màu | Probability tự động |
|---|---|---|---|
| **New** | Mới tiếp nhận | Xám | 10% |
| **Qualified** | Đã xác thực thông tin | Xanh nhạt | 20% |
| **Documentation** | Đang thu thập hồ sơ | Xanh | 35% |
| **Credit Assessment** | Thẩm định tín dụng | Vàng | 50% |
| **Approval** | Phê duyệt khoản vay | Cam | 70% |
| **Disbursement** | Giải ngân | Hồng | 90% |
| **Won** | Đã giải ngân | Xanh lá | 100% |
| **Lost** | Từ chối / Hủy | Đỏ | 0% |

> 💡 **Mẹo:**  
> - Đánh dấu stage **Won** là `is_won = True`  
> - Có thể gán team cho từng stage (VD: stage Credit Assessment chỉ dành cho team Thẩm định)

---

## 4. Hướng dẫn cho NVKD (Chỉ 3 bước)

> Đây là tài liệu dành cho **Nhân viên Kinh doanh** – những người "lười nhập liệu" nhất.

---

### Bước 1: Mở Pipeline

1. Đăng nhập Odoo
2. Vào **Sales → My Pipeline**
3. Màn hình hiển thị dạng **Kanban** với các cột stage

> 🎯 **Bạn không cần tạo gì cả.** Lead đã được tạo tự động từ email và gán vào pipeline cho bạn.

---

### Bước 2: Kéo thẻ qua các stage

- **Kéo thẻ** từ cột này sang cột khác khi có tiến triển mới
- VD: Kéo từ "New" → "Documentation" khi đã nhận đủ hồ sơ khách hàng

> 🎯 **Bạn chỉ cần kéo-thả.** Mọi thứ khác (xác suất, ngày tháng, lịch sử) đã tự động cập nhật.

---

### Bước 3: Nhập Expected Revenue

Khi kéo thẻ, có thể bạn sẽ thấy popup yêu cầu nhập **"Expected Revenue"**:

```
┌──────────────────────────────────┐
│  Move Opportunity:              │
│  - Stage: New → Won            │
│  - Expected Revenue: [______]  │ ← Nhập số tiền
│  - Expected Closing: [______]  │ ← Có thể bỏ qua
│                                │
│  [Move]  [Cancel]             │
└──────────────────────────────────┘
```

- **Bắt buộc:** Nhập `Expected Revenue` (số tiền dự kiến)
- **Không bắt buộc:** Các trường khác có thể bỏ qua
- Nhấn **Move**

> 🎯 **Xong!** Chỉ cần nhập 1 số duy nhất. Mọi thứ khác đã tự động.

---

### Khi nào cần làm thêm?

| Tình huống | Hành động |
|---|---|
| **Khách gọi điện** | Ghi nhanh tên + SĐT ra giấy, sau đó nhờ admin/quản lý nhập hoặc tự nhập vào CRM với tối thiểu thông tin |
| **Khách gửi email** | **Forward email** đến alias của team (VD: `hn-crm@bank.odoo.com`) – lead tự tạo |
| **Khách đến quầy** | Nhập **tối thiểu**: Tên khách + Số điện thoại. Hệ thống tự động enrich phần còn lại |
| **Khách hủy giao dịch** | Kéo thẻ vào **Lost** → chọn 1 lý do (dropdown – chỉ cần click) |
| **Khách đã giải ngân** | Kéo thẻ vào **Won** → nhập số tiền |

---

## 5. Hướng dẫn cho Quản lý

### 5.1. Xem báo cáo từ email Digest

- Mỗi sáng Thứ Hai, quản lý nhận email **Digest** với các chỉ số:
  - 📊 Số lead mới trong tuần
  - 📊 Số opportunity mới
  - 📊 Số deal won
  - 📊 Tổng doanh thu kỳ vọng
- Không cần vào hệ thống – xem ngay trong email

### 5.2. Kiểm tra Lead Exception

Vào **CRM → Leads** (chỉ quản lý mới thấy menu này):

- Kiểm tra các lead chưa được auto-convert (do thiếu thông tin)
- Có thể **Convert thủ công** nếu cần
- Có thể gán cho NVKD khác nếu auto assignment chưa chạy

### 5.3. Phân tích Pipeline

Vào **CRM → Reporting → Pipeline**:

- Xem tổng quan pipeline theo team, chi nhánh
- Lọc theo stage, salesperson, thời gian
- Export báo cáo ra Excel nếu cần

### 5.4. Kiểm tra Auto Assignment

Vào **CRM → Configuration → Sales Teams**:

- Xem **Lead Unassigned Count**: Số lead chưa được gán
- Xem **Lead Monthly Count**: Số lead mỗi NVKD đã nhận trong tháng
- Nếu có tồn đọng → chạy assignment thủ công (nút "Assign Now")

### 5.5. Dashboard tổng quan

Vào **CRM** (trang chủ):

- Widgets hiển thị: Pipeline value, Won this month, Leads to process
- Click vào từng widget để xem chi tiết

---

## 6. Các kịch bản thực tế

### Kịch bản 1: Khách hàng gửi email yêu cầu vay

```
1. Khách gửi email: "Tôi muốn vay 500 triệu mua nhà"
2. NVKD forward email → hn-crm@bank.odoo.com
3. [Tự động] Lead được tạo
4. [Tự động] IAP Enrich: điền thông tin công ty, địa chỉ
5. [Tự động] Auto Assign: gán cho NVKD phù hợp
6. [Tự động] Auto Convert: Lead → Opportunity
7. NVKD mở Pipeline → thấy opportunity mới
8. NVKD kéo thẻ: New → Documentation → Credit Assessment → Approval → Disbursement → Won
9. NVKD nhập Expected Revenue: 500,000,000 VND
10. 🎉 Xong! Chỉ mất 5 giây kéo thả.
```

### Kịch bản 2: Khách hàng đến quầy

```
1. Khách đến quầy: "Tôi muốn mở thẻ tín dụng"
2. NVKD ghi nhanh: Tên + SĐT
3. NVKD vào CRM → Create:
   - Nhập: Tên khách + Số điện thoại
   - Stage: New
   - Nhấn Save (mất 10 giây)
4. [Tự động] PLS tính xác suất = 60%
5. NVKD gọi điện tư vấn → kéo sang Qualified
6. Khách đồng ý → kéo sang Documentation → ...
7. 🎉 Xong!
```

### Kịch bản 3: Quản lý xem báo cáo cuối tháng

```
1. Thứ Hai đầu tháng → email Digest gửi đến
2. Quản lý mở email → thấy:
   - 20 lead mới (tăng 15% so với tháng trước)
   - 15 opportunity đang xử lý
   - 3 deal won, tổng doanh thu 2.5 tỷ
   - Pipeline value: 12 tỷ
3. Nếu cần chi tiết → click link vào CRM → xem báo cáo Pipeline
4. 🎉 Xong! Chỉ mất 30 giây đọc email.
```

---

## 7. Mẹo tối ưu cho ngân hàng

### 7.1. Phân quyền chi nhánh (Multi-company)

Nếu ngân hàng có nhiều chi nhánh:
- Mỗi chi nhánh = 1 **Company** trong Odoo
- Mỗi chi nhánh = 1 **Sales Team** riêng
- Cấu hình **Record Rule** đa công ty (đã có sẵn: `crm_lead_company_rule`)
- NVKD chi nhánh nào chỉ thấy lead/opportunity của chi nhánh đó

### 7.2. Stage tùy chỉnh cho từng loại sản phẩm

Tạo nhiều **Pipeline** khác nhau cho từng sản phẩm:

| Sản phẩm | Pipeline |
|---|---|
| Vay thế chấp | Stage: Tiếp nhận → Thẩm định TS → Phê duyệt → Giải ngân |
| Thẻ tín dụng | Stage: Tiếp nhận → Thẩm định → Phát hành → Kích hoạt |
| Bảo hiểm | Stage: Tư vấn → Ký hợp đồng → Đóng phí |
| Huy động vốn | Stage: Tiếp nhận → Chào lãi suất → Gửi tiền |

### 7.3. Template Email cho từng stage

Cấu hình **Mail Template** tự động gửi email khi chuyển stage:
- **New → Qualified**: Email cảm ơn khách hàng
- **Qualified → Documentation**: Email hướng dẫn chuẩn bị hồ sơ
- **Won**: Email chúc mừng + thông tin giải ngân
- **Lost**: Email khảo sát lý do

### 7.4. Tích hợp signing (chữ ký số)

- Module `sign` của Odoo cho phép gửi hợp đồng ký số
- Tích hợp vào stage **Documentation** hoặc **Approval**

### 7.5. Tích hợp SMS

- Module `crm_sms` cho phép gửi SMS từ lead/opportunity
- Dùng để gửi thông báo: "Hồ sơ của Quý khách đã được duyệt"

### 7.6. KPI cho NVKD

Sử dụng module **Gamification** để tự động tính KPI:

| KPI | Công thức |
|---|---|
| Số deal won trong tháng | Đếm số opportunity đến stage Won |
| Doanh số | Tổng Expected Revenue của deal won |
| Thời gian chốt deal trung bình | Trung bình `day_close` |
| Tỷ lệ chuyển đổi | (Số deal won) / (Tổng lead nhận được) |

---

## 8. Phụ lục: Bảng phân quyền đề xuất

| Vai trò | Menu thấy | Quyền |
|---|---|---|
| **NVKD** | My Pipeline, My Activities, Customers | Chỉ xem lead/opportunity của mình |
| **Quản lý phòng** | + Leads, Teams, Reporting | Xem tất cả lead/opportunity trong team |
| **Giám đốc kinh doanh** | + Forecast, Settings | Xem tất cả, cấu hình pipeline |
| **Admin hệ thống** | + Technical, Automation | Toàn quyền |

### Cách cấu hình cho NVKD chỉ thấy Pipeline:

1. Vào **Settings → Users & Companies → Users**
2. Chọn NVKD
3. Tab **Access Rights**:
   - CRM: ✅ `Salesman: Own Leads Only`
   - **Bỏ** `Show Lead Menu`
4. Nhấn **Save**

---

> Tài liệu được tạo cho Odoo CRM v1.9 – Module CRM thuộc Odoo 18.  
> Mục tiêu: **NVKD ngân hàng chỉ kéo-thả, không nhập liệu thủ công.**