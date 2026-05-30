# Tài liệu CRM AI Banking

## Mục lục

### Tiến độ & Kế hoạch
- [tien_do.md](tien_do.md) — Trạng thái các task theo phase

### Phase 1 — Tài liệu kỹ thuật

| File | Nội dung |
|------|---------|
| [phase1_p0_config_service.md](phase1_p0_config_service.md) | `crm.ai.config` + `CrmAiService` — nền tảng cấu hình và AI routing |
| [phase1_p1_live_call.md](phase1_p1_live_call.md) | Live Call Screen — gọi Twilio, STT realtime, AI hints, post-call summary |
| [phase1_p2_p3_p4_p5.md](phase1_p2_p3_p4_p5.md) | Email AI · Checklist hồ sơ · Cảnh báo lead nguội/deal lớn · Daily Digest |

### Phase 2 — Tài liệu kỹ thuật

| File | Nội dung |
|------|---------|
| [phase2_flow.md](phase2_flow.md) | Name Card Scan · CCCD Scan · Zalo Webhook · Needs Detection · AI Copilot |

### Hướng dẫn sử dụng
- [huong_dan_su_dung.md](huong_dan_su_dung.md) — Hướng dẫn dành cho nhân viên (Phase 1)
- [huong_dan_phase2.md](huong_dan_phase2.md) — Hướng dẫn Phase 2: Name Card, CCCD, Zalo, Copilot

---

## Kiến trúc tổng quan

```
crm.ai.config (singleton)
        │
        ▼
CrmAiService (pure Python, per-request)
        │
        ├─ LLM: OpenRouter / Anthropic API
        ├─ OCR: OpenRouter Qwen3 VL / Local server
        ├─ STT Batch: OpenAI Whisper / faster-whisper local
        └─ STT Realtime: Deepgram / whisper-streaming local

Models:
  crm.lead                    ← Email AI, Cold Alert, Deal Alert, Daily Digest
  crm.ai.call.session         ← Phiên gọi + AI Summary
  crm.ai.transcript.line      ← Từng câu thoại
  crm.document.checklist      ← Hồ sơ theo loại sản phẩm

Controllers:
  /crm/ai/call/*              ← Session, transcript, hints, upload audio
  /crm/ai/twilio/*            ← Gọi ra, hangup, TwiML, callbacks

Frontend:
  LiveCallScreen (OWL)        ← Màn hình gọi realtime
```

## Nguyên tắc bảo mật

**Số CCCD, MST, số tài khoản không bao giờ rời hạ tầng nội bộ.**

Dữ liệu nhạy cảm → OCR nội bộ → `anonymize()` → chỉ sau đó mới gửi Claude.

Xem chi tiết: [phase1_p0_config_service.md#3-data-privacy](phase1_p0_config_service.md)
