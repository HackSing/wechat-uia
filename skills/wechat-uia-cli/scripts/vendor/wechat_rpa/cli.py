"""CLI for exporting and analyzing WeChat chat history."""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from .desktop_export import DesktopExportFlow


def _load_wechat_client():
    """Load WeChatClient from installed wx4py or local repo source."""
    try:
        from wx4py import WeChatClient  # type: ignore

        return WeChatClient
    except ModuleNotFoundError:
        repo_root = Path(__file__).resolve().parents[2]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        from src import WeChatClient  # type: ignore

        return WeChatClient


def _ensure_output_dir(path: str | None, target: str) -> Path:
    """Resolve and create output directory."""
    if path:
        output_dir = Path(path)
    else:
        safe_target = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in target).strip("_")
        safe_target = safe_target or "chat_history"
        output_dir = Path.cwd() / "output" / safe_target

    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir.resolve()


def _build_summary(messages: list[dict[str, Any]], target: str, target_type: str, since: str, max_count: int) -> dict[str, Any]:
    """Build a compact analysis summary."""
    type_counter = Counter(message.get("type", "unknown") for message in messages)
    time_counter = Counter(message.get("time", "") for message in messages if message.get("time"))
    message_lengths = [len(str(message.get("content", ""))) for message in messages]

    return {
        "target": target,
        "target_type": target_type,
        "since": since,
        "max_count": max_count,
        "message_count": len(messages),
        "type_breakdown": dict(type_counter),
        "time_breakdown": dict(time_counter),
        "avg_message_length": round(sum(message_lengths) / len(message_lengths), 2) if message_lengths else 0,
        "first_message_time": messages[0].get("time") if messages else "",
        "last_message_time": messages[-1].get("time") if messages else "",
        "sample_messages": messages[:5],
    }


def _write_json(path: Path, payload: Any) -> None:
    """Write JSON file."""
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, messages: list[dict[str, Any]]) -> None:
    """Write CSV export."""
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["time", "type", "content"])
        writer.writeheader()
        for message in messages:
            writer.writerow(
                {
                    "time": message.get("time", ""),
                    "type": message.get("type", ""),
                    "content": message.get("content", ""),
                }
            )


def _emit(payload: dict[str, Any]) -> int:
    """Emit JSON result to stdout."""
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok") else 1


def _cmd_export_history(args: argparse.Namespace) -> int:
    """Export and analyze chat history."""
    try:
        WeChatClient = _load_wechat_client()
        output_dir = _ensure_output_dir(args.output_dir, args.target)

        with WeChatClient() as wx:
            messages = wx.chat_window.get_chat_history(
                args.target,
                target_type=args.target_type,
                since=args.since,
                max_count=args.max_count,
            )
            messages = messages[: args.max_count]

        summary = _build_summary(
            messages,
            target=args.target,
            target_type=args.target_type,
            since=args.since,
            max_count=args.max_count,
        )

        written_files: list[str] = []
        if not args.summary_only:
            json_path = output_dir / "messages.json"
            _write_json(json_path, messages)
            written_files.append(str(json_path))

        if not args.summary_only and not args.json_only:
            csv_path = output_dir / "messages.csv"
            _write_csv(csv_path, messages)
            written_files.append(str(csv_path))

        summary_path = output_dir / "summary.json"
        _write_json(summary_path, summary)
        written_files.append(str(summary_path))

        return _emit(
            {
                "ok": True,
                "action": "export-history",
                "target": args.target,
                "target_type": args.target_type,
                "since": args.since,
                "output_dir": str(output_dir),
                "written_files": written_files,
                "summary": summary,
            }
        )
    except Exception as exc:
        return _emit(
            {
                "ok": False,
                "action": "export-history",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )


def _cmd_desktop_export(args: argparse.Namespace) -> int:
    """Run the dedicated desktop export flow."""
    try:
        WeChatClient = _load_wechat_client()

        with WeChatClient() as wx:
            flow = DesktopExportFlow(wx)
            result = flow.run(
                targets=args.targets,
                time_range_label=args.time_range_label,
                content_scope_label=args.content_scope_label,
                max_scrolls=args.max_scrolls,
                step_delay=args.step_delay,
            )

        return _emit(
            {
                "ok": result["ok"],
                "action": "desktop-export",
                "targets": args.targets,
                "time_range_label": args.time_range_label,
                "content_scope_label": args.content_scope_label,
                "steps": result["steps"],
            }
        )
    except Exception as exc:
        return _emit(
            {
                "ok": False,
                "action": "desktop-export",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )


def _build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(prog="wechat-rpa", description="WeChat chat history export CLI")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export-history", help="Export and analyze chat history")
    export_parser.add_argument("--target", required=True, help="Contact or group name")
    export_parser.add_argument("--target-type", choices=["contact", "group"], default="contact")
    export_parser.add_argument("--since", choices=["today", "yesterday", "week", "all"], default="today")
    export_parser.add_argument("--max-count", type=int, default=500)
    export_parser.add_argument("--output-dir", help="Directory to write output files")
    export_parser.add_argument("--json-only", action="store_true", help="Only write messages.json and summary.json")
    export_parser.add_argument("--summary-only", action="store_true", help="Only write summary.json")

    desktop_export_parser = subparsers.add_parser("desktop-export", help="Run the dedicated WeChat desktop export flow")
    desktop_export_parser.add_argument("--targets", nargs="+", required=True, help="Contact/group names to select in export dialog")
    desktop_export_parser.add_argument("--time-range-label", default="三个月内", help="Visible option text for time range")
    desktop_export_parser.add_argument("--content-scope-label", default="部分聊天记录", help="Visible option text for content scope")
    desktop_export_parser.add_argument("--max-scrolls", type=int, default=25, help="Maximum scroll iterations while searching targets")
    desktop_export_parser.add_argument("--step-delay", type=float, default=0.8, help="Delay between desktop flow actions")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entrypoint."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.command == "export-history":
        return _cmd_export_history(args)
    if args.command == "desktop-export":
        return _cmd_desktop_export(args)

    return _emit(
        {
            "ok": False,
            "error_type": "ValueError",
            "error": f"unknown command: {args.command}",
        }
    )


if __name__ == "__main__":
    raise SystemExit(main())
