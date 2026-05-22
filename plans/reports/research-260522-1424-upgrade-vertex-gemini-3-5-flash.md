# Research Report: Nâng cấp Vertex AI lên Gemini 3.5 Flash

**Ngày:** 2026-05-22 14:24 (Asia/Saigon)
**Phạm vi:** Đánh giá khả năng nâng cấp model AI trong `cnl-competitor-tool` từ `gemini-3-flash-preview` lên Gemini 3.5 Flash.

## Executive Summary

**Có — nâng cấp được, và NÊN nâng cấp.** Gemini 3.5 Flash đã ra mắt tại Google I/O 2026 (19/05/2026), hỗ trợ Vertex AI, đã **GA (stable)**. Model hiện tại `gemini-3-flash-preview` vẫn là **pre-GA** (preview, support hạn chế, có thể bị deprecate). Nâng cấp = đổi 1 biến cấu hình, **không cần sửa logic code** vì model đã được tham số hóa qua env var `VERTEX_MODEL`.

## Hiện trạng codebase

| Vị trí | Giá trị hiện tại |
|---|---|
| `.env.example:5` | `VERTEX_MODEL=gemini-3-flash-preview` |
| `yt_inspector/vertex_ai.py:39` | default fallback `"gemini-3-flash-preview"` |
| `~/.claude/.ck.json` → `gemini.model` | `gemini-3-flash-preview` (chỉ dùng cho Gemini CLI / research skill — không liên quan project) |

`vertex_ai.py` build URL `.../models/{model}:generateContent` — model là string động, không hardcode logic. Endpoint hỗ trợ cả Vertex AI (`VERTEX_PROJECT_ID`) lẫn Gemini API (`generativelanguage.googleapis.com`).

## Key Findings

### 1. Gemini 3.5 Flash — tình trạng (tháng 5/2026)
- Ra mắt I/O 2026, **19/05/2026** (3 ngày trước).
- **GA / stable**, sẵn sàng production. (Trong khi `gemini-3-flash-preview` vẫn dưới "Pre-GA Offerings Terms".)
- Có trên: Vertex AI / Gemini Enterprise Agent Platform, Gemini API (AI Studio), Antigravity, Android Studio.
- Model ID API: **`gemini-3.5-flash`** — dùng đúng string này trong `:generateContent` cho cả Vertex AI và Gemini API.

### 2. Cải thiện so với 3 Flash
- Nhanh hơn ~4× output tokens/giây so với các frontier model khác.
- Vượt cả Gemini 3.1 Pro ở coding/agentic (Terminal-Bench 2.1: 76.2%, MCP Atlas: 83.6%).
- Multimodal mạnh hơn (CharXiv Reasoning 84.2%) — phù hợp use case của project: phân tích **thumbnail + title** YouTube.

### 3. Tương thích
- URL có dấu chấm (`gemini-3.5-flash`) — Google vốn dùng pattern này (`gemini-1.5-flash`, `gemini-2.5-flash`), không vấn đề.
- Payload hiện tại (`responseMimeType: application/json`, `inline_data` ảnh, `temperature`, `maxOutputTokens`) tương thích 3.5 Flash. Code đã có fallback bỏ `responseMimeType` nếu lỗi.

## Recommendation

Đổi cấu hình, **không sửa logic**:

1. `.env` thực tế (file local, không commit): `VERTEX_MODEL=gemini-3.5-flash`
2. `.env.example:5` → `VERTEX_MODEL=gemini-3.5-flash`
3. `yt_inspector/vertex_ai.py:39` → đổi default fallback thành `"gemini-3.5-flash"`
4. (Tùy chọn) `~/.claude/.ck.json` → `gemini.model: gemini-3.5-flash` nếu muốn research skill / Gemini CLI cũng dùng bản mới.

Sau khi đổi: chạy thử 1 lượt phân tích thumbnail/title để xác nhận output JSON parse đúng.

### Lưu ý
- **Pricing:** Cần kiểm tra giá `gemini-3.5-flash` trên trang Vertex AI pricing — có thể khác `gemini-3-flash-preview`. Preview đôi khi free/giảm giá; bản GA tính phí chuẩn.
- **Rollback:** Chỉ cần đổi lại `VERTEX_MODEL` về giá trị cũ nếu có sự cố — zero risk.

## Resources & References

- [Gemini 3.5 Flash — blog.google](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-5/)
- [Gemini 3.5 Flash — Vertex AI / Gemini Enterprise Agent Platform docs](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-5-flash)
- [What's new in Gemini 3.5 Flash — Gemini API docs](https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.5)
- [Gemini 3 Flash (preview) — Vertex AI docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-flash)
- [Model versions and lifecycle — Vertex AI](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions)
- [Google Introduces Gemini 3.5 Flash at I/O 2026 — MarkTechPost](https://www.marktechpost.com/2026/05/20/google-introduces-gemini-3-5-flash-at-i-o-2026-a-faster-and-cheaper-model-for-ai-agents-and-coding/)

## Unresolved Questions

1. Pricing chính xác `gemini-3.5-flash` trên Vertex AI? (Chưa tra cụ thể — cần check trang pricing.)
2. Project dùng Vertex AI endpoint (`VERTEX_PROJECT_ID`) hay Gemini API endpoint? Cả hai đều hỗ trợ `gemini-3.5-flash` nên không ảnh hưởng quyết định, nhưng pricing/quota khác nhau.
