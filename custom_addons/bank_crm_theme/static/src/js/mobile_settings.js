/** @odoo-module **/

import { rpc } from '@web/core/network/rpc';
import { onMounted } from '@odoo/owl';
import { registry } from '@web/core/registry';

// CSS rules tương ứng với mỗi config key
const MOBILE_RULES = {
    mobile_hide_account_map:    `@media(max-width:767px){.o_notebook .nav-tabs .nav-item:has([data-name="account_map"]),.o_notebook .tab-pane[name="account_map"]{display:none!important}}`,
    mobile_hide_ai_documents:   `@media(max-width:767px){.o_notebook .nav-tabs .nav-item:has([data-name="ai_documents"]),.o_notebook .tab-pane[name="ai_documents"]{display:none!important}}`,
    mobile_hide_product_recs:   `@media(max-width:767px){.o_notebook .nav-tabs .nav-item:has([data-name="product_recommendations"]),.o_notebook .tab-pane[name="product_recommendations"]{display:none!important}}`,
    mobile_hide_btn_scan_card:  `@media(max-width:767px){button[name="action_scan_name_card"]{display:none!important}}`,
    mobile_hide_btn_scan_gpkd:  `@media(max-width:767px){button[name="action_scan_gpkd"]{display:none!important}}`,
    mobile_hide_btn_proposal:   `@media(max-width:767px){button[name="action_generate_proposal"]{display:none!important}}`,
    mobile_hide_btn_zalo_remind:`@media(max-width:767px){button[name="action_zalo_remind_checklist"]{display:none!important}}`,
};

// "Xem thêm" button CSS — luôn inject, không phụ thuộc config
const SHOW_MORE_CSS = `
@media(max-width:767px){
    .bank_mobile_show_more_btn{
        white-space:nowrap;font-size:0.75rem;padding:0.35rem 0.6rem;
        border:1px solid #dee2e6;border-radius:4px;background:#fff;
        cursor:pointer;color:#0054A5;
    }
    .bank_mobile_show_more_btn:hover{background:#e9f0fb}
}
@media(min-width:768px){.bank_mobile_show_more_btn{display:none!important}}
`;

function injectMobileCSS(config) {
    // Xóa style cũ nếu có
    const existing = document.getElementById('bank_crm_mobile_config');
    if (existing) existing.remove();

    const css = Object.entries(config)
        .filter(([key, val]) => val && MOBILE_RULES[key])
        .map(([key]) => MOBILE_RULES[key])
        .join('\n');

    const style = document.createElement('style');
    style.id = 'bank_crm_mobile_config';
    style.textContent = css + '\n' + SHOW_MORE_CSS;
    document.head.appendChild(style);

    // Thêm nút "⋯ Xem thêm" vào các notebook trên mobile
    if (window.innerWidth < 768) {
        injectShowMoreButtons(config);
    }
}

function injectShowMoreButtons(config) {
    // Chạy sau khi DOM render xong — dùng MutationObserver để chờ notebook
    const observer = new MutationObserver(() => {
        document.querySelectorAll('.o_notebook .nav-tabs').forEach(navTabs => {
            if (navTabs.querySelector('.bank_mobile_show_more_btn')) return;

            const li = document.createElement('li');
            li.className = 'nav-item';
            const btn = document.createElement('button');
            btn.className = 'bank_mobile_show_more_btn nav-link';
            btn.textContent = '⋯';
            btn.title = 'Xem tất cả tab';
            let expanded = false;
            btn.addEventListener('click', () => {
                expanded = !expanded;
                btn.textContent = expanded ? '✕' : '⋯';
                btn.title = expanded ? 'Thu gọn' : 'Xem tất cả tab';
                // Toggle: xóa hoặc thêm lại style ẩn
                const styleEl = document.getElementById('bank_crm_mobile_config');
                if (styleEl) styleEl.disabled = expanded;
            });
            li.appendChild(btn);
            navTabs.appendChild(li);
        });
    });
    observer.observe(document.body, { childList: true, subtree: true });
    // Dừng observe sau 30s để không tốn tài nguyên
    setTimeout(() => observer.disconnect(), 30000);
}

// Service đăng ký với Odoo app registry — chạy khi app boot
const bankMobileService = {
    name: 'bank_crm_mobile',
    async start() {
        try {
            const config = await rpc('/bank_crm_theme/mobile_config', {});
            injectMobileCSS(config);
        } catch (e) {
            // Không crash app nếu service fail
            console.warn('bank_crm_theme: không lấy được mobile config', e);
        }
    },
};

registry.category('services').add('bank_crm_mobile', bankMobileService);
