"""
Script tạo dữ liệu giả lập cho hệ thống CRM Odoo.

Cấu trúc tổ chức:
  1. Giám đốc chi nhánh (Branch Director)
  2. Trưởng phòng Kinh doanh Bán lẻ (Retail Sales Manager)
  3. Trưởng phòng Kinh doanh Doanh nghiệp (Corporate Sales Manager)
  4. Nhân viên kinh doanh Bán lẻ (dưới quyền Retail Manager)
  5. Nhân viên kinh doanh Doanh nghiệp (dưới quyền Corporate Manager)

Cách chạy:
  cd /Users/trung/projects/odoo
  python3 odoo-bin shell -c odoo.conf -d odoo_dev -- scripts/seed_crm_data.py

Hoặc copy-paste nội dung bên dưới vào Odoo shell khi đã vào môi trường.
"""

import json
from datetime import datetime, timedelta

# ============================================================
# CẤU HÌNH
# ============================================================
COMPANY_NAME = "Công ty TNHH Nội Thất Văn Phòng ABC"

# ============================================================
# 1. TẠO CÁC GROUP/QUYỀN
# ============================================================
def ensure_groups(env):
    """Đảm bảo các group cần thiết tồn tại."""
    groups = {
        'group_sale_manager': 'sales_team.group_sale_manager',
        'group_sale_salesman': 'sales_team.group_sale_salesman',
        'group_use_lead': 'crm.group_use_lead',
    }
    group_ids = {}
    for name, xml_id in groups.items():
        try:
            group_ids[name] = env.ref(xml_id).id
        except ValueError:
            print(f"[WARN] Không tìm thấy group {xml_id}")
    return group_ids

# ============================================================
# 2. TẠO NGƯỜI DÙNG (Users)
# ============================================================
def create_users(env, group_ids):
    """Tạo users cho các vai trò khác nhau."""
    users_data = [
        # (login, name, password, role)
        # Giám đốc chi nhánh
        ("branch_director", "Nguyễn Văn An", "123", "director"),
        # Trưởng phòng Bán lẻ
        ("retail_manager", "Trần Thị Bình", "123", "retail_manager"),
        # Trưởng phòng Doanh nghiệp
        ("corp_manager", "Lê Văn Cường", "123", "corp_manager"),
        # Nhân viên Bán lẻ
        ("retail_sale_1", "Phạm Thị Dung", "123", "salesman"),
        ("retail_sale_2", "Hoàng Văn Em", "123", "salesman"),
        ("retail_sale_3", "Đỗ Thị Phương", "123", "salesman"),
        ("retail_sale_4", "Vũ Văn Giang", "123", "salesman"),
        # Nhân viên Doanh nghiệp
        ("corp_sale_1", "Bùi Thị Hạnh", "123", "salesman"),
        ("corp_sale_2", "Đinh Văn Ý", "123", "salesman"),
        ("corp_sale_3", "Ngô Thị Kim", "123", "salesman"),
        ("corp_sale_4", "Lý Văn Long", "123", "salesman"),
        ("corp_sale_5", "Mai Thị Mai", "123", "salesman"),
    ]

    role_groups = {
        "director": [
            group_ids['group_sale_manager'],
            group_ids['group_use_lead'],
        ],
        "retail_manager": [
            group_ids['group_sale_manager'],
            group_ids['group_use_lead'],
        ],
        "corp_manager": [
            group_ids['group_sale_manager'],
            group_ids['group_use_lead'],
        ],
        "salesman": [
            group_ids['group_sale_salesman'],
            group_ids['group_use_lead'],
        ],
    }

    created_users = {}
    for login, name, password, role in users_data:
        existing = env['res.users'].search([('login', '=', login)])
        if existing:
            print(f"  [SKIP] User '{name}' ({login}) đã tồn tại, bỏ qua.")
            created_users[login] = existing
            continue

        # Tạo user với context để tránh gửi mail reset password
        user = env['res.users'].with_context({'no_reset_password': True}).create({
            'login': login,
            'name': name,
            'password': password,
        })

        # Gán groups cho user thông qua SQL
        for group_id in role_groups[role]:
            env.cr.execute(
                "INSERT INTO res_groups_users_rel (gid, uid) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                [group_id, user.id]
            )
        created_users[login] = user
        print(f"  [OK] Tạo user '{name}' ({login}) - vai trò: {role}")
    return created_users

