/** @odoo-module **/
import { Component, useState, useRef, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * CameraCaptureWidget — field widget thay thế binary widget cho ảnh OCR.
 * Hỗ trợ 2 chế độ:
 *   1. 📷 Chụp ảnh trực tiếp — dùng camera (mobile: camera sau, desktop: webcam)
 *   2. 📁 Upload file — file picker thông thường
 */
class CameraCaptureWidget extends Component {
    static template = "crm_ai_banking.CameraCaptureWidget";
    static props = { ...standardFieldProps };
    static supportedTypes = ["binary"];

    setup() {
        this.state = useState({
            preview: null,        // data URL để hiển thị preview
            capturing: false,     // đang xem live camera stream
            error: null,
        });
        this.fileInputRef = useRef("fileInput");
        this.cameraInputRef = useRef("cameraInput");
        this.videoRef = useRef("video");
        this.canvasRef = useRef("canvas");
        this._stream = null;

        onWillUnmount(() => this._stopStream());
    }

    get hasValue() {
        return !!this.props.record.data[this.props.name];
    }

    // ── File upload thông thường ──────────────────────────────────────────────

    triggerFileUpload() {
        this.fileInputRef.el?.click();
    }

    async onFileSelected(ev) {
        const file = ev.target.files?.[0];
        if (!file) return;
        await this._processFile(file);
        ev.target.value = "";   // reset để cho phép chọn cùng file lần sau
    }

    // ── Chụp ảnh từ camera ────────────────────────────────────────────────────
    // Mobile: dùng input capture="environment" → mở camera sau trực tiếp
    // Desktop: dùng getUserMedia → live webcam stream

    async triggerCameraCapture() {
        const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
        if (isMobile) {
            this.cameraInputRef.el?.click();
        } else {
            await this.startLiveCamera();
        }
    }

    async onCameraFileSelected(ev) {
        const file = ev.target.files?.[0];
        if (!file) return;
        await this._processFile(file);
        ev.target.value = "";
    }

    // ── Live camera stream (desktop webcam) ──────────────────────────────────

    async startLiveCamera() {
        this.state.error = null;
        try {
            this._stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
                audio: false,
            });
            this.state.capturing = true;
            // Cần nextTick để video element render xong
            await Promise.resolve();
            if (this.videoRef.el) {
                this.videoRef.el.srcObject = this._stream;
                await this.videoRef.el.play();
            }
        } catch (e) {
            this.state.error = "Không thể truy cập camera: " + (e.message || e);
            this._stopStream();
        }
    }

    captureFromLive() {
        const video = this.videoRef.el;
        const canvas = this.canvasRef.el;
        if (!video || !canvas) return;
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0);
        canvas.toBlob(async (blob) => {
            if (blob) {
                this._stopStream();
                this.state.capturing = false;
                await this._processFile(new File([blob], "capture.jpg", { type: "image/jpeg" }));
            }
        }, "image/jpeg", 0.92);
    }

    cancelLiveCamera() {
        this._stopStream();
        this.state.capturing = false;
    }

    _stopStream() {
        if (this._stream) {
            this._stream.getTracks().forEach(t => t.stop());
            this._stream = null;
        }
    }

    // ── Xử lý file → base64 → cập nhật field ─────────────────────────────────

    async _processFile(file) {
        const MAX_MB = 10;
        if (file.size > MAX_MB * 1024 * 1024) {
            this.state.error = `File quá lớn (${(file.size / 1024 / 1024).toFixed(1)} MB). Tối đa ${MAX_MB} MB.`;
            return;
        }
        this.state.error = null;
        const dataUrl = await this._readAsDataURL(file);
        this.state.preview = dataUrl;

        // Lấy base64 thuần (bỏ phần "data:image/jpeg;base64,")
        const b64 = dataUrl.split(",")[1];
        await this.props.record.update({ [this.props.name]: b64 });
    }

    _readAsDataURL(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = e => resolve(e.target.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    clearImage() {
        this.state.preview = null;
        this.props.record.update({ [this.props.name]: false });
    }

    // ── Preview URL ───────────────────────────────────────────────────────────

    get previewSrc() {
        if (this.state.preview) return this.state.preview;
        const val = this.props.record.data[this.props.name];
        if (val && typeof val === "string") return "data:image/jpeg;base64," + val;
        return null;
    }
}

export const cameraCaptureField = {
    component: CameraCaptureWidget,
    supportedTypes: ["binary"],
    extractProps: ({ attrs }) => ({ name: attrs.name }),
};

registry.category("fields").add("camera_capture", cameraCaptureField);

export { CameraCaptureWidget };
