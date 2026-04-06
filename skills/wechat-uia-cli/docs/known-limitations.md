# Known Limitations

## 1. Content-based dedup merges identical messages

**Affected**: `get_chat_history` in `scripts/vendor/wx4py/pages/chat_window.py`

**Symptom**: If a user sends the exact same text or emoji twice in a conversation (e.g. two `[呲牙]` in a row), only one copy appears in the output.

**Root cause**: `get_chat_history` scrolls through the chat and collects messages across multiple overlapping viewport batches. To eliminate duplicates caused by viewport overlap, it deduplicates by message content (first occurrence wins). This cannot distinguish "same message seen twice across batches" from "two genuinely different messages with identical content".

**Why not use UIA RuntimeId?** Attempted and abandoned (2026-04-05). WeChat's Qt/mmui UIA provider **recycles RuntimeId** when controls scroll in/out of the viewport — the same RID gets assigned to completely different messages across batches, causing false merges (5+ messages silently dropped in testing).

**Why not use suffix-prefix overlap merge?** Also attempted and abandoned (2026-04-06). WeChat's Qt wheel handler + varying message heights + DPI scaling make the scroll-step-to-viewport-size ratio unpredictable. Consecutive batches may have no overlap (gap) or partial overlap, causing suffix-prefix matching to fail. Results ranged from massive duplication (42 msgs vs 22 real) to partial duplication (30-31 msgs).

**Impact**: For the primary use case (AI-generated daily sales reports), losing a repeated emoji or short phrase is negligible — AI summarisation naturally ignores duplicate expressions. Tested with 22 real messages → output 21 (one duplicate emoji merged).

**Future fix path**: If a future WeChat version or UIA provider update makes RuntimeId stable across scroll batches, `get_chat_history` can switch back to RID-based dedup. The `_read_visible_chat_items` method already captures RuntimeId in its return value for this purpose.

---

## 2. Search result group header may be missing

**Affected**: `_find_target_result` / `_parse_search_results` in `scripts/vendor/wx4py/pages/chat_window.py`

**Symptom**: `open_chat` fails with `TargetNotFoundError` even though the contact exists in WeChat.

**Root cause**: WeChat 4.x search popup sometimes omits group header rows (e.g. the "联系人" label that normally appears above contact results). The `_parse_search_results` parser groups items by their preceding header; when no header is present, items land in the `"未知"` bucket. The original `_find_target_result` only checked `"联系人"`, `"群聊"`, and `"功能"` groups.

**Fix applied** (2026-04-05): `_find_target_result` now falls back to scanning all non-noise groups (excluding `"搜索网络结果"` and `"聊天记录"`) for items with `auto_id` starting with `search_item_` and an exact name match. This catches contacts in the `"未知"` bucket.

**Diagnostic tip**: If a contact still can't be found, run `search --keyword <name>` and check which group the result appears in. If it only appears in `"聊天记录"` or `"搜索网络结果"`, the fallback won't match — use the `aliases` field in `customers.yaml` to try alternative search terms (e.g. the contact's WeChat ID or a different nickname).

---

## 3. Sender information unavailable

**Affected**: All chat history collection (`get_chat_history`, `daily-report-fetch`)

**Symptom**: Messages in the output have no sender field — you cannot tell which messages were sent by the sales rep vs. the customer.

**Root cause**: WeChat 4.x's Qt UIA provider does not expose sender names or direction on message bubble controls. This is a platform-level limitation, not a bug in wx4py.

**Workaround**: The downstream AI layer (Claude) infers sender from conversational context (sentence patterns, question-answer flow, tone). For the daily sales report use case, this inference is typically accurate enough. The `notes` field in `customers.yaml` can provide persona hints to improve inference quality.
