# Known Limitations

Updated for the current optimized UIA history collector on 2026-04-07.

The 2026-04-07 update fixed the most obvious duplication bug by switching
`get_chat_history()` from global content-based dedup to adjacent-batch
overlap merge. That improved real chats such as `AIWare` and `一辣`.

However, the UIA solution is still a UI-layer collector, not a database
reader. The remaining limits below are intentional "open risks" that other
agents should know before relying on the output.

---

## 1. Pagination is still heuristic, not exact

**Affected**: `get_chat_history`, `export-history`, `daily-report-fetch`, `customer-followup`

**Current implementation**:

- reads visible chat controls from `chat_message_list`
- treats `GetChildren()` as visual top-to-bottom order
- scrolls upward with a small mouse-wheel step
- merges adjacent batches by overlap on `(kind, content)` sequences
- stops when it sees an older timestamp, hits the safety cap, or the viewport stops changing

**What can still go wrong**:

- if one scroll step jumps too far, consecutive batches may have no reliable overlap
- if WeChat's list stops reacting near a time separator, collection ends with `reached top (scroll stuck)`
- if the provider re-renders the same viewport repeatedly, the collector may stop before the true top
- if no overlap is found, the implementation keeps the whole batch rather than dropping it, which means duplicates are still possible on some chats

**Why this still exists**:

- WeChat 4.x UIA does not expose stable database-like message ids
- wheel-to-viewport movement depends on bubble height, DPI, layout, and rich-message rendering

**Operational advice**:

- prefer daily incremental capture with `--since today` for production customer tracking
- treat `--since all` as a best-effort history export, not an audit-grade export
- if a new target is important, validate it with a small probe before trusting a large batch run

---

## 2. `reached top (scroll stuck)` does not always mean the true start of the conversation

**Affected**: `get_chat_history`

**Symptom**:

Logs may end with:

```text
stop='reached top (scroll stuck)'
```

This means the visible batch signature stopped changing. It does **not**
guarantee that WeChat exposed the absolute first message in the conversation.

**What it really means**:

- the list no longer advanced under the current UIA + wheel interaction
- sometimes that is the true top
- sometimes it is just a UI dead-zone or non-moving viewport

**Practical impact**:

- for daily follow-up reports, this is usually acceptable
- for full-history reconstruction, this remains a real accuracy limit

---

## 3. Time information is block-level, not per-message exact time

**Affected**: all chat-history collection and downstream reports

**Symptom**:

Many consecutive messages may all show the same time such as `13:55`.

**Root cause**:

WeChat UIA exposes visible time separators, not precise per-message send
timestamps. The collector attaches the most recently seen separator to the
following messages in that block.

**Impact**:

- message ordering within a block is preserved
- exact per-message timestamps are unavailable
- daily reports can say "messages happened around 13:55", but not "this exact line was sent at 13:57:23"

**Related limit**:

The CLI only supports these range selectors:

- `today`
- `yesterday`
- `week`
- `all`

There is no native arbitrary range like "last 15 days". For that use case,
the recommended path is daily accumulation through `customer-followup`.

---

## 4. Sender identity is unavailable

**Affected**: `get_chat_history`, `daily-report-fetch`, `customer-followup`

**Symptom**:

Messages have no sender field, so you cannot directly tell whether a line was
sent by the sales rep or by the customer.

**Root cause**:

WeChat 4.x's Qt UIA provider does not expose sender name or left/right
bubble direction as stable structured data.

**Impact**:

- reports must use neutral language such as "the conversation mentions..."
- any "who said what" reasoning is heuristic
- this is acceptable for sales follow-up drafts, but not for strict audit use

**Workaround**:

- let the downstream agent infer speaker roles from context
- keep `company`, `notes`, and customer metadata in `customers.yaml` accurate

---

## 5. Search/open-chat is better than before, but still brittle

**Affected**: `open_chat`, `daily-report-fetch`, `customer-followup`

**Current improvement**:

If WeChat omits the normal search-result group header like `联系人`, the code
now falls back to exact-match scanning in non-noise groups such as `未知`.

**What can still go wrong**:

- contact remark names drift over time
- the search result may only appear under `聊天记录` or `搜索网络结果`
- exact-match fallback will not rescue partial or fuzzy matches

**Operational advice**:

- use `aliases` in `customers.yaml`
- prefer stable remark names / WeChat IDs as search targets
- when one customer starts failing, update config instead of hardcoding ad hoc names elsewhere

---

## 6. Rich message types are still lossy

**Affected**: history export and downstream reports

**Current behavior**:

The collector mainly emits:

- `text`
- `link`
- `system`

**What this means in practice**:

- file cards often come out as one `link` item with multiline text
- images, voice, mini-program cards, quoted cards, transfers, red packets, and other rich items may be simplified or partially represented
- reports flatten multiline content for readability, which is good for summary reading but loses some original UI shape

**Impact**:

- enough for many sales follow-up scenarios
- not enough for exact media-forensics or message-type analytics

---

## 7. Runtime conditions still matter a lot

**Affected**: all UIA commands

**Symptom**:

Commands fail intermittently or return incomplete results when the environment changes during capture.

**Examples**:

- WeChat not in front
- user manually clicks around while capture is running
- focus moves away from the message list
- window size or DPI changes
- a popup obscures the chat area

**Operational advice**:

- keep WeChat open, logged in, and stable during runs
- avoid interacting with the WeChat window while a capture is in progress
- use `check-env` and a small probe first when runtime state is unclear

---

## 8. The customer-followup pipeline is operationally useful, not ground truth

**Affected**: `customer-followup`

**Important framing**:

The follow-up pipeline is meant to support day-to-day sales execution:

- daily archive
- timeline continuity
- report drafting
- next-action suggestions

It is **not** a perfect transcript system.

**What other agents should assume**:

- `reports/YYYY-MM-DD/<id>.md` is the best first-draft summary for that day
- `customers/<id>/timeline.md` is the best continuity document
- both inherit every limit from the underlying UIA capture

If the user needs exact legal, compliance, or forensic quality, this UIA path
is the wrong tool.