# ============================================================
# 3. TẠO SALES TEAMS (Phòng ban)
# ============================================================
def create_teams(env, users):
    """Tạo Sales Teams."""
    teams_config = [
        {
            'name': 'Kinh doanh Bán lẻ',
            'leader': users['retail_manager'],
            'members': [
                users['retail_sale_1'],
                users['retail_sale_2'],
                users['retail_sale_3'],
                users['retail_sale_4'],
            ],
            'use_leads': True,
            'use_opportunities': True,
        },
        {
            'name': 'Kinh doanh Doanh nghiệp',
            'leader': users['corp_manager'],
            'members': [
                users['corp_sale_1'],
                users['corp_sale_2'],
                users['corp_sale_3'],
                users['corp_sale_4'],
                users['corp_sale_5'],
            ],
            'use_leads': True,
            'use_opportunities': True,
        },
    ]

    created_teams = {}
    for cfg in teams_config:
        existing = env['crm.team'].search([('name', '=', cfg['name'])])
        if existing:
            print(f"  [SKIP] Team '{cfg['name']}' đã tồn tại, bỏ qua.")
            created_teams[cfg['name']] = existing
            continue

        team = env['crm.team'].create({
            'name': cfg['name'],
            'user_id': cfg['leader'].id,
            'use_leads': cfg['use_leads'],
            'use_opportunities': cfg['use_opportunities'],
        })
        created_teams[cfg['name']] = team
        print(f"  [OK] Tạo team '{cfg['name']}' với leader '{cfg['leader'].name}'")

        # Thêm members
        for member in cfg['members']:
            env['crm.team.member'].create({
                'crm_team_id': team.id,
                'user_id': member.id,
                'assignment_max': 30,
            })
            print(f"    -> Thêm member '{member.name}' vào team '{cfg['name']}'")
    return created_teams

# ============================================================
# 4. TẠO KHÁCH HÀNG (Partners)
# ============================================================
def create_partners(env):
    """Tạo danh sách khách hàng mẫu."""
    partners_config = [
        {"name": "Công ty TNHH Thương Mại Sao Mai", "phone": "02838251234", "email": "info@saomai.vn", "city": "Hồ Chí Minh"},
        {"name": "Công ty CP Đầu Tư Phát Triển Nhà Đất", "phone": "02835261234", "email": "info@nhadat.vn", "city": "Hồ Chí Minh"},
        {"name": "Ngân hàng TMCP Á Châu", "phone": "02838221234", "email": "info@acb.vn", "city": "Hồ Chí Minh"},
        {"name": "Công ty TNHH Dịch Vụ Kỹ Thuật Số", "phone": "02438221234", "email": "info@soi.vn", "city": "Hà Nội"},
        {"name": "Tập đoàn Bưu Chính Viễn Thông", "phone": "02438251234", "email": "info@vnpt.vn", "city": "Hà Nội"},
        {"name": "Công ty CP Bán Lẻ Hiện Đại", "phone": "02836251234", "email": "info@banle.vn", "city": "Hồ Chí Minh"},
        {"name": "Trường Đại Học Kinh Tế", "phone": "02838211234", "email": "info@ueh.vn", "city": "Hồ Chí Minh"},
        {"name": "Bệnh Viện Đa Khoa Trung Ương", "phone": "02438231234", "email": "info@bvtw.vn", "city": "Hà Nội"},
        {"name": "Công ty CP Sữa Việt Nam", "phone": "02838271234", "email": "info@vinamilk.vn", "city": "Hồ Chí Minh"},
        {"name": "Công ty TNHH MTV Thương Mại Điện Tử", "phone": "02839251234", "email": "info@tmd.vn", "city": "Hồ Chí Minh"},
        {"name": "Khách sạn Sài Gòn Pearl", "phone": "02838281234", "email": "info@saigonpearl.vn", "city": "Hồ Chí Minh"},
        {"name": "Công ty TNHH Sản Xuất & Thương Mại Gỗ", "phone": "027438251234", "email": "info@go.vn", "city": "Bình Dương"},
        {"name": "Công ty CP Giải Pháp Phần Mềm", "phone": "02438251234", "email": "info@soft.vn", "city": "Hà Nội"},
        {"name": "Ngân hàng TMCP Ngoại Thương", "phone": "02438241234", "email": "info@vietcombank.vn", "city": "Hà Nội"},
        {"name": "Công ty TNHH Thời Trang & Phụ Kiện", "phone": "02838225234", "email": "info@thoitrang.vn", "city": "Hồ Chí Minh"},
    ]

    created_partners = []
    for cfg in partners_config:
        existing = env['res.partner'].search([
            ('name', '=', cfg['name']),
            ('phone', '=', cfg['phone']),
        ])
        if existing:
            print(f"  [SKIP] Partner '{cfg['name']}' đã tồn tại, bỏ qua.")
            created_partners.append(existing)
            continue

        partner = env['res.partner'].create({
            'name': cfg['name'],
            'phone': cfg['phone'],
            'email': cfg['email'],
            'city': cfg['city'],
            'company_type': 'company',
        })
        created_partners.append(partner)
        print(f"  [OK] Tạo khách hàng '{cfg['name']}' - {cfg['city']}")

    return created_partners

