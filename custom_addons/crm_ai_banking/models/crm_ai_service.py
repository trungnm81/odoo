import base64
import json
import logging
import re
import requests

_logger = logging.getLogger(__name__)

# ── Anonymization patterns ────────────────────────────────────────────────────
_CCCD_RE = re.compile(r'\b\d{9,12}\b')
_TAX_ID_RE = re.compile(r'\b\d{10}(?:-\d{3})?\b')
_ACCOUNT_RE = re.compile(r'\b\d{13,19}\b')

PROMPT_EMAIL_SUMMARY = """Bạn là trợ lý CRM ngân hàng. Hãy phân tích email sau và trả về JSON:
{
  "summary_bullets": ["<tối đa 3 bullet points tóm tắt>"],
  "intent": "<pricing_inquiry|ready_to_buy|complaint|document_request|general_inquiry|follow_up>",
  "urgency": "<high|medium|low>",
  "detected_needs": ["<loan|credit_card|savings|insurance|payroll|lc|fx|pos>"],
  "suggested_action": "<mô tả ngắn hành động tiếp theo>"
}
Chỉ trả về JSON, không giải thích thêm.

Subject: {subject}
Body: {body}"""

PROMPT_CALL_SUMMARY = """Bạn là trợ lý CRM ngân hàng. Hãy phân tích transcript cuộc gọi và trả về JSON:
{
  "summary": "<tóm tắt cuộc gọi 2-3 câu>",
  "action_items": ["<việc cần làm 1>", "<việc cần làm 2>"],
  "sentiment": "<positive|neutral|negative|objection>",
  "detected_needs": ["<loan|credit_card|savings|insurance|payroll|lc|fx|pos>"],
  "next_step": "<hành động tiếp theo cụ thể>",
  "key_concerns": ["<lo lắng/phản đối của khách>"]
}
Chỉ trả về JSON.

Context lead: {lead_context}
Transcript: {transcript}"""

PROMPT_GENERATE_REPLY = """Bạn là chuyên viên tư vấn ngân hàng chuyên nghiệp. Hãy soạn {num_drafts} phương án phản hồi cho tin nhắn của khách hàng.
Trả về JSON:
{
  "drafts": [
    {"tone": "<tone>", "text": "<nội dung>"}
  ]
}
Chỉ trả về JSON.

Tone: {tone}
Context lead: {lead_context}
Lịch sử hội thoại gần nhất:
{conversation}"""

PROMPT_DETECT_NEEDS = """Phân tích tin nhắn khách hàng và nhận diện nhu cầu tài chính. Trả về JSON:
{
  "needs": ["<loan|credit_card|savings|insurance|payroll|lc|fx|pos>"],
  "confidence": <0.0-1.0>,
  "signals": ["<từ/cụm từ nhận diện được>"]
}
Chỉ trả về JSON.

Tin nhắn: {message}"""

PROMPT_AI_HINTS = """Bạn là coach bán hàng ngân hàng realtime. Dựa trên transcript cuộc gọi đến thời điểm này và loại sản phẩm đang tư vấn, hãy gợi ý ngắn gọn cho nhân viên.
Trả về JSON:
{
  "detected_needs": ["<nhu cầu nhận ra>"],
  "missing_questions": ["<câu hỏi quan trọng chưa hỏi>"],
  "suggested_question": "<1 câu hỏi gợi ý ngay bây giờ>",
  "alert": "<cảnh báo nếu có, hoặc null>"
}
Chỉ trả về JSON.

Sản phẩm: {product_type}
Transcript hiện tại:
{transcript}"""

PROMPT_DAILY_DIGEST = """Bạn là trợ lý CRM. Soạn tin nhắn daily digest cá nhân hóa bằng tiếng Việt cho nhân viên kinh doanh ngân hàng.
Ngắn gọn, thân thiện, actionable. Dưới 150 từ.

Tên nhân viên: {name}
Dữ liệu hôm nay:
- Activities quá hạn: {overdue_count}
- Hot leads (xác suất >70%): {hot_leads}
- Checklist hồ sơ pending: {checklist_pending}
- Leads không liên lạc >{cold_days} ngày: {cold_leads}"""

