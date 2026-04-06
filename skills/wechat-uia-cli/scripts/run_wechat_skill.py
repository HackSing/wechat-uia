from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from runtime_bootstrap import ensure_runtime


SKILL_DIR = Path(__file__).resolve().parents[1]
VENDOR_DIR = SKILL_DIR / "scripts" / "vendor"


def _ensure_vendor_path() -> None:
    vendor = str(VENDOR_DIR)
    if vendor not in sys.path:
        sys.path.insert(0, vendor)


def _rect_to_dict(rect: Any) -> dict[str, int] | None:
    if not rect:
        return None
    try:
        return {
            "left": int(rect.left),
            "top": int(rect.top),
            "right": int(rect.right),
            "bottom": int(rect.bottom),
            "width": int(rect.right - rect.left),
            "height": int(rect.bottom - rect.top),
        }
    except Exception:
        return None


def _serialize_control(ctrl: Any, include_children: bool = False, depth: int = 0, max_depth: int = 0) -> dict[str, Any]:
    payload = {
        "name": getattr(ctrl, "Name", "") or "",
        "class_name": getattr(ctrl, "ClassName", "") or "",
        "automation_id": getattr(ctrl, "AutomationId", "") or "",
        "control_type": getattr(ctrl, "ControlTypeName", "") or "",
        "rect": _rect_to_dict(getattr(ctrl, "BoundingRectangle", None)),
    }
    if include_children and depth < max_depth:
        children = []
        try:
            for child in ctrl.GetChildren():
                children.append(
                    _serialize_control(
                        child,
                        include_children=True,
                        depth=depth + 1,
                        max_depth=max_depth,
                    )
                )
        except Exception:
            children = []
        payload["children"] = children
    return payload


def _safe_exists(ctrl: Any, timeout: float = 0.5) -> bool:
    if not ctrl:
        return False
    try:
        return bool(ctrl.Exists(maxSearchSeconds=timeout))
    except Exception:
        return False


def _search_results_to_dict(results: dict[str, list[Any]]) -> dict[str, list[dict[str, Any]]]:
    serialized: dict[str, list[dict[str, Any]]] = {}
    for group, items in results.items():
        serialized[group] = [
            {
                "name": item.name,
                "item_type": item.item_type,
                "auto_id": item.auto_id,
                "group": item.group,
            }
            for item in items
        ]
    return serialized


def _summarize_history(messages: list[dict[str, Any]]) -> dict[str, Any]:
    type_breakdown: dict[str, int] = {}
    for message in messages:
        msg_type = str(message.get("type", "unknown"))
        type_breakdown[msg_type] = type_breakdown.get(msg_type, 0) + 1
    return {
        "message_count": len(messages),
        "type_breakdown": type_breakdown,
        "first_message_time": messages[0].get("time", "") if messages else "",
        "last_message_time": messages[-1].get("time", "") if messages else "",
        "sample_messages": messages[:5],
    }


