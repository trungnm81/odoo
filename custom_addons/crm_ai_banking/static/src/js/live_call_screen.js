/** @odoo-module **/
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

const SPEAKER_LABEL = { agent: "NV", customer: "KH", unknown: "?" };
const SPEAKER_COLOR = { agent: "bg-primary", customer: "bg-success", unknown: "bg-secondary" };

/**
 * LiveCallScreen — 2 chế độ:
 *   - "record"   : Ghi âm đơn giản → upload → batch STT (dùng ngay, không cần STT server)
 *   - "realtime" : Stream realtime tới Deepgram / whisper-streaming (cần config)
 */
export class LiveCallScreen extends Component {
    static template = "crm_ai_banking.LiveCallScreen";
    // Khi mở qua ir.actions.client, Odoo truyền { action } prop
    // Khi nhúng trực tiếp, truyền leadId, leadName, sessionType
    static props = ["*"];

    setup() {
        this.notification = useService("notification");
        this.actionService = useService("action");

        // Đọc params từ action (client action) hoặc từ props trực tiếp
        const p = this.props.action?.params || this.props;
        this.leadId = p.leadId || p.lead_id;
        this.leadName = p.leadName || p.lead_name || "";
        this.sessionTypeVal = p.sessionType || "call";

        this.state = useState({
            // UI steps: channel_select → [phone_input] → ready → recording → paused → processing → done
            step: "channel_select",
            callChannel: "phone_mic",
            mode: "record",           // record | realtime (auto-detect từ sttConfig)
            sessionId: null,
            elapsedSeconds: 0,
            isRecording: false,
            transcript: [],           // batch: từ STT sau upload; realtime: từng line
            status: "",               // thông báo trạng thái cho user
            hintsEnabled: false,
            hints: null,
            sttConfig: null,
            audioChunks: [],          // ghi âm chunks
            audioBlob: null,          // blob sau khi stop
            // Twilio state
            twilioEnabled: false,     // true khi dùng kênh Twilio
            toNumber: p.phone || p.partnerPhone || "",
            callSid: null,
            twilioStatus: "idle",     // idle | calling | connected | ended | error
            twilioError: "",
        });

        this.mediaRecorder = null;
        this.audioStream = null;
        this.deepgramSocket = null;
        this.timerInterval = null;
        this.hintsInterval = null;
        this.sequenceCounter = 0;
        this.partialMap = {};

        onMounted(async () => {
            const cfg = await rpc("/crm/ai/call/stt_config");
            this.state.sttConfig = cfg;
            // Tự động chọn chế độ: realtime chỉ khi có key cấu hình đầy đủ
            const hasRealtime = cfg && (
                (cfg.provider === "deepgram" && cfg.api_key) ||
                (cfg.provider === "local" && cfg.ws_url)
            );
            this.state.mode = hasRealtime ? "realtime" : "record";
        });

        onWillUnmount(() => this._cleanup());
    }

    // ── Bước 1: chọn kênh ────────────────────────────────────────────────────

    async selectChannel(channel) {
        this.state.callChannel = channel;
        if (channel === "twilio") {
            // Twilio cần nhập số trước khi bắt đầu
            this.state.twilioEnabled = true;
            this.state.step = "phone_input";
        } else {
            this.state.twilioEnabled = false;
            await this._createSession();
            this.state.step = "ready";
        }
    }

    // ── Twilio: nhập số → gọi + tạo session ─────────────────────────────────

