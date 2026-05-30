# Tiến độ phát triển CRM AI Banking

> Cập nhật lần cuối: 2026-05-29

---

## Phase 1 — Core Infrastructure ✅ Hoàn thành

### P1-0. Cấu hình & Service Layer ✅
| Task | Trạng thái | File |
|------|-----------|------|
| Model `crm.ai.config` — singleton cấu hình tập trung | ✅ | `models/crm_ai_config.py` |
| LLM: OpenRouter + Anthropic, switch không đổi code | ✅ | `models/crm_ai_config.py` |
| OCR: OpenRouter (Qwen3 VL) + Local API | ✅ | `models/crm_ai_config.py` |
| STT Batch: OpenAI Whisper API + Local faster-whisper | ✅ | `models/crm_ai_config.py` |
| STT Realtime: Deepgram API + local whisper-streaming | ✅ | `models/crm_ai_config.py` |
| Twilio Voice: Account SID, Auth Token, From Number, Public URL | ✅ | `models/crm_ai_config.py` |
| Zalo OA: Access Token, Webhook Secret | ✅ | `models/crm_ai_config.py` |
| Test buttons cho mọi provider (LLM, OCR, STT Batch, STT Realtime, Twilio) | ✅ | `models/crm_ai_config.py` |
| `CrmAiService` — service layer, router tất cả AI calls | ✅ | `models/crm_ai_service.py` |
| `_safe_format()` — tránh KeyError khi content có `{` `}` | ✅ | `models/crm_ai_service.py` |
| HTTP calls dùng `requests` trực tiếp (không cần SDK) | ✅ | `models/crm_ai_service.py` |
| Menu "AI Banking" + action "AI Configuration" | ✅ | `views/crm_ai_config_views.xml` |

### P1-1. Realtime Call & Meeting Screen ✅
| Task | Trạng thái | File |
|------|-----------|------|
| Model `crm.ai.call.session` | ✅ | `models/crm_ai_call_session.py` |
| Model `crm.ai.transcript.line` | ✅ | `models/crm_ai_transcript_line.py` |
| OWL `LiveCallScreen` — 4 kênh: Twilio / phone_mic / webrtc / mobile | ✅ | `static/src/js/live_call_screen.js` |
| Chế độ Ghi âm (batch) — record → upload → Whisper STT | ✅ | `live_call_screen.js` |
| Chế độ Realtime STT — Deepgram WebSocket streaming | ✅ | `live_call_screen.js` |
| Transcript realtime (partial → final lines) | ✅ | `live_call_screen.js` |
| AI Hints — opt-in, fetch mỗi 15s từ Claude | ✅ | `live_call_screen.js` |
| Timer, recording animation, badge trạng thái | ✅ | `live_call_screen.js` |
| POST `/crm/ai/call/start` — tạo session | ✅ | `controllers/call_stream.py` |
| POST `/crm/ai/call/end` — kết thúc + trigger AI summary | ✅ | `controllers/call_stream.py` |
| POST `/crm/ai/call/transcript/add` — lưu từng dòng transcript | ✅ | `controllers/call_stream.py` |
| GET `/crm/ai/call/hints` — AI hints realtime | ✅ | `controllers/call_stream.py` |
| POST `/crm/ai/call/upload_audio` — upload ghi âm batch | ✅ | `controllers/call_stream.py` |
| AI Summary async (threading pattern) → post vào chatter | ✅ | `models/crm_ai_call_session.py` |
| Nút "🎤 Gọi AI" trên form lead | ✅ | `views/crm_lead_views_inherit.xml` |
| Stat button "Cuộc gọi AI" trên form lead | ✅ | `views/crm_lead_views_inherit.xml` |
| **Twilio tích hợp vào "Gọi AI"** — kênh Twilio gọi ra SĐT khách | ✅ | `live_call_screen.js` |
| Twilio phone normalization (VN: 0xxx → +84xxx) | ✅ | `controllers/twilio_voice.py` |
| Twilio hangup từ browser `/crm/ai/twilio/hangup` | ✅ | `controllers/twilio_voice.py` |
| Twilio recording callback → batch STT → AI summary | ✅ | `controllers/twilio_voice.py` |
| Twilio status callback → auto-trigger summary khi gọi xong | ✅ | `controllers/twilio_voice.py` |
| Error handling Twilio 21219 (trial account) + hướng dẫn verify | ✅ | `templates + controllers` |

### P1-2. Email AI ✅
| Task | Trạng thái | File |
|------|-----------|------|
| Override `message_new()` → auto-process email đến | ✅ | `models/mail_thread.py` |
| Claude phân tích intent, urgency, detected_needs | ✅ | `models/crm_ai_service.py` |
| Post internal note tóm tắt vào chatter | ✅ | `models/crm_lead.py` |
| Auto-tạo activity theo intent (follow up, báo giá, v.v.) | ✅ | `models/crm_lead.py` |
| Async processing dùng threading pattern | ✅ | `models/crm_lead.py` |