# ============================================================
# 5. TẠO LEADS & OPPORTUNITIES
# ============================================================
def create_leads(env, users, teams, partners):
    """Tạo leads và opportunities cho từng salesperson."""
    today = datetime.now()

    leads_config = [
        # Bán lẻ - Nhân viên 1 (Phạm Thị Dung)
        {
            "name": "Mua 20 bộ bàn ghế văn phòng",
            "partner": 0,  # index in partners list
            "user": "retail_sale_1",
            "team": "Kinh doanh Bán lẻ",
            "type": "opportunity",
            "expected_revenue": 180000000,
            "probability": 60,
            "days_ago": 5,
            "stage": "crm.stage_lead3",  # Quotation sent
        },
        {
            "name": "Tư vấn nội thất showroom 200m2",
            "partner": 6,
            "user": "retail_sale_1",
            "team": "Kinh doanh Bán lẻ",
            "type": "opportunity",
            "expected_revenue": 250000000,
            "probability": 30,
            "days_ago": 10,
            "stage": "crm.stage_lead2",  # Negotiation
        },
        {
            "name": "Mua 5 kệ sách văn phòng",
            "partner": 5,
            "user": "retail_sale_1",
            "team": "Kinh doanh Bán lẻ",
            "type": "lead",
            "expected_revenue": 15000000,
            "probability": 20,
            "days_ago": 1,
            "stage": "crm.stage_lead1",  # New
        },
        # Bán lẻ - Nhân viên 2 (Hoàng Văn Em)
        {
            "name": "Trang bị bàn ghế cho 30 nhân viên",
            "partner": 2,
            "user": "retail_sale_2",
            "team": "Kinh doanh Bán lẻ",
            "type": "opportunity",
            "expected_revenue": 120000000,
            "probability": 75,
            "days_ago": 3,
            "stage": "crm.stage_lead3",
        },
        {
            "name": "Mua tủ hồ sơ di động",
            "partner": 9,
            "user": "retail_sale_2",
            "team": "Kinh doanh Bán lẻ",
            "type": "opportunity",
            "expected_revenue": 45000000,
            "probability": 40,
            "days_ago": 7,
            "stage": "crm.stage_lead2",
        },
        {
            "name": "Báo giá bàn làm việc đơn",
            "partner": 14,
            "user": "retail_sale_2",
            "team": "Kinh doanh Bán lẻ",
            "type": "lead",
            "expected_revenue": 8500000,
            "probability": 15,
            "days_ago": 1,
            "stage": "crm.stage_lead1",
        },
        # Bán lẻ - Nhân viên 3 (Đỗ Thị Phương)
        {
            "name": "Nội thất phòng họp 50 chỗ",
            "partner": 10,
            "user": "retail_sale_3",
            "team": "Kinh doanh Bán lẻ",
            "type": "opportunity",
            "expected_revenue": 350000000,
            "probability": 45,
            "days_ago": 4,
            "stage": "crm.stage_lead2",
        },
        {
            "name": "Ghế văn phòng cao cấp 15 cái",
            "partner": 1,
            "user": "retail_sale_3",
            "team": "Kinh doanh Bán lẻ",
            "type": "lead",
            "expected_revenue": 45000000,
            "probability": 25,
            "days_ago": 2,
            "stage": "crm.stage_lead1",
        },
        # Bán lẻ - Nhân viên 4 (Vũ Văn Giang)
        {
            "name": "Thiết kế & thi công nội thất VP mới",
            "partner": 4,
            "user": "retail_sale_4",
            "team": "Kinh doanh Bán lẻ",
            "type": "opportunity",
            "expected_revenue": 500000000,
            "probability": 20,
            "days_ago": 8,
            "stage": "crm.stage_lead2",
        },
        {
            "name": "Bàn họp nhóm 10 cái",
            "partner": 0,
            "user": "retail_sale_4",
            "team": "Kinh doanh Bán lẻ",
            "type": "lead",
            "expected_revenue": 28000000,
            "probability": 35,
            "days_ago": 0,
            "stage": "crm.stage_lead1",
        },
        # Doanh nghiệp - Nhân viên 1 (Bùi Thị Hạnh)
        {
            "name": "Hợp đồng trang bị nội thất cho tòa nhà 20 tầng",
            "partner": 3,
            "user": "corp_sale_1",
            "team": "Kinh doanh Doanh nghiệp",
            "type": "opportunity",
            "expected_revenue": 2500000000,
            "probability": 50,
            "days_ago": 15,
            "stage": "crm.stage_lead3",
        },
        {
            "name": "Cung cấp bàn ghế cho dự án VP mới",
            "partner": 13,
            "user": "corp_sale_1",
            "team": "Kinh doanh Doanh nghiệp",
            "type": "opportunity",
            "expected_revenue": 800000000,
            "probability": 65,
            "days_ago": 6,
            "stage": "crm.stage_lead3",
        },
        # Doanh nghiệp - Nhân viên 2 (Đinh Văn Ý)
        {
            "name": "Nội thất không gian làm việc chung",
            "partner": 12,
            "user": "corp_sale_2",
            "team": "Kinh doanh Doanh nghiệp",
            "type": "opportunity",
            "expected_revenue": 980000000,
            "probability": 35,
            "days_ago": 10,
            "stage": "crm.stage_lead2",
        },
        {
            "name": "Tư vấn thiết kế nội thất toàn bộ VP",
            "partner": 8,
            "user": "corp_sale_2",
            "team": "Kinh doanh Doanh nghiệp",
            "type": "opportunity",
            "expected_revenue": 150000000,
            "probability": 15,
            "days_ago": 3,
            "stage": "crm.stage_lead1",
        },
        # Doanh nghiệp - Nhân viên 3 (Ngô Thị Kim)
        {
            "name": "Đấu thầu nội thất trụ sở mới",
            "partner": 7,
            "user": "corp_sale_3",
            "team": "Kinh doanh Doanh nghiệp",
            "type": "opportunity",
            "expected_revenue": 5200000000,
            "probability": 25,
            "days_ago": 20,
            "stage": "crm.stage_lead2",
        },
        {
            "name": "Cung cấp ghế chờ cho sảnh bệnh viện",
            "partner": 7,
            "user": "corp_sale_3",
            "team": "Kinh doanh Doanh nghiệp",
            "type": "opportunity",
            "expected_revenue": 350000000,
            "probability": 70,
            "days_ago": 4,
            "stage": "crm.stage_lead3",
        },
        # Doanh nghiệp - Nhân viên 4 (Lý Văn Long)
        {
            "name": "Hợp đồng khung nội thất cho 5 chi nhánh",
            "partner": 11,
            "user": "corp_sale_4",
            "team": "Kinh doanh Doanh nghiệp",
            "type": "opportunity",
            "expected_revenue": 1800000000,
            "probability": 40,
            "days_ago": 12,
            "stage": "crm.stage_lead2",
        },
        {
            "name": "Bàn làm việc lập trình viên 100 cái",
            "partner": 12,
            "user": "corp_sale_4",
            "team": "Kinh doanh Doanh nghiệp",
            "type": "lead",
            "expected_revenue": 500000000,
            "probability": 10,
            "days_ago": 1,
            "stage": "crm.stage_lead1",
        },
        # Doanh nghiệp - Nhân viên 5 (Mai Thị Mai)
        {
            "name": "Nội thất phòng họp và phòng GĐ các cấp",
            "partner": 8,
            "user": "corp_sale_5",
            "team": "Kinh doanh Doanh nghiệp",
            "type": "opportunity",
            "expected_revenue": 670000000,
            "probability": 55,
            "days_ago": 5,
            "stage": "crm.stage_lead3",
        },
        {
            "name": "Tư vấn thiết kế không gian mở",
            "partner": 0,
            "user": "corp_sale_5",
            "team": "Kinh doanh Doanh nghiệp",
            "type": "lead",
            "expected_revenue": 85000000,
            "probability": 20,
            "days_ago": 2,
            "stage": "crm.stage_lead1",
        },
    ]

    # Lấy stage IDs
    stage_map = {}
    stage_names = {
        "crm.stage_lead1": "New",
        "crm.stage_lead2": "Qualified",
        "crm.stage_lead3": "Proposition",
    }
    for xml_id, _ in stage_names.items():
        try:
            stage = env.ref(xml_id)
            stage_map[xml_id] = stage.id
        except ValueError:
            print(f"  [WARN] Không tìm thấy stage {xml_id}")

    leads_created = 0
    for cfg in leads_config:
        partner = partners[cfg["partner"]] if cfg["partner"] < len(partners) else False
        user = users[cfg["user"]]
        team = teams[cfg["team"]]
        stage_id = stage_map.get(cfg["stage"])

        create_date = today - timedelta(days=cfg["days_ago"])

        lead = env['crm.lead'].create({
            'name': cfg["name"],
            'type': cfg["type"],
            'partner_id': partner.id if partner else False,
            'user_id': user.id,
            'team_id': team.id,
            'expected_revenue': cfg["expected_revenue"],
            'probability': cfg["probability"],
            'stage_id': stage_id,
            'create_date': create_date.strftime('%Y-%m-%d %H:%M:%S'),
            'date_open': (create_date + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),
        })

        # Ghi đè create_date thực tế (dùng SQL trực tiếp vì create_date là readonly)
        env.cr.execute(
            "UPDATE crm_lead SET create_date = %s WHERE id = %s",
            [create_date.strftime('%Y-%m-%d %H:%M:%S'), lead.id]
        )

        leads_created += 1
        print(f"  [OK] Tạo {cfg['type']} '{cfg['name']}' - {user.name} - {team.name}")

    return leads_created