    async confirmTwilioCall() {
        if (!this.state.toNumber) {
            this.notification.add("Vui lòng nhập số điện thoại", { type: "warning" });
            return;
        }
        this.state.twilioStatus = "calling";
        this.state.twilioError = "";

        // Tạo session trước
        await this._createSession();
        if (!this.state.sessionId) return;

        // Khởi tạo cuộc gọi Twilio
        try {
            const res = await rpc("/crm/ai/twilio/call", {
                lead_id: this.leadId,
                to_number: this.state.toNumber,
                session_id: this.state.sessionId,
            });
            if (res.error) {
                this.state.twilioStatus = "error";
                this.state.twilioError = res.error;
                if (res.more_info) this.state.twilioError += `\n${res.more_info}`;
                this.notification.add(`Twilio: ${res.error}`, { type: "danger" });
                return;
            }
            this.state.callSid = res.call_sid;
            this.state.twilioStatus = "connected";
        } catch (e) {
            this.state.twilioStatus = "error";
            this.state.twilioError = e.message || "Lỗi không xác định";
            return;
        }

        // Chuyển sang bước "ready" để user click bật mic
        // (getUserMedia cần user gesture trực tiếp — không thể gọi sau nhiều await)
        this.state.step = "ready";
    }

    async endTwilioCall() {
        this.state.twilioStatus = "ended";
        // Cúp máy phía Twilio (nếu có call SID)
        if (this.state.callSid) {
            rpc("/crm/ai/twilio/hangup", {
                call_sid: this.state.callSid,
                session_id: this.state.sessionId,
            }).catch(() => {});
        }
        await this.endRecording();
    }

    async _createSession() {
        const res = await rpc("/crm/ai/call/start", {
            lead_id: this.leadId,
            session_type: this.sessionTypeVal,
            call_channel: this.state.callChannel,
        });
        if (res.error) {
            this.notification.add(res.error, { type: "danger" });
            return;
        }
        this.state.sessionId = res.session_id;
    }

    // ── Bước 2: bắt đầu ghi âm ───────────────────────────────────────────────

    async startRecording() {
        try {
            this.audioStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        } catch (e) {
            this.notification.add(`Không thể truy cập microphone: ${e.message}`, { type: "danger" });
            return;
        }

        this.state.audioChunks = [];
        this.state.transcript = [];
        this.state.step = "recording";
        this.state.isRecording = true;
        this._startTimer();

        if (this.state.mode === "realtime" && this.state.sttConfig) {
            this._startRealtimeSTT();
        } else {
            // Chế độ ghi âm: chỉ record, transcript sau
            this._startBatchRecorder();
        }
    }

