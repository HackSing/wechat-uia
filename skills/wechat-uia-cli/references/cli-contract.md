# CLI Contract

Primary entrypoint:

```bash
python scripts/run_wechat_skill.py <command> ...
```

Compatibility entrypoint for old history-export-only usage:

```bash
python scripts/run_wechat_uia.py --target "文件传输助手" --target-type contact --since today --max-count 20
```

## Stable JSON Shape

All commands print one JSON object.

Success payloads always include:

```json
{
  "ok": true,
  "action": "send_to",
  "result": {}
}
```

Failure payloads always include:

```json
{
  "ok": false,
  "action": "send_to",
  "error_type": "TargetNotFoundError",
  "error": "Target chat not found: '文件传输助手'"
}
```

## High-Value Commands

Environment check:

```bash
python scripts/run_wechat_skill.py check-env
```

Send a message:

```bash
python scripts/run_wechat_skill.py send-to --target "文件传输助手" --target-type contact --message "hello"
```

Send one file:

```bash
python scripts/run_wechat_skill.py send-file-to --target "文件传输助手" --file "C:\temp\demo.pdf"
```

Read history in-memory:

```bash
python scripts/run_wechat_skill.py get-chat-history --target "项目群" --target-type group --since week --max-count 50
```

Export history to files:

```bash
python scripts/run_wechat_skill.py export-history --target "项目群" --target-type group --since week --max-count 200
```

Batch send:

```bash
python scripts/run_wechat_skill.py batch-send --targets "群1" "群2" "群3" --target-type group --message "通知内容"
```

Group management:

```bash
python scripts/run_wechat_skill.py get-group-members --group "项目群"
python scripts/run_wechat_skill.py set-group-nickname --group "项目群" --nickname "值班号"
python scripts/run_wechat_skill.py set-do-not-disturb --group "项目群" --enable
python scripts/run_wechat_skill.py set-pin-chat --group "项目群" --enable
python scripts/run_wechat_skill.py modify-announcement --group "项目群" --content "今日发布窗口 18:00"
python scripts/run_wechat_skill.py set-announcement-from-markdown --group "项目群" --markdown-file "C:\temp\announcement.md"
```

Daily report batch fetch (for a configured customer list):

```bash
python scripts/run_wechat_skill.py daily-report-fetch --config config/customers.yaml --since today
python scripts/run_wechat_skill.py daily-report-fetch --config config/customers.yaml --group 战略客户
python scripts/run_wechat_skill.py daily-report-fetch --config config/customers.yaml --customer acme --customer betaco --no-cache
```

`daily-report-fetch` output shape:

```json
{
  "ok": true,
  "action": "daily_report_fetch",
  "args": { "config": "...", "since": "today", "max_count": 300, "group": null, "tag": null, "customer": null, "cache_dir": "...", "no_cache": false, "stop_on_error": false, "skip_empty": false },
  "result": {
    "report_date": "2026-04-05",
    "generated_at": "2026-04-05T18:02:11",
    "customer_count": 3,
    "success_count": 2,
    "empty_count": 0,
    "failure_count": 1,
    "from_cache": false,
    "cache_file": "<skill>/.cache/daily-report/2026-04-05.json",
    "customers": [
      {
        "id": "acme",
        "display_name": "张伟",
        "status": "ok",
        "target_used": "张伟-Acme采购",
        "tried_targets": ["张伟-Acme采购"],
        "target_type": "contact",
        "message_count": 12,
        "first_message_time": "09:14",
        "last_message_time": "17:48",
        "messages": [{ "type": "text", "content": "...", "time": "09:14" }],
        "truncated": false,
        "error": null, "error_type": null,
        "tags": ["战略客户"], "priority": "high", "company": "Acme 集团", "notes": "...",
        "from_cache": false,
        "fetched_at": "2026-04-05T18:01:58"
      }
    ]
  }
}
```

Each customer entry sets `status` to one of `ok` / `empty` / `not_found` / `error`. Per-customer failures do NOT set the top-level `ok` to `false`; the batch only fails on client-level errors (e.g., WeChat not running) or config parse errors. The `messages` array is passed through unchanged from `get-chat-history`, so sender information is still unavailable (an upstream AI layer is expected to infer sender from context). Template config lives at `config/customers.yaml.example`.