### P1-3. Checklist Hồ sơ Động ✅
| Task | Trạng thái | File |
|------|-----------|------|
| Model `crm.document.checklist` + lines | ✅ | `models/crm_ai_document_checklist.py` |
| Template checklist theo loại sản phẩm | ✅ | `models/crm_ai_document_checklist.py` |
| Field `product_type` trên `crm.lead` | ✅ | `models/crm_lead.py` |
| Hiển thị checklist trên form lead | ✅ | `views/crm_lead_views_inherit.xml` |

### P1-4. Cảnh báo Lead Nguội + Deal Lớn ✅
| Task | Trạng thái | File |
|------|-----------|------|
| Cron daily check lead nguội → gợi ý re-engage | ✅ | `data/ir_cron_data.xml` |
| Alert deal lớn không có manager activity | ✅ | `models/crm_lead.py` |
| Threshold cấu hình trong `crm.ai.config` | ✅ | `models/crm_ai_config.py` |

### P1-5. Daily Digest ✅
| Task | Trạng thái | File |
|------|-----------|------|
| Cron 8h sáng → Claude tổng hợp → gửi qua discuss DM | ✅ | `data/ir_cron_data.xml` |
| Per-salesperson: overdue activities, hot leads, checklist pending | ✅ | `models/crm_lead.py` |

---

## Phase 2 — Capture & Zalo ✅ Hoàn thành

### P2-1. Name Card Scan
| Task | Trạng thái | File |
|------|-----------|------|
| Wizard `crm.ai.scan.document` — scan_type: name_card/cccd/gpkd | ✅ | `wizard/crm_ai_scan_document.py` |
| Claude Vision extract: tên, phone, email, company, title | ✅ | `models/crm_ai_service.py:extract_card()` |
| Check duplicate qua phone / email → tạo lead hoặc update partner | ✅ | `wizard/crm_ai_scan_document.py:_apply_name_card()` |
| REST `POST /crm/ai/scan-card` cho mobile | ✅ | `controllers/zalo_webhook.py` |
| Button "📇 Quét Card" trên form lead | ✅ | `views/crm_lead_views_inherit.xml` |

### P2-2. CCCD Scan
| Task | Trạng thái | File |
|------|-----------|------|
| `_call_ocr(image, 'cccd_front')` → OCR + số CCCD không rời nội bộ | ✅ | `models/crm_ai_service.py:extract_id_card()` |
| Lưu số CCCD vào `res.partner.cccd_number` (ẩn với nhân viên thường) | ✅ | `models/res_partner.py` |
| `res.partner` extension: cccd_number, date_of_birth, gender, zalo_user_id | ✅ | `models/res_partner.py` |
| Auto-fill partner: name, dob, gender, address từ OCR | ✅ | `wizard/crm_ai_scan_document.py:_apply_cccd()` |

### P2-3. Zalo Integration
| Task | Trạng thái | File |
|------|-----------|------|
| Webhook `POST /crm/ai/webhook/zalo` — verify HMAC SHA256 signature | ✅ | `controllers/zalo_webhook.py` |
| Match lead theo zalo_user_id / tạo lead mới, tag "Từ Zalo" | ✅ | `models/crm_lead.py:_handle_zalo_incoming()` |
| Log message vào chatter, async AI detect intent/needs | ✅ | `models/crm_lead.py` |
| Button "📱 Gửi Zalo" + Wizard compose (AI gợi ý 2 draft) | ✅ | `wizard/crm_ai_zalo_compose.py` |
| REST `POST /crm/ai/zalo/send` cho API call | ✅ | `controllers/zalo_webhook.py` |
| `zalo_user_id` field trên `crm.lead` và `res.partner` | ✅ | `models/crm_lead.py`, `models/res_partner.py` |

### P2-4. Nhận diện Nhu cầu Tài chính
| Task | Trạng thái | File |
|------|-----------|------|
| `detect_needs()` — Claude classify loan/card/savings/insurance/v.v. | ✅ | `models/crm_ai_service.py` |
| Auto-update `lead.tag_ids` từ email, Zalo, cuộc gọi | ✅ | `models/crm_lead.py:_apply_needs_tags()` |
| Manual trigger từ chatter messages | ✅ | `models/crm_lead.py:action_detect_needs()` |

### P2-5. Copilot Soạn Tin nhắn
| Task | Trạng thái | File |
|------|-----------|------|
| Backend `/crm/ai/copilot/suggest` → 2 drafts từ lịch sử chatter | ✅ | `controllers/zalo_webhook.py` |
| OWL `AiCopilotPanel` — sinh 2 draft, click "Dùng" để điền | ✅ | `static/src/js/ai_copilot.js` |
| Wizard Zalo Compose tích hợp AI drafts (tone: informal/professional) | ✅ | `wizard/crm_ai_zalo_compose.py` |
| Nhân viên luôn review trước khi gửi — không auto-send | ✅ | Design principle |

---

## Phase 3 — B2B Deep Features ✅ Hoàn thành

