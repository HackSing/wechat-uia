# Roadmap

## Current Status

- Completed: add a self-contained `skills/wechat-uia-cli` skill that vendors `wx4py` and `wechat_rpa` runtime code under `scripts/vendor/`.
- Completed: add a unified wrapper at `skills/wechat-uia-cli/scripts/run_wechat_skill.py`.
- Completed: add first-use runtime bootstrap to auto-install missing Python dependencies with `python -m pip install`.
- Completed: add human-facing usage documentation at `skills/wechat-uia-cli/README.md`.

## Smoke Test Notes

Smoke test date: 2026-04-02

- Verified: `D:\Project\wx4py` can be removed and the skill still loads `wx4py` and `wechat_rpa` from the vendored runtime.
- Verified: `check-env` succeeds without the external source repo.
- Verified: direct current-chat send via `send-message` succeeds after the external source repo is removed.
- Observed issue: target-based search/open flows are not stable in the current WeChat UI session.
- Observed issue: `send-to --target "文件传输助手"` failed with `Search popup not found` / target not found.
- Observed issue: `export-history --target "文件传输助手"` failed because the chat could not be reopened through search.
- Diagnostic note: `search --keyword "文件传输助手"` can still return results, and WeChat currently groups it under `功能` rather than a normal contact result.

## Next Work

- Fix the search/open-chat flow so it handles transient missing search popups more reliably.
- Improve target resolution for entries that appear under `功能`, including `文件传输助手`.
- Add a fallback open-chat strategy that can recover from an already-open search popup or other UI state drift.
- Re-run smoke tests for:
  - `send-to --target "文件传输助手"`
  - `export-history --target "文件传输助手"`
  - `get-chat-history --target "文件传输助手"`
- Consider persisting a lightweight diagnostic trace when search/open-chat fails so later debugging is faster.
