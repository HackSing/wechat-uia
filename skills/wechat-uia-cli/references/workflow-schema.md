# Workflow Schema

Use workflow files with:

```bash
python scripts/run_wechat_skill.py run-workflow --workflow path\to\workflow.json
```

## Shape

```json
{
  "name": "send-and-check",
  "steps": [
    {
      "action": "send_to",
      "target": "文件传输助手",
      "target_type": "contact",
      "message": "workflow test"
    },
    {
      "action": "get_chat_history",
      "target": "文件传输助手",
      "target_type": "contact",
      "since": "today",
      "max_count": 10
    }
  ]
}
```

## Supported `action` Values

- `snapshot`
- `inspect`
- `search`
- `open_chat`
- `send_message`
- `send_to`
- `batch_send`
- `send_file`
- `send_file_to`
- `get_chat_history`
- `get_group_members`
- `set_group_nickname`
- `set_do_not_disturb`
- `set_pin_chat`
- `modify_announcement`
- `set_announcement_from_markdown`

Use underscore action names inside workflows even when the top-level CLI command uses hyphens.

## Rules

- `workflow.steps` must be a JSON array.
- Each step must be a JSON object with an `action` field.
- The runner stops on the first failed step.
- `export-history` and `desktop-export` are top-level commands, not workflow steps.
- Use absolute Windows paths for `file` and `markdown_file`.
