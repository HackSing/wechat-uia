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

Desktop export dialog automation:

```bash
python scripts/run_wechat_skill.py desktop-export --targets "项目群" "文件传输助手" --time-range-label "三个月内" --content-scope-label "部分聊天记录"
```

## Notes

- Prefer `check-env` once per session when runtime state is unknown.
- Prefer `send-to` or `export-history --since today --max-count 20` as a small probe.
- `get-chat-history` returns messages in JSON only.
- `export-history` writes `messages.json`, optional `messages.csv`, and `summary.json`.
- `run-workflow` uses wrapper-level action names, not raw Python method names.
