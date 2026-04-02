# -*- coding: utf-8 -*-
"""Command-line interface for wx4py."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .._version import __version__

if TYPE_CHECKING:
    from ..client import WeChatClient


def _rect_to_dict(rect: Any) -> dict[str, int] | None:
    """Serialize a UIA rectangle if available."""
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
    """Serialize a UI Automation control into JSON-friendly data."""
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
    """Best-effort control existence check."""
    if not ctrl:
        return False

    try:
        return bool(ctrl.Exists(maxSearchSeconds=timeout))
    except Exception:
        return False


def _guess_page(client: "WeChatClient") -> str:
    """Infer the current high-level page from visible controls."""
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
    """Capture the current focused control."""
    try:
        from ..core.uiautomation import GetFocusedControl

        focused = GetFocusedControl()
    except Exception:
        return None

    if not focused:
        return None

    return _serialize_control(focused)


def _build_snapshot(client: "WeChatClient") -> dict[str, Any]:
    """Build a compact runtime snapshot."""
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


def _search_results_to_dict(results: dict[str, list[Any]]) -> dict[str, list[dict[str, Any]]]:
    """Serialize search results."""
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


def _emit(payload: dict[str, Any]) -> None:
    """Print one JSON payload."""
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _load_workflow(path: str) -> dict[str, Any]:
    """Load JSON workflow definition."""
    workflow_path = Path(path)
    content = workflow_path.read_text(encoding="utf-8")

    if workflow_path.suffix.lower() == ".json":
        data = json.loads(content)
    else:
        raise ValueError("workflow file must be .json in this first CLI version")

    if not isinstance(data, dict):
        raise ValueError("workflow root must be an object")
    if not isinstance(data.get("steps"), list):
        raise ValueError("workflow.steps must be a list")

    return data


def _run_action(client: "WeChatClient", action: str, args: argparse.Namespace | dict[str, Any]) -> dict[str, Any]:
    """Dispatch one action."""
    if isinstance(args, argparse.Namespace):
        params = vars(args)
    else:
        params = args

    if action == "inspect":
        max_depth = int(params["max_depth"])
        return {
            "ok": True,
            "action": action,
            "result": _serialize_control(
                client.window.uia.root,
                include_children=True,
                max_depth=max_depth,
            ),
        }

    if action == "snapshot":
        return {
            "ok": True,
            "action": action,
            "result": _build_snapshot(client),
        }

    if action == "search":
        keyword = str(params["keyword"])
        results = client.chat_window.search(keyword)
        return {
            "ok": True,
            "action": action,
            "args": {
                "keyword": keyword,
            },
            "result": _search_results_to_dict(results),
        }

    if action == "open_chat":
        target = str(params["target"])
        target_type = str(params.get("target_type", "contact"))
        ok = client.chat_window.open_chat(target, target_type=target_type)
        return {
            "ok": ok,
            "action": action,
            "args": {
                "target": target,
                "target_type": target_type,
            },
            "result": _build_snapshot(client),
        }

    if action == "send_message":
        message = str(params["message"])
        ok = client.chat_window.send_message(message)
        return {
            "ok": ok,
            "action": action,
            "args": {
                "message": message,
            },
            "result": _build_snapshot(client),
        }

    if action == "send_to":
        target = str(params["target"])
        message = str(params["message"])
        target_type = str(params.get("target_type", "contact"))
        ok = client.chat_window.send_to(target, message, target_type=target_type)
        return {
            "ok": ok,
            "action": action,
            "args": {
                "target": target,
                "target_type": target_type,
                "message": message,
            },
            "result": _build_snapshot(client),
        }

    raise ValueError(f"unsupported action: {action}")


def _cmd_run_workflow(client: "WeChatClient", path: str) -> dict[str, Any]:
    """Execute workflow steps sequentially."""
    workflow = _load_workflow(path)
    results = []

    for index, step in enumerate(workflow["steps"], start=1):
        if not isinstance(step, dict):
            raise ValueError(f"workflow step #{index} must be an object")

        action = step.get("action")
        if not action:
            raise ValueError(f"workflow step #{index} missing action")

        step_result = _run_action(client, str(action), step)
        step_result["step"] = index
        results.append(step_result)

        if not step_result["ok"]:
            break

    return {
        "ok": all(item["ok"] for item in results),
        "action": "run_workflow",
        "workflow": {
            "name": workflow.get("name", Path(path).name),
            "path": str(Path(path).resolve()),
            "step_count": len(workflow["steps"]),
        },
        "results": results,
    }


def _build_parser() -> argparse.ArgumentParser:
    """Build top-level parser."""
    parser = argparse.ArgumentParser(prog="wx4py", description="CLI for wx4py desktop automation")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Dump the visible UIA control tree")
    inspect_parser.add_argument("--max-depth", type=int, default=2, help="Maximum child depth to include")

    subparsers.add_parser("snapshot", help="Dump a compact runtime snapshot")

    search_parser = subparsers.add_parser("search", help="Search WeChat contacts/groups")
    search_parser.add_argument("--keyword", required=True, help="Search keyword")

    exec_parser = subparsers.add_parser("exec", help="Run a single action")
    exec_subparsers = exec_parser.add_subparsers(dest="exec_action", required=True)

    open_chat_parser = exec_subparsers.add_parser("open_chat", help="Open a chat by name")
    open_chat_parser.add_argument("--target", required=True, help="Contact or group name")
    open_chat_parser.add_argument("--target-type", choices=["contact", "group"], default="contact")

    send_message_parser = exec_subparsers.add_parser("send_message", help="Send a message to the current chat")
    send_message_parser.add_argument("--message", required=True, help="Message to send")

    send_to_parser = exec_subparsers.add_parser("send_to", help="Open a chat and send a message")
    send_to_parser.add_argument("--target", required=True, help="Contact or group name")
    send_to_parser.add_argument("--target-type", choices=["contact", "group"], default="contact")
    send_to_parser.add_argument("--message", required=True, help="Message to send")

    run_parser = subparsers.add_parser("run", help="Run a workflow definition")
    run_parser.add_argument("--workflow", required=True, help="Path to a JSON workflow file")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    known_error_types = (OSError, ValueError)

    try:
        from ..client import WeChatClient
        from ..core.exceptions import WeChatError
        known_error_types = known_error_types + (WeChatError,)

        with WeChatClient() as client:
            if args.command == "inspect":
                payload = _run_action(client, "inspect", args)
            elif args.command == "snapshot":
                payload = _run_action(client, "snapshot", args)
            elif args.command == "search":
                payload = _run_action(client, "search", args)
            elif args.command == "exec":
                payload = _run_action(client, args.exec_action, args)
            elif args.command == "run":
                payload = _cmd_run_workflow(client, args.workflow)
            else:
                raise ValueError(f"unknown command: {args.command}")
    except known_error_types as exc:
        _emit(
            {
                "ok": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )
        return 1
    except ModuleNotFoundError as exc:
        _emit(
            {
                "ok": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )
        return 1

    _emit(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
