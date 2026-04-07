---
name: wechat-uia-cli
description: Self-contained Windows WeChat 4.x automation skill backed by vendored wx4py and wechat-rpa runtime code. Use when Codex needs to search contacts or groups, open chats, send messages or files, batch send, export or analyze chat history, inspect UIA state, manage groups, or troubleshoot WeChat UI automation on this machine.
---

# Wechat Uia Cli

Use `python scripts/run_wechat_skill.py ...` as the primary entrypoint. Do not depend on `D:\Project\wx4py`; this skill vendors the runtime under `scripts/vendor/`. The wrapper also auto-installs missing third-party Python packages on first use through `python -m pip install`.

## Quick Start

Check runtime prerequisites first:

```bash
python scripts/run_wechat_skill.py check-env
```

Send a validation message:

```bash
python scripts/run_wechat_skill.py send-to --target "文件传输助手" --target-type contact --message "skill smoke test"
```

Export recent history:

```bash
python scripts/run_wechat_skill.py export-history --target "文件传输助手" --target-type contact --since today --max-count 20
```

## Workflow

1. Run `check-env` when the environment has not been verified in the current session. This also triggers runtime dependency bootstrap.
2. Prefer a low-risk probe first:
   - `search`
   - `snapshot`
   - `send-to` with `文件传输助手`
   - `export-history --since today --max-count 20`
3. Use direct commands instead of ad hoc Python when the wrapper already supports the task.
4. Treat JSON `ok: false` as a hard failure and report `error_type` plus `error`.
5. For write operations, state exactly which target was used and whether the command returned success.

## Command Families

- Runtime and diagnostics:
  - `check-env`
  - `snapshot`
  - `inspect --max-depth N`
  - `search --keyword ...`
- Messaging:
  - `open-chat`
  - `send-message`
  - `send-to`
  - `batch-send`
  - `send-file`
  - `send-file-to`
- History:
  - `get-chat-history`
  - `export-history`
  - `daily-report-fetch` — batch-fetch today's messages for a configured customer list (reads `config/customers.yaml`)
- Group management:
  - `get-group-members`
  - `set-group-nickname`
  - `set-do-not-disturb --enable|--disable`
  - `set-pin-chat --enable|--disable`
  - `modify-announcement`
  - `set-announcement-from-markdown`
- Reusable automation:
  - `run-workflow --workflow path\to\workflow.json`

For the JSON contract and examples, read `references/cli-contract.md`.
For workflow shape and supported step names, read `references/workflow-schema.md`.
For reusable code examples, read files under `references/examples/`.

## Operating Rules

- Keep WeChat open and logged in on Windows.
- Assume the WeChat window must stay in the foreground during automation.
- Allow the wrapper to install missing Python packages on first use.
- Prefer `target_type=contact` unless the target is explicitly a group.
- Validate risky operations on `文件传输助手` before running broader sends.
- Use small `--max-count` values first when collecting chat history.
- Use `modify-announcement` only when the operator is likely a group admin.
- When passing file paths or markdown paths, use absolute Windows paths.

## Extension Rules

- Add new automation code under `scripts/vendor/wx4py/` or `scripts/vendor/wechat_rpa/` only when the vendored runtime itself must change.
- Keep `scripts/run_wechat_skill.py` as the stable facade for agents.
- Add new wrapper commands by extending the parser and the action dispatcher, then document them in `references/cli-contract.md`.
- Put task-specific examples in `references/examples/` instead of bloating this file.
- Preserve JSON output stability: include `ok`, `action`, and either `result` or `error_type` plus `error`.

## Compatibility

`scripts/run_wechat_uia.py` remains as a compatibility shim for the older history-export-only entrypoint. Prefer the unified wrapper for all new work.