| Task | Trạng thái | File |
|------|-----------|------|
| **P3-1** Account Map B2B — model `crm.account.contact` | ✅ | `models/crm_account_contact.py` |
| **P3-1** View stakeholders inline trên Lead form (tab "🏢 Account Map B2B") | ✅ | `views/crm_account_contact_views.xml` |
| **P3-2** GPKD Scan — OCR + anonymize MST + auto-fill partner | ✅ | `wizard/crm_ai_scan_document.py:_apply_gpkd()` |
| **P3-2** Button "🏢 Quét GPKD" trên header lead | ✅ | `views/crm_lead_views_inherit.xml` |
| **P3-3** Model `crm.ai.document` — BCTC/GPKD/Sao kê | ✅ | `models/crm_ai_document.py` |
| **P3-3** OCR + anonymize + Claude gợi ý câu hỏi | ✅ | `models/crm_ai_service.py:read_financial_statement()` |
| **P3-3** Tab "📊 Tài liệu AI" trên Lead form | ✅ | `views/crm_lead_views_inherit.xml` |
| **P3-4** Wizard `crm.ai.generate.proposal` — template fill + AI enhance | ✅ | `wizard/crm_ai_generate_proposal.py` |
| **P3-4** Button "📄 Sinh đề xuất" trên header lead | ✅ | `views/crm_lead_views_inherit.xml` |
| **P3-5** Cross-sell Engine — AI gợi ý sản phẩm cross-sell | ✅ | `models/crm_lead.py:action_crosssell_suggestions()` |
| **P3-5** `crm_ai_service.get_crosssell_suggestions()` | ✅ | `models/crm_ai_service.py` |

---

## Phase 4 — AI Intelligence Layer ✅ Hoàn thành

| Task | Trạng thái | File |
|------|-----------|------|
| **P4-1** NBA fields trên `crm.lead` (nba_action_type, detail, urgency, v.v.) | ✅ | `models/crm_lead.py` |
| **P4-1** `_ai_run_nba()` + `crm_ai_service.compute_next_best_action()` | ✅ | `models/crm_lead.py`, `crm_ai_service.py` |
| **P4-1** NBA banner trên đầu form lead (hiển thị action + reasoning + message) | ✅ | `views/crm_lead_views_inherit.xml` |
| **P4-1** Cron daily refresh NBA | ✅ | `data/ir_cron_data.xml` |
| **P4-2** Model `crm.product.eligibility.rule` — rule engine admin-configurable | ✅ | `models/crm_product_recommendation.py` |
| **P4-2** Model `crm.product.recommendation` — AI scoring + top 3 | ✅ | `models/crm_product_recommendation.py` |
| **P4-2** 8 sản phẩm mẫu pre-loaded | ✅ | `data/product_eligibility_data.xml` |
| **P4-2** Tab "🏦 Sản phẩm phù hợp" trên Lead form | ✅ | `views/crm_lead_views_inherit.xml` |
| **P4-3** Model `crm.ai.coaching.report` — 5 scores + key moments | ✅ | `models/crm_ai_coaching_report.py` |
| **P4-3** Tab "🏆 AI Sales Coach" trên phiên gọi | ✅ | `views/crm_ai_call_session_views.xml` |
| **P4-3** `crm_ai_service.analyze_call_coaching()` | ✅ | `models/crm_ai_service.py` |
| **P4-4** Customer 360 fields + `_ai_run_customer_360()` | ✅ | `models/crm_lead.py` |
| **P4-4** Tab "👤 Customer 360°" trên Lead form | ✅ | `views/crm_lead_views_inherit.xml` |
| **P4-4** `crm_ai_service.generate_customer_360()` | ✅ | `models/crm_ai_service.py` |

---

## Hạ tầng & DevOps

| Item | Trạng thái | Ghi chú |
|------|-----------|---------|
| Twilio trial account — verify số `+84983511981` | ⚠️ Cần làm | Twilio Console → Verified Caller IDs |
| Ngrok / Public URL cho Twilio callbacks trong dev | ⚠️ Cần làm | Điền vào AI Config → Twilio → Public URL |
| Deepgram API key đã cấu hình | ✅ | |
| OpenRouter API key đã cấu hình | ✅ | |
| Local OCR server | 🔲 Tuỳ chọn | Có thể dùng OpenRouter trước |
| Local Whisper server | 🔲 Tuỳ chọn | Có thể dùng OpenAI Whisper API trước |

---

## Tóm tắt nhanh

| Phase | Tiến độ |
|-------|---------|
| Phase 1 — Core | ✅ **Hoàn thành** |
| Phase 2 — Capture & Zalo | ✅ **Hoàn thành** |
| Phase 3 — B2B Deep | ✅ **Hoàn thành** (2026-05-29) |
| Phase 4 — AI Intelligence | ✅ **Hoàn thành** (2026-05-29) |

**🎉 Tất cả 4 phase đã hoàn thành!**

**Bước tiếp theo:**
1. Chạy `./odoo-bin -u crm_ai_banking -d odoo_dev -c odoo.conf` để upgrade
2. Cấu hình Quy tắc sản phẩm (Menu AI Banking → Quy tắc sản phẩm)
3. Test NBA, Customer 360, Sales Coach trên lead thực tế
4. Xem hướng dẫn chi tiết: `docs/phase3_phase4_guide.md`