    _startBatchRecorder() {
        const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
            ? "audio/webm;codecs=opus"
            : "audio/webm";
        this.mediaRecorder = new MediaRecorder(this.audioStream, { mimeType });
        this.mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) this.state.audioChunks.push(e.data);
        };
        this.mediaRecorder.start(1000);
    }

    // ── Pause / Resume ────────────────────────────────────────────────────────

    pauseRecording() {
        if (this.mediaRecorder?.state === "recording") this.mediaRecorder.pause();
        if (this.deepgramSocket) this.deepgramSocket.close();
        this.state.step = "paused";
        this.state.isRecording = false;
    }

    resumeRecording() {
        if (this.mediaRecorder?.state === "paused") this.mediaRecorder.resume();
        this.state.step = "recording";
        this.state.isRecording = true;
    }

    // ── Kết thúc → upload → summarize ────────────────────────────────────────

    async endRecording() {
        this.state.step = "processing";
        this.state.isRecording = false;
        this._stopTimer();

        // Stop recorder
        await new Promise((resolve) => {
            if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
                this.mediaRecorder.onstop = resolve;
                this.mediaRecorder.stop();
            } else {
                resolve();
            }
        });

        this._stopAudioStream();

        if (this.state.mode === "record") {
            await this._uploadAndTranscribe();
        } else {
            // Realtime đã có transcript → chỉ trigger summary
            await this._triggerSummary();
        }
    }

    async _uploadAndTranscribe() {
        if (!this.state.audioChunks.length) {
            this.notification.add("Không có dữ liệu ghi âm.", { type: "warning" });
            this.state.step = "ready";
            return;
        }

        this.state.status = "Đang upload ghi âm...";
        const blob = new Blob(this.state.audioChunks, { type: "audio/webm" });
        const formData = new FormData();
        formData.append("audio", blob, "recording.webm");
        formData.append("session_id", String(this.state.sessionId));

        try {
            const res = await fetch("/crm/ai/call/upload_audio", {
                method: "POST",
                body: formData,
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            const data = await res.json();
            if (data.transcript) {
                // Hiển thị transcript dạng đơn giản
                const lines = data.transcript.split("\n").filter(Boolean);
                this.state.transcript = lines.map((t, i) => ({
                    sequence: i, speaker: "unknown", text: t, is_final: true,
                }));
            }
            this.state.status = "AI đang tóm tắt cuộc gọi...";
            this.state.step = "done";
            this.notification.add("Ghi âm đã upload! AI đang xử lý...", { type: "success" });
            if (this.props.onClose) {
                setTimeout(() => this.props.onClose({ session_id: this.state.sessionId }), 2000);
            } else {
                // Đóng dialog client action
                setTimeout(() => this.actionService.doAction({ type: "ir.actions.act_window_close" }), 2000);
            }
        } catch (e) {
            this.notification.add(`Upload lỗi: ${e.message}`, { type: "danger" });
            this.state.step = "ready";
        }
    }

    async _triggerSummary() {
        await rpc("/crm/ai/call/end", { session_id: this.state.sessionId });
        this.state.step = "done";
        this.state.status = "AI đang tóm tắt...";
        this.notification.add("Đã kết thúc. AI đang tóm tắt cuộc gọi...", { type: "info" });
        if (this.props.onClose) {
            setTimeout(() => this.props.onClose({ session_id: this.state.sessionId }), 2000);
        }
    }

    // ── Realtime STT (Deepgram / local) ──────────────────────────────────────

    _startRealtimeSTT() {
        const cfg = this.state.sttConfig;
        if (cfg.provider === "deepgram") {
            this._connectDeepgram(cfg);
        } else {
            this._connectLocalWhisper(cfg);
        }
    }

    _connectDeepgram(cfg) {
        const params = new URLSearchParams({
            language: "vi", model: cfg.model || "nova-3",
            punctuate: "true", interim_results: "true",
            diarize: cfg.diarize ? "true" : "false",
        });
        const ws = new WebSocket(`wss://api.deepgram.com/v1/listen?${params}`, ["token", cfg.api_key]);
        this.deepgramSocket = ws;

        ws.onopen = () => {
            // Tạo recorder riêng gửi audio chunks thẳng tới Deepgram WebSocket
            const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
                ? "audio/webm;codecs=opus" : "audio/webm";
            const recorder = new MediaRecorder(this.audioStream, { mimeType });
            recorder.ondataavailable = (e) => {
                if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
                    ws.send(e.data);
                }
            };
            recorder.start(250);  // chunks 250ms
            this.mediaRecorder = recorder;
        };

        ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.type !== "Results") return;
            const alt = data.channel?.alternatives?.[0];
            if (!alt?.transcript) return;
            let speaker = "unknown";
            if (cfg.diarize && alt.words?.length) {
                speaker = alt.words[0].speaker === 0 ? "agent" : "customer";
            }
            this._pushLine(speaker, alt.transcript, data.is_final);
        };

        ws.onerror = (e) => {
            this.notification.add("Deepgram connection error — kiểm tra API key", { type: "danger" });
        };
    }

    _connectLocalWhisper(cfg) {
        const ws = new WebSocket(cfg.ws_url);
        ws.binaryType = "arraybuffer";
        ws.onopen = () => {
            ws.send(JSON.stringify({ language: "vi", api_key: cfg.api_key || "" }));
            // Tạo recorder gửi audio chunks tới local whisper server
            const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
                ? "audio/webm;codecs=opus" : "audio/webm";
            const recorder = new MediaRecorder(this.audioStream, { mimeType });
            recorder.ondataavailable = (e) => {
                if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
                    e.data.arrayBuffer().then((buf) => ws.send(buf));
                }
            };
            recorder.start(250);
            this.mediaRecorder = recorder;
        };
        ws.onmessage = (e) => {
            try {
                const d = JSON.parse(e.data);
                if (d.text) this._pushLine(d.speaker || "unknown", d.text, d.is_final ?? true);
            } catch (_) {}
        };
        this.deepgramSocket = ws;
    }

    _pushLine(speaker, text, isFinal) {
        const key = isFinal ? null : speaker;
        if (!isFinal && key) {
            const seq = this.partialMap[key] ?? ++this.sequenceCounter;
            this.partialMap[key] = seq;
            const existing = this.state.transcript.find(l => l.sequence === seq);
            if (existing) { existing.text = text; }
            else { this.state.transcript.push({ sequence: seq, speaker, text, is_final: false }); }
        } else {
            const seq = (key ? this.partialMap[key] : null) ?? ++this.sequenceCounter;
            if (key) delete this.partialMap[key];
            const existing = this.state.transcript.find(l => l.sequence === seq);
            if (existing) { existing.text = text; existing.is_final = true; }
            else { this.state.transcript.push({ sequence: seq, speaker, text, is_final: true }); }
            // Persist to backend
            rpc("/crm/ai/call/transcript/add", {
                session_id: this.state.sessionId, sequence: seq,
                speaker, text, timestamp: this.state.elapsedSeconds, is_final: true,
            }).catch(() => {});
        }
        this._scrollTranscript();
    }

    // ── AI Hints ─────────────────────────────────────────────────────────────

    toggleHints() {
        this.state.hintsEnabled = !this.state.hintsEnabled;
        if (this.state.hintsEnabled) {
            this.state.hints = { suggested_question: "Đang phân tích hội thoại...", missing_questions: [], alert: null };
            // Fetch ngay sau 3 giây (chờ có vài câu transcript)
            setTimeout(() => this._fetchHints(), 3000);
            // Lặp lại mỗi 15 giây
            this.hintsInterval = setInterval(() => this._fetchHints(), 15000);
        } else {
            if (this.hintsInterval) { clearInterval(this.hintsInterval); this.hintsInterval = null; }
            this.state.hints = null;
        }
    }

    async _fetchHints() {
        if (!this.state.sessionId) return;
        try {
            const hints = await rpc("/crm/ai/call/hints", {
                session_id: this.state.sessionId,
                product_type: "",
            });
            if (hints && Object.keys(hints).length) {
                this.state.hints = hints;
            }
        } catch (e) {
            // Không làm gián đoạn cuộc gọi nếu hints lỗi
            console.warn("AI hints error:", e);
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    _startTimer() {
        this.state.elapsedSeconds = 0;
        this.timerInterval = setInterval(() => {
            if (this.state.step === "recording") this.state.elapsedSeconds++;
        }, 1000);
    }

    _stopTimer() {
        if (this.timerInterval) { clearInterval(this.timerInterval); this.timerInterval = null; }
    }

    _stopAudioStream() {
        this.audioStream?.getTracks().forEach(t => t.stop());
        this.deepgramSocket?.close();
    }

    _cleanup() {
        this._stopTimer();
        if (this.hintsInterval) clearInterval(this.hintsInterval);
        this._stopAudioStream();
    }

    _scrollTranscript() {
        setTimeout(() => {
            const el = document.querySelector(".o_live_call_transcript");
            if (el) el.scrollTop = el.scrollHeight;
        }, 50);
    }

    get formattedTime() {
        const s = this.state.elapsedSeconds;
        return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
    }

    get modeLabel() {
        return this.state.mode === "realtime" ? "Realtime STT" : "Ghi âm (batch)";
    }

    getSpeakerBadge(speaker) { return SPEAKER_COLOR[speaker] || "bg-secondary"; }
    getSpeakerLabel(speaker) { return SPEAKER_LABEL[speaker] || "?"; }
}

registry.category("actions").add("crm_ai_banking.live_call_screen", LiveCallScreen);