# ============================================================
# MAIN
# ============================================================
def run_seed(env):
    print("\n" + "="*60)
    print("BẮT ĐẦU TẠO DỮ LIỆU GIẢ LẬP CRM")
    print("="*60)

    print("\n--- Bước 1: Thiết lập groups ---")
    group_ids = ensure_groups(env)
    print(f"   {len(group_ids)} groups sẵn sàng.")

    print("\n--- Bước 2: Tạo users ---")
    users = create_users(env, group_ids)
    print(f"   Tổng cộng: {len(users)} users.")

    print("\n--- Bước 3: Tạo Sales Teams ---")
    teams = create_teams(env, users)
    print(f"   Tổng cộng: {len(teams)} teams.")

    print("\n--- Bước 4: Tạo khách hàng (Partners) ---")
    partners = create_partners(env)
    print(f"   Tổng cộng: {len(partners)} khách hàng.")

    print("\n--- Bước 5: Tạo Leads & Opportunities ---")
    leads_count = create_leads(env, users, teams, partners)
    print(f"   Tổng cộng: {leads_count} leads/opportunities.")

    # Commit transaction để lưu dữ liệu vào database
    env.cr.commit()

    print("\n" + "="*60)
    print("HOÀN TẤT! Dữ liệu giả lập đã được tạo.")
    print("="*60)
    print(f"""
Tóm tắt:
  - 1 Chi nhánh: {COMPANY_NAME}
  - 11 Users (1 GĐ chi nhánh + 2 Trưởng phòng + 8 NVKD)
  - 2 Teams: Bán lẻ (4 NV) và Doanh nghiệp (5 NV)
  - 15 Khách hàng
  - {leads_count} Leads & Opportunities

Tài khoản đăng nhập (mật khẩu: 123):
  - branch_director: Giám đốc chi nhánh
  - retail_manager : Trưởng phòng Bán lẻ
  - corp_manager   : Trưởng phòng Doanh nghiệp
  - retail_sale_1..4: NVKD Bán lẻ
  - corp_sale_1..5 : NVKD Doanh nghiệp
    """)

# ============================================================
# Khi chạy qua Odoo shell (odoo-bin shell), env đã có sẵn
# ============================================================
if __name__ == '__main__':
    # Trong môi trường Odoo shell, biến 'env' đã được khởi tạo sẵn
    try:
        run_seed(env)
    except NameError:
        print("""
LỖI: Script này phải được chạy trong Odoo shell.
Cách chạy đúng:
  cd /Users/trung/projects/odoo
  python3 odoo-bin shell -c odoo.conf -d odoo_dev -- scripts/seed_crm_data.py
        """)