def _emit(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok") else 1


def _load_client_class():
    _ensure_vendor_path()
    from wx4py.client import WeChatClient

    return WeChatClient


def _guess_page(client: Any) -> str:
    root = client.window.uia.root
    try:
        if _safe_exists(root.GroupControl(ClassName="mmui::ChatRoomMemberInfoView"), timeout=0.2):
            return "group_detail"
    except Exception:
        pass
    try:
        if _safe_exists(root.EditControl(AutomationId="chat_input_field"), timeout=0.2):
            return "chat"
    except Exception:
        pass
    try:
        if _safe_exists(root.WindowControl(ClassName="mmui::SearchContentPopover"), timeout=0.2):
            return "search"
    except Exception:
        pass
    return "unknown"


def _get_focus_snapshot() -> dict[str, Any] | None:
    _ensure_vendor_path()
    try:
        from wx4py.core.uiautomation import GetFocusedControl

        focused = GetFocusedControl()
    except Exception:
        return None
    if not focused:
        return None
    return _serialize_control(focused)


def _build_snapshot(client: Any) -> dict[str, Any]:
    root = client.window.uia.root
    top_level_controls = []
    try:
        for child in root.GetChildren():
            top_level_controls.append(_serialize_control(child))
    except Exception:
        top_level_controls = []
    return {
        "connected": client.is_connected,
        "window": {
            "title": client.window.title,
            "class_name": client.window.class_name,
            "hwnd": client.window.hwnd,
        },
        "state": {
            "page": _guess_page(client),
            "focused_control": _get_focus_snapshot(),
            "chat_input_ready": _safe_exists(root.EditControl(AutomationId="chat_input_field"), timeout=0.2),
            "search_popup_visible": _safe_exists(root.WindowControl(ClassName="mmui::SearchContentPopover"), timeout=0.2),
        },
        "top_level_controls": top_level_controls,
    }


def _cmd_check_env() -> int:
    _ensure_vendor_path()
    bootstrap = ensure_runtime(auto_install=True)
    modules = ["wx4py", "wechat_rpa"]
    local_checks = []
    missing_local = []
    for module_name in modules:
        try:
            module = importlib.import_module(module_name)
            local_checks.append({"module": module_name, "ok": True, "path": getattr(module, "__file__", "built-in")})
        except Exception as exc:
            local_checks.append(
                {
                    "module": module_name,
                    "ok": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            missing_local.append(module_name)
    payload = {
        "ok": bootstrap["ok"] and not missing_local,
        "action": "check-env",
        "python": sys.executable,
        "cwd": os.getcwd(),
        "vendor_dir": str(VENDOR_DIR),
        "runtime_bootstrap": bootstrap,
        "checks": local_checks,
    }
    if missing_local:
        payload["missing_modules"] = missing_local
    return _emit(payload)


def _run_client_action(client: Any, action: str, params: dict[str, Any]) -> dict[str, Any]:
    if action == "snapshot":
        return {"ok": True, "action": action, "result": _build_snapshot(client)}

    if action == "inspect":
        return {
            "ok": True,
            "action": action,
            "result": _serialize_control(client.window.uia.root, include_children=True, max_depth=int(params.get("max_depth", 2))),
        }

    if action == "search":
        keyword = str(params["keyword"])
        return {
            "ok": True,
            "action": action,
            "args": {"keyword": keyword},
            "result": _search_results_to_dict(client.chat_window.search(keyword)),
        }

    if action == "open_chat":
        target = str(params["target"])
        target_type = str(params.get("target_type", "contact"))
        ok = client.chat_window.open_chat(target, target_type=target_type)
        return {
            "ok": ok,
            "action": action,
            "args": {"target": target, "target_type": target_type},
            "result": _build_snapshot(client) if ok else {"opened": False},
        }

    if action == "send_message":
        message = str(params["message"])
        ok = client.chat_window.send_message(message)
        return {"ok": ok, "action": action, "args": {"message": message}, "result": {"sent": ok}}

    if action == "send_to":
        target = str(params["target"])
        target_type = str(params.get("target_type", "contact"))
        message = str(params["message"])
        ok = client.chat_window.send_to(target, message, target_type=target_type)
        return {
            "ok": ok,
            "action": action,
            "args": {"target": target, "target_type": target_type, "message": message},
            "result": {"target": target, "target_type": target_type, "sent": ok},
        }

    if action == "batch_send":
        targets = list(params["targets"])
        target_type = str(params.get("target_type", "group"))
        message = str(params["message"])
        results = client.chat_window.batch_send(targets, message, target_type=target_type)
        success_count = sum(1 for value in results.values() if value)
        return {
            "ok": success_count == len(targets),
            "action": action,
            "args": {"targets": targets, "target_type": target_type, "message": message},
            "result": {
                "success_count": success_count,
                "failure_count": len(targets) - success_count,
                "per_target": results,
            },
        }

    if action == "send_file":
        file_paths = list(params["file"])
        message = params.get("message")
        ok = client.chat_window.send_file(file_paths if len(file_paths) > 1 else file_paths[0], message=message)
        return {"ok": ok, "action": action, "args": {"file": file_paths, "message": message}, "result": {"file_count": len(file_paths), "sent": ok}}

    if action == "send_file_to":
        target = str(params["target"])
        target_type = str(params.get("target_type", "contact"))
        file_paths = list(params["file"])
        message = params.get("message")
        ok = client.chat_window.send_file_to(target, file_paths if len(file_paths) > 1 else file_paths[0], target_type=target_type, message=message)
        return {
            "ok": ok,
            "action": action,
            "args": {"target": target, "target_type": target_type, "file": file_paths, "message": message},
            "result": {"target": target, "target_type": target_type, "file_count": len(file_paths), "sent": ok},
        }

    if action == "get_chat_history":
        target = str(params["target"])
        target_type = str(params.get("target_type", "contact"))
        since = str(params.get("since", "today"))
        max_count = int(params.get("max_count", 500))
        messages = client.chat_window.get_chat_history(target, target_type=target_type, since=since, max_count=max_count)
        return {
            "ok": True,
            "action": action,
            "args": {"target": target, "target_type": target_type, "since": since, "max_count": max_count},
            "result": {"messages": messages, "summary": _summarize_history(messages)},
        }

    if action == "get_group_members":
        group_name = str(params["group"])
        members = client.group_manager.get_group_members(group_name)
        return {
            "ok": True,
            "action": action,
            "args": {"group": group_name},
            "result": {"group": group_name, "member_count": len(members), "members": members},
        }

    if action == "set_group_nickname":
        group_name = str(params["group"])
        nickname = str(params["nickname"])
        ok = client.group_manager.set_group_nickname(group_name, nickname)
        return {"ok": ok, "action": action, "args": {"group": group_name, "nickname": nickname}, "result": {"updated": ok}}

    if action == "set_do_not_disturb":
        group_name = str(params["group"])
        enable = bool(params["enable"])
        ok = client.group_manager.set_do_not_disturb(group_name, enable)
        return {"ok": ok, "action": action, "args": {"group": group_name, "enable": enable}, "result": {"updated": ok}}

    if action == "set_pin_chat":
        group_name = str(params["group"])
        enable = bool(params["enable"])
        ok = client.group_manager.set_pin_chat(group_name, enable)
        return {"ok": ok, "action": action, "args": {"group": group_name, "enable": enable}, "result": {"updated": ok}}

    if action == "modify_announcement":
        group_name = str(params["group"])
        content = str(params["content"])
        ok = client.group_manager.modify_announcement_simple(group_name, content)
        return {"ok": ok, "action": action, "args": {"group": group_name, "content": content}, "result": {"updated": ok}}

    if action == "set_announcement_from_markdown":
        group_name = str(params["group"])
        markdown_file = str(params["markdown_file"])
        ok = client.group_manager.set_announcement_from_markdown(group_name, markdown_file)
        return {"ok": ok, "action": action, "args": {"group": group_name, "markdown_file": markdown_file}, "result": {"updated": ok}}

    raise ValueError(f"unsupported action: {action}")


def _cmd_with_client(args: argparse.Namespace) -> int:
    WeChatClient = _load_client_class()
    try:
        with WeChatClient() as client:
            payload = _run_client_action(client, args.command.replace("-", "_"), vars(args))
    except Exception as exc:
        payload = {
            "ok": False,
            "action": args.command.replace("-", "_"),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    return _emit(payload)


def _cmd_export_history(args: argparse.Namespace) -> int:
    _ensure_vendor_path()
    from wechat_rpa.cli import _cmd_export_history as export_history

    return export_history(args)


def _cmd_desktop_export(args: argparse.Namespace) -> int:
    _ensure_vendor_path()
    from wechat_rpa.cli import _cmd_desktop_export as desktop_export

    return desktop_export(args)


def _cmd_daily_report_fetch(args: argparse.Namespace) -> int:
    """Fetch today's chat messages for a configured list of customers."""
    _ensure_vendor_path()
    from wx4py.pages.daily_report import (
        DailyReportFetcher,
        filter_customers,
        load_cache,
        load_customers_config,
        logs_to_json,
        save_cache,
    )

    action = "daily_report_fetch"
    config_path = Path(args.config).resolve()

    # Phase 1: load + validate config (fail fast before opening WeChat)
    try:
        customers, meta = load_customers_config(config_path)
    except Exception as exc:
        return _emit(
            {
                "ok": False,
                "action": action,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "config": str(config_path),
            }
        )

    # Phase 2: filter by --customer / --group / --tag
    try:
        selected = filter_customers(
            customers,
            meta,
            ids=args.customer or None,
            group=args.group,
            tags=args.tag or None,
        )
    except Exception as exc:
        return _emit(
            {
                "ok": False,
                "action": action,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "config": str(config_path),
            }
        )

    # Phase 3: resolve defaults from config + CLI overrides
    defaults = meta.get("defaults") or {}
    since = args.since or str(defaults.get("since") or "today")
    max_count = args.max_count if args.max_count is not None else int(defaults.get("max_count") or 300)

    today = date.today()
    cache_dir = Path(args.cache_dir).resolve() if args.cache_dir else (SKILL_DIR / ".cache" / "daily-report")
    cached = load_cache(cache_dir, today) if not args.no_cache else {}

    request_args = {
        "config": str(config_path),
        "since": since,
        "max_count": max_count,
        "group": args.group,
        "tag": list(args.tag) if args.tag else None,
        "customer": list(args.customer) if args.customer else None,
        "cache_dir": str(cache_dir),
        "no_cache": bool(args.no_cache),
        "stop_on_error": bool(args.stop_on_error),
        "skip_empty": bool(args.skip_empty),
    }

    if not selected:
        return _emit(
            {
                "ok": True,
                "action": action,
                "args": request_args,
                "result": {
                    "report_date": today.isoformat(),
                    "generated_at": datetime.now().isoformat(timespec="seconds"),
                    "customer_count": 0,
                    "success_count": 0,
                    "empty_count": 0,
                    "failure_count": 0,
                    "from_cache": False,
                    "cache_file": None,
                    "customers": [],
                    "message": "no customers matched the given filters",
                },
            }
        )

    # Phase 4: run fetch under a WeChatClient session
    WeChatClient = _load_client_class()
    try:
        with WeChatClient() as client:
            fetcher = DailyReportFetcher(client)
            logs = fetcher.fetch_all(
                selected,
                since=since,
                max_count=max_count,
                stop_on_error=args.stop_on_error,
                cache=cached,
                use_cache=not args.no_cache,
            )
    except Exception as exc:
        return _emit(
            {
                "ok": False,
                "action": action,
                "args": request_args,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )

    # Phase 5: persist cache (merge with pre-existing day cache)
    cache_file_str: str | None = None
    try:
        cache_file = save_cache(cache_dir, today, logs, existing=cached)
        cache_file_str = str(cache_file)
    except Exception as exc:
        print(
            f"warning: failed to save daily-report cache: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

    # Phase 6: summarize + emit
    success_count = sum(1 for log in logs if log.status == "ok")
    empty_count = sum(1 for log in logs if log.status == "empty")
    failure_count = sum(1 for log in logs if log.status in ("not_found", "error"))
    from_cache_all = bool(logs) and all(log.from_cache for log in logs)

    output_logs = logs
    if args.skip_empty:
        output_logs = [log for log in logs if log.status != "empty"]

    return _emit(
        {
            "ok": True,
            "action": action,
            "args": request_args,
            "result": {
                "report_date": today.isoformat(),
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "customer_count": len(logs),
                "success_count": success_count,
                "empty_count": empty_count,
                "failure_count": failure_count,
                "from_cache": from_cache_all,
                "cache_file": cache_file_str,
                "customers": logs_to_json(output_logs),
            },
        }
    )


def _cmd_run_workflow(args: argparse.Namespace) -> int:
    workflow_path = Path(args.workflow).resolve()
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    if not isinstance(workflow, dict):
        return _emit({"ok": False, "action": "run-workflow", "error_type": "ValueError", "error": "workflow root must be an object"})
    steps = workflow.get("steps")
    if not isinstance(steps, list):
        return _emit({"ok": False, "action": "run-workflow", "error_type": "ValueError", "error": "workflow.steps must be a list"})

    WeChatClient = _load_client_class()
    results = []
    try:
        with WeChatClient() as client:
            for index, step in enumerate(steps, start=1):
                if not isinstance(step, dict):
                    raise ValueError(f"workflow step #{index} must be an object")
                action = str(step.get("action", "")).strip()
                if not action:
                    raise ValueError(f"workflow step #{index} missing action")
                params = dict(step)
                params.pop("action", None)
                step_result = _run_client_action(client, action, params)
                step_result["step"] = index
                results.append(step_result)
                if not step_result.get("ok"):
                    break
    except Exception as exc:
        return _emit({"ok": False, "action": "run-workflow", "workflow": str(workflow_path), "error_type": type(exc).__name__, "error": str(exc), "results": results})

    return _emit(
        {
            "ok": all(item.get("ok") for item in results),
            "action": "run-workflow",
            "workflow": {"name": workflow.get("name", workflow_path.name), "path": str(workflow_path), "step_count": len(steps)},
            "results": results,
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run_wechat_skill", description="Self-contained WeChat automation wrapper for the wechat-uia-cli skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check-env", help="Validate Python/runtime dependencies")
    subparsers.add_parser("snapshot", help="Dump a compact runtime snapshot")

    inspect_parser = subparsers.add_parser("inspect", help="Dump the visible UIA control tree")
    inspect_parser.add_argument("--max-depth", type=int, default=2)

    search_parser = subparsers.add_parser("search", help="Search contacts or groups")
    search_parser.add_argument("--keyword", required=True)

    open_chat_parser = subparsers.add_parser("open-chat", help="Open a chat by name")
    open_chat_parser.add_argument("--target", required=True)
    open_chat_parser.add_argument("--target-type", choices=["contact", "group"], default="contact")

    send_message_parser = subparsers.add_parser("send-message", help="Send a message in the current chat")
    send_message_parser.add_argument("--message", required=True)

    send_to_parser = subparsers.add_parser("send-to", help="Open a chat and send a message")
    send_to_parser.add_argument("--target", required=True)
    send_to_parser.add_argument("--target-type", choices=["contact", "group"], default="contact")
    send_to_parser.add_argument("--message", required=True)

    batch_send_parser = subparsers.add_parser("batch-send", help="Send the same message to multiple targets")
    batch_send_parser.add_argument("--targets", nargs="+", required=True)
    batch_send_parser.add_argument("--target-type", choices=["contact", "group"], default="group")
    batch_send_parser.add_argument("--message", required=True)

    send_file_parser = subparsers.add_parser("send-file", help="Send one or more files in the current chat")
    send_file_parser.add_argument("--file", nargs="+", required=True)
    send_file_parser.add_argument("--message")

    send_file_to_parser = subparsers.add_parser("send-file-to", help="Open a chat and send one or more files")
    send_file_to_parser.add_argument("--target", required=True)
    send_file_to_parser.add_argument("--target-type", choices=["contact", "group"], default="contact")
    send_file_to_parser.add_argument("--file", nargs="+", required=True)
    send_file_to_parser.add_argument("--message")

    history_parser = subparsers.add_parser("get-chat-history", help="Collect chat history directly via UIA")
    history_parser.add_argument("--target", required=True)
    history_parser.add_argument("--target-type", choices=["contact", "group"], default="contact")
    history_parser.add_argument("--since", choices=["today", "yesterday", "week", "all"], default="today")
    history_parser.add_argument("--max-count", type=int, default=500)

    export_parser = subparsers.add_parser("export-history", help="Export chat history to JSON/CSV/summary files")
    export_parser.add_argument("--target", required=True)
    export_parser.add_argument("--target-type", choices=["contact", "group"], default="contact")
    export_parser.add_argument("--since", choices=["today", "yesterday", "week", "all"], default="today")
    export_parser.add_argument("--max-count", type=int, default=500)
    export_parser.add_argument("--output-dir")
    export_parser.add_argument("--json-only", action="store_true")
    export_parser.add_argument("--summary-only", action="store_true")

    desktop_export_parser = subparsers.add_parser("desktop-export", help="Drive the export-chat-history desktop dialog")
    desktop_export_parser.add_argument("--targets", nargs="+", required=True)
    desktop_export_parser.add_argument("--time-range-label", default="三个月内")
    desktop_export_parser.add_argument("--content-scope-label", default="部分聊天记录")
    desktop_export_parser.add_argument("--max-scrolls", type=int, default=25)
    desktop_export_parser.add_argument("--step-delay", type=float, default=0.8)

    group_members_parser = subparsers.add_parser("get-group-members", help="List group members")
    group_members_parser.add_argument("--group", required=True)

    nickname_parser = subparsers.add_parser("set-group-nickname", help="Set your nickname in a group")
    nickname_parser.add_argument("--group", required=True)
    nickname_parser.add_argument("--nickname", required=True)

    dnd_parser = subparsers.add_parser("set-do-not-disturb", help="Toggle Do Not Disturb for a group")
    dnd_parser.add_argument("--group", required=True)
    dnd_state = dnd_parser.add_mutually_exclusive_group(required=True)
    dnd_state.add_argument("--enable", action="store_true")
    dnd_state.add_argument("--disable", action="store_true")

    pin_parser = subparsers.add_parser("set-pin-chat", help="Toggle pin chat for a group")
    pin_parser.add_argument("--group", required=True)
    pin_state = pin_parser.add_mutually_exclusive_group(required=True)
    pin_state.add_argument("--enable", action="store_true")
    pin_state.add_argument("--disable", action="store_true")

    announcement_parser = subparsers.add_parser("modify-announcement", help="Set plain-text group announcement")
    announcement_parser.add_argument("--group", required=True)
    announcement_parser.add_argument("--content", required=True)

    markdown_parser = subparsers.add_parser("set-announcement-from-markdown", help="Set a formatted group announcement from a markdown file")
    markdown_parser.add_argument("--group", required=True)
    markdown_parser.add_argument("--markdown-file", required=True)

    workflow_parser = subparsers.add_parser("run-workflow", help="Run a JSON workflow using the unified wrapper actions")
    workflow_parser.add_argument("--workflow", required=True)

    daily_report_parser = subparsers.add_parser(
        "daily-report-fetch",
        help="Batch-fetch daily chat messages for a configured list of customers",
    )
    daily_report_parser.add_argument(
        "--config",
        required=True,
        help="Path to customers.yaml or customers.json",
    )
    daily_report_parser.add_argument(
        "--since",
        choices=["today", "yesterday", "week", "all"],
        help="Override defaults.since from the config (default: today)",
    )
    daily_report_parser.add_argument(
        "--max-count",
        type=int,
        help="Override defaults.max_count from the config (default: 300)",
    )
    daily_report_parser.add_argument(
        "--group",
        help="Filter by a named group declared under config.groups",
    )
    daily_report_parser.add_argument(
        "--tag",
        action="append",
        help="Filter by tag (may be repeated to match any of several tags)",
    )
    daily_report_parser.add_argument(
        "--customer",
        action="append",
        help="Fetch only the given customer id (may be repeated); overrides --group/--tag",
    )
    daily_report_parser.add_argument(
        "--cache-dir",
        help="Override cache directory (default: <skill>/.cache/daily-report)",
    )
    daily_report_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignore any existing day cache and re-fetch every customer",
    )
    daily_report_parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Abort the batch on the first customer that ends in 'error' status",
    )
    daily_report_parser.add_argument(
        "--skip-empty",
        action="store_true",
        help="Omit customers whose status is 'empty' from the output JSON",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if hasattr(args, "disable") and getattr(args, "disable"):
        setattr(args, "enable", False)

    if args.command != "check-env":
        bootstrap = ensure_runtime(auto_install=True)
        if not bootstrap["ok"]:
            return _emit(
                {
                    "ok": False,
                    "action": args.command,
                    "error_type": "RuntimeDependencyError",
                    "error": "failed to install required Python packages",
                    "runtime_bootstrap": bootstrap,
                }
            )

    if args.command == "check-env":
        return _cmd_check_env()
    if args.command == "export-history":
        return _cmd_export_history(args)
    if args.command == "desktop-export":
        return _cmd_desktop_export(args)
    if args.command == "run-workflow":
        return _cmd_run_workflow(args)
    if args.command == "daily-report-fetch":
        return _cmd_daily_report_fetch(args)
    return _cmd_with_client(args)


if __name__ == "__main__":
    raise SystemExit(main())
