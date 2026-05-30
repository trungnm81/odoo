/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class TwilioCallDialog extends Component {
    static template = "crm_ai_banking.TwilioCallDialog";
    static props = ["*"];

    setup() {
        this.notification = useService("notification");
        this.actionService = useService("action");

        const p = this.props.action?.params || this.props;
        this.leadId = p.leadId;
        this.leadName = p.leadName || "";
        this.defaultPhone = p.phone || p.partnerPhone || "";

        this.state = useState({
            toNumber: this.defaultPhone,
            status: "idle",   // idle | calling | connected | ended | error
            callSid: null,
            errorMsg: "",
            sessionId: null,
        });
    }

    async startCall() {
        if (!this.state.toNumber) {
            this.notification.add("Vui lòng nhập số điện thoại", { type: "warning" });
            return;
        }
        this.state.status = "calling";
        this.state.errorMsg = "";

        try {
            // Tạo call session trước
            const sessionRes = await rpc("/crm/ai/call/start", {
                lead_id: this.leadId,
                session_type: "call",
                call_channel: "webrtc",
            });
            this.state.sessionId = sessionRes.session_id;

            // Gọi Twilio REST API
            const res = await rpc("/crm/ai/twilio/call", {
                lead_id: this.leadId,
                to_number: this.state.toNumber,
                session_id: this.state.sessionId,
            });

            if (res.error) {
                this.state.status = "error";
                this.state.errorMsg = res.error;
                if (res.more_info) {
                    console.error("Twilio more_info:", res.more_info);
                    this.state.errorMsg += `\n${res.more_info}`;
                }
                if (res.call_data) {
                    console.log("Call data sent:", res.call_data);
                }
                return;
            }

            this.state.callSid = res.call_sid;
            this.state.status = "connected";
            this.notification.add(
                `Đang kết nối tới ${this.state.toNumber}...`,
                { type: "info" }
            );
        } catch (e) {
            this.state.status = "error";
            this.state.errorMsg = e.message || "Lỗi không xác định";
        }
    }

    async endCall() {
        if (!this.state.callSid) return;
        try {
            // Không cần gọi Twilio API để cúp máy từ server vì người dùng cúp trực tiếp
            // Chỉ cần đóng dialog — Twilio status callback sẽ xử lý
            this.state.status = "ended";
            this.notification.add("Cuộc gọi kết thúc. AI đang tóm tắt...", { type: "success" });
            setTimeout(() => this.actionService.doAction({ type: "ir.actions.act_window_close" }), 1500);
        } catch (e) {
            this.notification.add(e.message, { type: "danger" });
        }
    }

    close() {
        this.actionService.doAction({ type: "ir.actions.act_window_close" });
    }
}

registry.category("actions").add("crm_ai_banking.twilio_call_dialog", TwilioCallDialog);