Customer follow-up pipeline:

```bash
python scripts/run_wechat_skill.py customer-followup --config config/customers.yaml --since today
python scripts/run_wechat_skill.py customer-followup --config config/customers.yaml --group 战略客户
python scripts/run_wechat_skill.py customer-followup --config config/customers.yaml --customer acme --output-root .\output\customer-followup
python scripts/run_wechat_skill.py customer-followup --config config/customers.yaml --knowledge-dir .\knowledge\real
```

`customer-followup` output shape:

```json
{
  "ok": true,
  "action": "customer_followup",
  "args": {
    "config": "...",
    "since": "today",
    "max_count": 300,
    "group": null,
    "tag": null,
    "customer": null,
    "cache_dir": "...",
    "output_root": "...",
    "history_days": 14,
    "knowledge_dir": null,
    "no_cache": false,
    "stop_on_error": false,
    "skip_empty": false
  },
  "result": {
    "report_date": "2026-04-07",
    "generated_at": "2026-04-07T19:12:00",
    "customer_count": 2,
    "success_count": 2,
    "empty_count": 0,
    "failure_count": 0,
    "from_cache": false,
    "cache_file": "<skill>/.cache/daily-report/2026-04-07.json",
    "output_root": "<repo>/output/customer-followup",
    "index_file": "<repo>/output/customer-followup/reports/2026-04-07/index.md",
    "batch_file": "<repo>/output/customer-followup/reports/2026-04-07/batch.json",
    "weekly_index_file": "<repo>/output/customer-followup/reports/weekly/2026-04-07/index.md",
    "weekly_batch_file": "<repo>/output/customer-followup/reports/weekly/2026-04-07/batch.json",
    "customers": [
      {
        "id": "acme",
        "display_name": "张伟",
        "status": "ok",
        "message_count": 12,
        "stage": "需求沟通",
        "priority": "medium",
        "knowledge_virtual": true,
        "timeline_file": "<repo>/output/customer-followup/customers/acme/timeline.md",
        "daily_file": "<repo>/output/customer-followup/customers/acme/daily/2026-04-07.json",
        "report_file": "<repo>/output/customer-followup/reports/2026-04-07/acme.md",
        "report_json_file": "<repo>/output/customer-followup/reports/2026-04-07/acme.json",
        "projects_overview_file": "<repo>/output/customer-followup/customers/acme/projects/overview.md",
        "projects_overview_json_file": "<repo>/output/customer-followup/customers/acme/projects/overview.json",
        "issues_file": "<repo>/output/customer-followup/customers/acme/issues/current.json",
        "issues_history_file": "<repo>/output/customer-followup/customers/acme/issues/history/2026-04-07.json",
        "weekly_report_file": "<repo>/output/customer-followup/reports/weekly/2026-04-07/acme.md",
        "weekly_report_json_file": "<repo>/output/customer-followup/reports/weekly/2026-04-07/acme.json",
        "from_cache": false
      }
    ]
  }
}
```

The workflow is intended for daily customer tracking. It archives each day separately, rebuilds one timeline document per customer, refreshes project and issue views, and emits both daily and weekly follow-up reports.

The daily JSON payload stored under `customers/<id>/daily/YYYY-MM-DD.json` also carries:

- the raw `log`
- `history` summary over recent days
- `analysis.digest` / `analysis.projects` / `analysis.issues`
- `analysis.selection_review` / `analysis.similar_cases`
- `analysis.execution_split`, which explicitly separates what the code already did from what an upstream LLM should keep doing

## Notes

- Prefer `check-env` once per session when runtime state is unknown.
- Prefer `send-to` or `export-history --since today --max-count 20` as a small probe.
- `get-chat-history` returns messages in JSON only.
- `export-history` writes `messages.json`, optional `messages.csv`, and `summary.json`.
- `run-workflow` uses wrapper-level action names, not raw Python method names.