PROMPT_COLD_LEAD_REENGAGE = """Bạn là chuyên gia CRM ngân hàng. Dựa trên lịch sử tương tác với khách hàng, gợi ý cách re-engage ngắn gọn.
Trả về JSON:
{
  "reason_cold": "<lý do có thể lead nguội>",
  "reengage_suggestion": "<cách tiếp cận lại>",
  "suggested_message": "<tin nhắn mẫu để liên hệ lại>"
}
Chỉ trả về JSON.

Lead: {lead_name}
Stage: {stage}
Ngày không liên lạc: {days_cold}
Tóm tắt lịch sử: {history_summary}"""


class CrmAiService:
    """
    Pure-Python service layer. All AI calls route through here.
    Instantiate per-request: service = CrmAiService(env)
    """

    def __init__(self, env):
        self.env = env
        self.config = env['crm.ai.config'].get_config()

    # ── Internal routers ──────────────────────────────────────────────────────

    def _claude(self, prompt: str, model: str = None, max_tokens: int = 1024) -> str:
        """Route LLM call to OpenRouter or Anthropic API based on config."""
        model = model or self.config.claude_model_text
        if self.config.llm_provider == 'openrouter':
            return self._claude_via_openrouter(prompt, model, max_tokens)
        return self._claude_via_anthropic(prompt, model, max_tokens)

    def _claude_via_openrouter(self, prompt: str, model: str, max_tokens: int) -> str:
        resp = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {self.config.openrouter_api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'max_tokens': max_tokens,
                'messages': [{'role': 'user', 'content': prompt}],
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content']

    def _claude_via_anthropic(self, prompt: str, model: str, max_tokens: int) -> str:
        resp = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': self.config.claude_api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            json={
                'model': model,
                'max_tokens': max_tokens,
                'messages': [{'role': 'user', 'content': prompt}],
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get('content', [{}])[0].get('text', '{}')

    def _claude_json(self, prompt: str, model: str = None) -> dict:
        raw = self._claude(prompt, model=model)
        try:
            # Extract JSON from potential markdown code block
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
            text = match.group(1) if match else raw
            return json.loads(text.strip())
        except json.JSONDecodeError:
            _logger.warning('AI returned non-JSON: %s', raw[:200])
            return {}

    def _call_ocr(self, image_bytes: bytes, doc_type: str) -> dict:
        """Route OCR call to api (OpenRouter) or local endpoint."""
        if self.config.ocr_provider == 'local':
            return self._call_ocr_local(image_bytes, doc_type)
        return self._call_ocr_openrouter(image_bytes, doc_type)

    @staticmethod
    def _detect_mime(image_bytes: bytes) -> str:
        """Detect image MIME type from magic bytes — works on Python 3.13+ (imghdr removed)."""
        if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            return 'image/png'
        if image_bytes[:3] == b'\xff\xd8\xff':
            return 'image/jpeg'
        if image_bytes[:4] in (b'RIFF',) and image_bytes[8:12] == b'WEBP':
            return 'image/webp'
        if image_bytes[:6] in (b'GIF87a', b'GIF89a'):
            return 'image/gif'
        return 'image/jpeg'

    def _call_ocr_openrouter(self, image_bytes: bytes, doc_type: str) -> dict:
        mime = self._detect_mime(image_bytes)

        b64 = base64.b64encode(image_bytes).decode()
        prompt = self._ocr_prompt_for_doc_type(doc_type)
        model = self.config.openrouter_ocr_model or 'qwen/qwen2.5-vl-72b-instruct'
        payload = {
            'model': model,
            'messages': [{
                'role': 'user',
                'content': [
                    {'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{b64}'}},
                    {'type': 'text', 'text': prompt},
                ],
            }],
            'max_tokens': 512,
        }
        resp = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {self.config.openrouter_api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=60,
        )
        if not resp.ok:
            err_body = {}
            try:
                err_body = resp.json()
            except Exception:
                err_body = {'raw': resp.text[:300]}
            err_msg = err_body.get('error', {})
            if isinstance(err_msg, dict):
                err_msg = err_msg.get('message', str(err_body))
            raise ValueError(
                f'OpenRouter OCR lỗi {resp.status_code} (model: {model}): {err_msg}'
            )
        content = resp.json()['choices'][0]['message']['content']
        try:
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
            return json.loads((match.group(1) if match else content).strip())
        except json.JSONDecodeError:
            return {'raw': content}

    def _call_ocr_local(self, image_bytes: bytes, doc_type: str) -> dict:
        resp = requests.post(
            self.config.ocr_local_endpoint,
            headers={'Authorization': f'Bearer {self.config.ocr_local_api_key}'},
            files={'file': ('document', image_bytes, 'image/jpeg')},
            data={'doc_type': doc_type},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def _call_stt_batch(self, audio_bytes: bytes, mime_type: str = 'audio/mpeg') -> str:
        """Route batch STT to api (OpenAI) or local (faster-whisper)."""
        if self.config.stt_batch_provider == 'local':
            return self._call_stt_batch_local(audio_bytes, mime_type)
        return self._call_stt_batch_openai(audio_bytes, mime_type)

    def _call_stt_batch_openai(self, audio_bytes: bytes, mime_type: str) -> str:
        resp = requests.post(
            self.config.whisper_api_endpoint,
            headers={'Authorization': f'Bearer {self.config.whisper_api_key}'},
            files={'file': ('audio.mp3', audio_bytes, mime_type)},
            data={'model': self.config.whisper_api_model, 'language': 'vi'},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get('text', '')

    def _call_stt_batch_local(self, audio_bytes: bytes, mime_type: str) -> str:
        resp = requests.post(
            self.config.whisper_local_endpoint,
            headers={'Authorization': f'Bearer {self.config.whisper_local_api_key}'},
            files={'file': ('audio', audio_bytes, mime_type)},
            data={'language': 'vi', 'model': self.config.whisper_local_model},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get('text', '')

    # ── Anonymization ─────────────────────────────────────────────────────────

    @staticmethod
    def anonymize(text: str) -> str:
        """Mask sensitive numbers before sending to external LLM."""
        text = _ACCOUNT_RE.sub('[ACCOUNT_NO]', text)
        text = _TAX_ID_RE.sub('[TAX_ID]', text)
        text = _CCCD_RE.sub('[ID_NUMBER]', text)
        return text

    # ── OCR prompts by doc type ───────────────────────────────────────────────

    @staticmethod
    def _ocr_prompt_for_doc_type(doc_type: str) -> str:
        prompts = {
            'cccd_front': (
                'Đây là mặt trước CCCD Việt Nam. Hãy trích xuất và trả về JSON: '
                '{"full_name": "", "date_of_birth": "", "gender": "", "nationality": "", '
                '"place_of_origin": "", "place_of_residence": "", "id_number": ""}'
            ),
            'cccd_back': (
                'Đây là mặt sau CCCD Việt Nam. Trả về JSON: '
                '{"issue_date": "", "issue_place": "", "features": ""}'
            ),
            'gpkd': (
                'Đây là Giấy phép kinh doanh Việt Nam. Trả về JSON: '
                '{"company_name": "", "tax_id": "", "address": "", "business_lines": [], '
                '"charter_capital": "", "representative": "", "issue_date": ""}'
            ),
            'bctc': (
                'Đây là Báo cáo tài chính. Trích xuất số liệu chính và trả về JSON: '
                '{"total_assets": "", "current_assets": "", "total_liabilities": "", '
                '"equity": "", "revenue": "", "net_profit": "", "year": ""}'
            ),
            'name_card': (
                'Đây là name card / danh thiếp. Trả về JSON: '
                '{"full_name": "", "title": "", "company": "", "phone": "", '
                '"email": "", "address": "", "website": ""}'
            ),
        }
        return prompts.get(doc_type, 'Trích xuất toàn bộ thông tin từ ảnh và trả về JSON.')

    # ── Public methods ────────────────────────────────────────────────────────

    def extract_card(self, image_bytes: bytes) -> dict:
        """Name card → Vision LLM (OpenRouter hoặc Anthropic tuỳ config)."""
        mime = self._detect_mime(image_bytes)
        b64 = base64.b64encode(image_bytes).decode()
        prompt = (
            'Đây là name card / danh thiếp. Trả về JSON: '
            '{"full_name": "", "title": "", "company": "", "phone": "", '
            '"email": "", "address": "", "website": ""}\nChỉ trả về JSON.'
        )
        try:
            model = self.config.claude_model_vision
            if self.config.llm_provider == 'openrouter':
                resp = requests.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {self.config.openrouter_api_key}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'model': model,
                        'max_tokens': 256,
                        'messages': [{
                            'role': 'user',
                            'content': [
                                {'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{b64}'}},
                                {'type': 'text', 'text': prompt},
                            ],
                        }],
                    },
                    timeout=60,
                )
                if not resp.ok:
                    err = resp.json().get('error', {}) if resp.text else {}
                    raise ValueError(f'OpenRouter vision lỗi {resp.status_code}: {err}')
                raw = resp.json()['choices'][0]['message']['content']
            else:
                resp = requests.post(
                    'https://api.anthropic.com/v1/messages',
                    headers={
                        'x-api-key': self.config.claude_api_key,
                        'anthropic-version': '2023-06-01',
                        'content-type': 'application/json',
                    },
                    json={
                        'model': model,
                        'max_tokens': 256,
                        'messages': [{
                            'role': 'user',
                            'content': [
                                {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': b64}},
                                {'type': 'text', 'text': prompt},
                            ],
                        }],
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                raw = resp.json().get('content', [{}])[0].get('text', '{}')
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
            return json.loads((match.group(1) if match else raw).strip())
        except Exception as e:
            _logger.error('extract_card error: %s', e)
            return {}

    def extract_id_card(self, image_bytes: bytes, side: str = 'cccd_front') -> dict:
        """CCCD → on-premise/OpenRouter OCR. Returns data WITHOUT sending raw to Claude."""
        return self._call_ocr(image_bytes, side)

    def extract_business_license(self, image_bytes: bytes) -> dict:
        return self._call_ocr(image_bytes, 'gpkd')

    def extract_financial_statement(self, pdf_bytes: bytes) -> dict:
        return self._call_ocr(pdf_bytes, 'bctc')

    def transcribe_audio(self, audio_bytes: bytes, mime_type: str = 'audio/mpeg') -> str:
        return self._call_stt_batch(audio_bytes, mime_type)

    def summarize_call(self, transcript: str, lead_context: str = '') -> dict:
        prompt = self._safe_format(
            PROMPT_CALL_SUMMARY,
            lead_context=lead_context or 'N/A',
            transcript=transcript[:6000],
        )
        return self._claude_json(prompt)

    def summarize_email(self, body: str, subject: str = '') -> dict:
        prompt = self._safe_format(
            PROMPT_EMAIL_SUMMARY,
            subject=subject or '(no subject)',
            body=body[:4000],
        )
        return self._claude_json(prompt)

    def generate_reply(self, conversation: list[dict], lead_context: str = '', tone: str = 'professional') -> list[dict]:
        conv_text = '\n'.join(f"[{m.get('author', '?')}]: {m.get('body', '')}" for m in conversation[-5:])
        prompt = self._safe_format(
            PROMPT_GENERATE_REPLY,
            num_drafts=2,
            tone=tone,
            lead_context=lead_context or 'N/A',
            conversation=conv_text,
        )
        result = self._claude_json(prompt)
        return result.get('drafts', [])

    @staticmethod
    def _safe_format(template: str, **kwargs) -> str:
        """Format prompt template an toàn với user content có thể chứa { } ."""
        for key, val in kwargs.items():
            safe_val = str(val).replace('{', '(').replace('}', ')')
            template = template.replace('{' + key + '}', safe_val)
        return template

    def detect_needs(self, message_text: str) -> dict:
        prompt = self._safe_format(PROMPT_DETECT_NEEDS, message=message_text[:2000])
        return self._claude_json(prompt)

    def get_ai_hints(self, transcript_so_far: str, product_type: str = '') -> dict:
        prompt = self._safe_format(
            PROMPT_AI_HINTS,
            product_type=product_type or 'chưa xác định',
            transcript=transcript_so_far[-3000:],
        )
        return self._claude_json(prompt)

    def generate_daily_digest(self, name: str, overdue_count: int, hot_leads: list,
                               checklist_pending: list, cold_leads: list, cold_days: int) -> str:
        hot_text = '\n'.join(f"  - {l}" for l in hot_leads[:5]) or '  (không có)'
        cold_text = '\n'.join(f"  - {l}" for l in cold_leads[:5]) or '  (không có)'
        pending_text = '\n'.join(f"  - {l}" for l in checklist_pending[:5]) or '  (không có)'
        prompt = self._safe_format(
            PROMPT_DAILY_DIGEST,
            name=name,
            overdue_count=overdue_count,
            hot_leads=hot_text,
            checklist_pending=pending_text,
            cold_days=cold_days,
            cold_leads=cold_text,
        )
        return self._claude(prompt, max_tokens=300)

    def get_cold_lead_reengage(self, lead_name: str, stage: str,
                                days_cold: int, history_summary: str) -> dict:
        prompt = self._safe_format(
            PROMPT_COLD_LEAD_REENGAGE,
            lead_name=lead_name,
            stage=stage,
            days_cold=days_cold,
            history_summary=self.anonymize(history_summary)[:2000],
        )
        return self._claude_json(prompt)

    def read_financial_statement(self, ocr_text: str) -> dict:
        """Anonymize then ask Claude for questions to ask the customer."""
        anon_text = self.anonymize(ocr_text)
        prompt = (
            'Bạn là chuyên gia tín dụng ngân hàng. Dựa trên số liệu BCTC sau (đã ẩn danh), '
            'hãy highlight điểm bất thường và gợi ý câu hỏi cho Relationship Manager. '
            'Trả về JSON: {"highlights": ["<điểm cần chú ý>"], "questions": ["<câu hỏi>"]}\n\n'
            f'BCTC:\n{anon_text[:5000]}'
        )
        return self._claude_json(prompt)

    # ── Phase 3 methods ───────────────────────────────────────────────────────

    def get_crosssell_suggestions(self, lead_context: str, existing_products: list) -> dict:
        existing_str = ', '.join(existing_products) if existing_products else 'chưa có'
        prompt = (
            'Bạn là chuyên gia cross-sell ngân hàng. Dựa trên thông tin lead và sản phẩm hiện có, '
            'gợi ý sản phẩm cross-sell phù hợp nhất. '
            'Trả về JSON: {"suggestions": [{"product": "<tên>", "reason": "<lý do>", "approach": "<cách tiếp cận>"}], '
            '"priority_product": "<sản phẩm ưu tiên nhất>"}\n\n'
            f'Context lead: {self.anonymize(lead_context[:2000])}\n'
            f'Sản phẩm hiện có: {existing_str}'
        )
        return self._claude_json(prompt)

    def generate_proposal_content(self, base_content: str, lead_context: str, custom_notes: str = '') -> str:
        anon_context = self.anonymize(lead_context)
        prompt = (
            'Bạn là chuyên viên tư vấn ngân hàng. Hãy cải thiện đề xuất sau dựa trên context lead '
            'và ghi chú của nhân viên. Giữ nguyên cấu trúc, chỉ làm cho nội dung thuyết phục hơn. '
            'Trả về văn bản đề xuất đã cải thiện (không cần JSON).\n\n'
            f'Context lead: {anon_context[:1000]}\n'
            f'Ghi chú nhân viên: {custom_notes[:500]}\n\n'
            f'Nội dung cần cải thiện:\n{base_content[:2000]}'
        )
        return self._claude(prompt, max_tokens=1500)

    # ── Phase 4 methods ───────────────────────────────────────────────────────

    def compute_next_best_action(self, lead_context: dict) -> dict:
        ctx_str = json.dumps(lead_context, ensure_ascii=False)
        prompt = (
            'Bạn là AI CRM chuyên gia ngân hàng. Phân tích trạng thái lead và đề xuất 1 hành động tốt nhất cần làm ngay. '
            'Trả về JSON:\n'
            '{"action_type": "<call|send_zalo|send_email|send_proposal|schedule_meeting|escalate_manager|'
            'send_document_reminder|close_won|mark_cold>", '
            '"action_detail": "<mô tả hành động cụ thể>", '
            '"urgency": "<high|medium|low>", '
            '"reasoning": "<lý do ngắn gọn>", '
            '"suggested_message": "<tin nhắn mẫu nếu cần liên hệ, hoặc null>", '
            '"confidence": <0.0-1.0>}\n\n'
            f'Trạng thái lead:\n{self.anonymize(ctx_str[:3000])}'
        )
        return self._claude_json(prompt)

    def score_products(self, eligible_products: list, lead_context: str) -> list:
        products_str = json.dumps(eligible_products, ensure_ascii=False)
        prompt = (
            'Bạn là chuyên gia tư vấn ngân hàng. Dựa trên thông tin khách hàng, hãy xếp hạng các sản phẩm '
            'theo mức độ phù hợp và cung cấp lý do cụ thể. '
            'Trả về JSON: {"ranked_products": [{"product_code": "<code>", "product_name": "<name>", '
            '"match_score": <0.0-1.0>, "match_reasons": ["<lý do>"], '
            '"approach_suggestion": "<cách tư vấn>", "cross_sell_trigger": ["<mã sp cross-sell>"]}]}\n\n'
            f'Context khách hàng: {self.anonymize(lead_context[:2000])}\n'
            f'Danh sách sản phẩm đủ điều kiện:\n{products_str[:2000]}'
        )
        result = self._claude_json(prompt)
        return result.get('ranked_products', [])

    def analyze_call_coaching(self, transcript: str, product_type: str = '') -> dict:
        prompt = (
            'Bạn là sales coach chuyên nghiệp cho ngân hàng. Phân tích transcript cuộc gọi bán hàng '
            'và đưa ra phản hồi chi tiết. '
            'Trả về JSON:\n'
            '{"scores": {"opening": <0-10>, "needs_discovery": <0-10>, "product_fit": <0-10>, '
            '"objection": <0-10>, "closing": <0-10>}, '
            '"strengths": ["<điểm mạnh>"], '
            '"improvements": [{"text": "<điều cần cải thiện>", "feedback": "<hướng dẫn cụ thể>"}], '
            '"missed_opportunities": ["<cơ hội bỏ lỡ>"], '
            '"key_moments": [{"timestamp_hint": "<gần dòng nào>", "speaker": "agent", '
            '"text": "<câu nói>", "feedback": "<nhận xét>", "type": "<strength|improvement>"}]}\n\n'
            f'Sản phẩm tư vấn: {product_type or "chưa xác định"}\n'
            f'Transcript:\n{transcript[:6000]}'
        )
        return self._claude_json(prompt)

    def send_zalo_message(self, zalo_user_id: str, message: str) -> bool:
        """Gửi tin nhắn Zalo OA đến user. Trả về True nếu thành công."""
        import requests
        config = self.env['crm.ai.config'].get_config()
        access_token = config.zalo_oa_access_token
        if not access_token:
            _logger.warning('Zalo OA access_token chưa cấu hình.')
            return False
        try:
            payload = {
                'recipient': {'user_id': zalo_user_id},
                'message': {'text': message},
            }
            resp = requests.post(
                'https://openapi.zalo.me/v3.0/oa/message/cs',
                headers={'access_token': access_token, 'Content-Type': 'application/json'},
                json=payload,
                timeout=10,
            )
            data = resp.json()
            if data.get('error') == 0:
                return True
            _logger.warning('Zalo send failed: %s', data)
            return False
        except Exception as e:
            _logger.error('Zalo send_message error: %s', e)
            return False

    def generate_customer_360(self, lead_data: dict) -> dict:
        anon_data = self.anonymize(json.dumps(lead_data, ensure_ascii=False))
        prompt = (
            'Bạn là AI CRM ngân hàng. Tổng hợp thông tin khách hàng thành bản tóm tắt 360 độ ngắn gọn, '
            'actionable, bằng tiếng Việt tự nhiên. '
            'Trả về JSON:\n'
            '{"profile_snapshot": "<2 câu mô tả khách hàng>", '
            '"relationship_history": "<tóm tắt lịch sử tương tác>", '
            '"current_status": "<tình trạng hiện tại và việc cần làm>", '
            '"key_needs": ["<nhu cầu chính>"], '
            '"concerns_objections": ["<lo lắng/từ chối>"], '
            '"opportunities": ["<cơ hội bán thêm>"], '
            '"recommended_approach": "<cách tiếp cận được khuyến nghị>"}\n\n'
            f'Dữ liệu lead:\n{anon_data[:4000]}'
        )
        return self._claude_json(prompt)
