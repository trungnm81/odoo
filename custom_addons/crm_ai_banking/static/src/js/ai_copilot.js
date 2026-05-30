/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

/**
 * AiCopilotPanel — panel gợi ý phản hồi AI cho Lead chatter
 * Dùng như standalone component, gọi qua action_send_zalo wizard
 */
class AiCopilotPanel extends Component {
    static template = "crm_ai_banking.AiCopilotPanel";
    static props = {
        leadId: Number,
        onInsert: Function,
        onClose: Function,
    };

    setup() {
        this.state = useState({ drafts: [], loading: false, error: null });
        this.rpc = useService("rpc");
        this._fetchDrafts();
    }

    async _fetchDrafts() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const result = await this.rpc("/crm/ai/copilot/suggest", {
                lead_id: this.props.leadId,
                channel: "general",
            });
            if (result.error) {
                this.state.error = result.error;
            } else {
                this.state.drafts = result.drafts || [];
            }
        } catch {
            this.state.error = "Không thể kết nối AI. Kiểm tra API key.";
        } finally {
            this.state.loading = false;
        }
    }

    selectDraft(text) {
        this.props.onInsert(text);
        this.props.onClose();
    }
}

registry.category("components").add("AiCopilotPanel", AiCopilotPanel);

export { AiCopilotPanel };
