from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from wx4py.pages.daily_report import CustomerConfig, CustomerDailyLog


DEFAULT_HISTORY_DAYS = 14
DEFAULT_ISSUE_RETENTION_DAYS = 14
GENERIC_PROJECT_TITLE = "当前商机"
CHIP_REGEX = re.compile(r"\b[A-Z]{1,5}\d{2,4}[A-Z0-9_-]{0,8}\b")

SCHEDULE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"拜访",
        r"到的时候",
        r"到时",
        r"我来接你",
        r"见面",
        r"待会",
        r"方便吗",
        r"有时间",
        r"\d{1,2}点",
        r"\d{1,2}:\d{2}",
        r"下午",
        r"明天",
    )
]
ADDRESS_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"地址",
        r"路",
        r"号",
        r"栋",
        r"大厦",
        r"国际城",
        r"位置",
        r"楼",
    )
]
DEMAND_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"需求",
        r"咨询",
        r"方案",
        r"功能",
        r"智能体",
        r"开发",
        r"业务",
        r"demo",
        r"演示",
        r"产品",
        r"项目",
    )
]
BUSINESS_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"报价",
        r"预算",
        r"合同",
        r"付款",
        r"回款",
        r"发票",
        r"签约",
        r"合作",
        r"采购",
        r"代理商",
        r"客户",
    )
]
QUESTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"[?？]$",
        r"吗[?？]?$",
        r"呢[?？]?$",
        r"方便",
        r"什么时间",
        r"请给我",
        r"能不能",
        r"可不可以",
        r"是否",
        r"怎么",
        r"为什么",
        r"支持不支持",
    )
]
URGENT_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"紧急",
        r"着急",
        r"尽快",
        r"马上",
        r"今天前",
        r"今天就",
        r"明天前",
        r"本周内",
        r"赶紧",
        r"尽早",
        r"来不及",
    )
]
RISK_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"风险",
        r"不支持",
        r"不能",
        r"有问题",
        r"异常",
        r"失败",
        r"卡住",
        r"不稳定",
        r"丢包",
        r"bug",
        r"兼容",
        r"不合适",
    )
]
TECH_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"技术",
        r"调试",
        r"驱动",
        r"sdk",
        r"接口",
        r"协议",
        r"串口",
        r"wifi",
        r"蓝牙",
        r"ble",
        r"音频",
        r"视频",
        r"camera",
        r"codec",
        r"摄像头",
        r"麦克风",
        r"录音",
        r"解码",
        r"编码",
        r"功耗",
        r"兼容",
    )
]
SELECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"芯片",
        r"型号",
        r"选型",
        r"方案",
        r"支持不支持",
        r"能不能做",
    )
]
CLOSURE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"没问题",
        r"可以的",
        r"好的",
        r"搞定",
        r"解决",
        r"已处理",
        r"处理好了",
        r"ok",
    )
]
VAGUE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"看一下",
        r"咨询一下",
        r"大概",
        r"差不多",
        r"类似",
        r"比较冷门",
        r"先了解",
    )
]

CAPABILITY_PATTERNS = {
    "wifi": [re.compile(pattern, re.IGNORECASE) for pattern in (r"wifi", r"wi-fi", r"无线")],
    "ble": [re.compile(pattern, re.IGNORECASE) for pattern in (r"ble", r"蓝牙")],
    "audio_capture": [re.compile(pattern, re.IGNORECASE) for pattern in (r"麦克风", r"录音", r"采音", r"语音输入")],
    "audio_playback": [re.compile(pattern, re.IGNORECASE) for pattern in (r"喇叭", r"扬声器", r"播报", r"音频播放", r"语音播报")],
    "camera": [re.compile(pattern, re.IGNORECASE) for pattern in (r"camera", r"摄像头", r"图像", r"相机")],
    "video_encode": [re.compile(pattern, re.IGNORECASE) for pattern in (r"视频", r"编码", r"推流", r"h264", r"h265", r"AV视频")],
    "video_decode": [re.compile(pattern, re.IGNORECASE) for pattern in (r"解码", r"视频播放", r"rtsp")],
    "display": [re.compile(pattern, re.IGNORECASE) for pattern in (r"lcd", r"显示", r"屏幕", r"屏")],
    "ai": [re.compile(pattern, re.IGNORECASE) for pattern in (r"\bai\b", r"识别", r"推理", r"视觉", r"智能")],
    "ethernet": [re.compile(pattern, re.IGNORECASE) for pattern in (r"网口", r"以太网", r"ethernet")],
    "low_power": [re.compile(pattern, re.IGNORECASE) for pattern in (r"低功耗", r"电池", r"续航", r"待机")],
}

CAPABILITY_LABELS = {
    "wifi": "WiFi",
    "ble": "BLE",
    "audio_capture": "音频采集",
    "audio_playback": "音频播放",
    "camera": "摄像头输入",
    "video_encode": "视频编码",
    "video_decode": "视频解码",
    "display": "显示输出",
    "ai": "AI/视觉推理",
    "ethernet": "以太网",
    "low_power": "低功耗",
}

SCENARIO_TITLE_MAP = {
    "wifi_audio_video": "WiFi 音视频项目",
    "audio_terminal": "音频终端项目",
    "video_device": "视频设备项目",
    "edge_ai": "AI 视觉项目",
    "networked_device": "联网设备项目",
    "general_presales": GENERIC_PROJECT_TITLE,
}

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def resolve_knowledge_dir(knowledge_dir: Path | str | None = None) -> Path:
    if knowledge_dir is not None:
        return Path(knowledge_dir).resolve()
    return Path(__file__).resolve().parents[1] / "knowledge"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _message_summary(messages: list[dict[str, Any]]) -> dict[str, Any]:
    type_breakdown: dict[str, int] = {}
    time_breakdown: dict[str, int] = {}
    lengths: list[int] = []
    for message in messages:
        msg_type = str(message.get("type") or "unknown")
        type_breakdown[msg_type] = type_breakdown.get(msg_type, 0) + 1
        msg_time = str(message.get("time") or "").strip()
        if msg_time:
            time_breakdown[msg_time] = time_breakdown.get(msg_time, 0) + 1
        lengths.append(len(str(message.get("content") or "")))
    return {
        "message_count": len(messages),
        "type_breakdown": type_breakdown,
        "time_breakdown": time_breakdown,
        "avg_message_length": round(sum(lengths) / len(lengths), 2) if lengths else 0,
        "first_message_time": messages[0].get("time", "") if messages else "",
        "last_message_time": messages[-1].get("time", "") if messages else "",
    }


def _customer_metadata(customer: CustomerConfig) -> dict[str, Any]:
    return {
        "id": customer.id,
        "display_name": customer.display_name,
        "target": customer.target,
        "aliases": list(customer.aliases),
        "target_type": customer.target_type,
        "tags": list(customer.tags),
        "priority": customer.priority,
        "company": customer.company,
        "notes": customer.notes,
        "owner": customer.owner,
        "chip_focus": list(customer.chip_focus),
        "project_hints": list(customer.project_hints),
        "max_count": customer.max_count,
        "since": customer.since,
    }


def _trim_text(text: str, limit: int = 72) -> str:
    normalized = " ".join(str(text).split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _flatten_text(text: str) -> str:
    parts = [segment.strip() for segment in re.split(r"\r?\n+", str(text)) if segment.strip()]
    return " / ".join(parts) if parts else str(text).strip()


def _dedupe_preserve(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    replaced = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", lowered)
    collapsed = re.sub(r"-{2,}", "-", replaced).strip("-")
    return collapsed or "item"


def _entry_date(entry: dict[str, Any]) -> date | None:
    raw = entry.get("report_date")
    if not isinstance(raw, str):
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _flatten_messages(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for entry in entries:
        log = entry.get("log") or {}
        raw_messages = log.get("messages") or []
        if isinstance(raw_messages, list):
            messages.extend(message for message in raw_messages if isinstance(message, dict))
    return messages


def load_customer_entries(customer_dir: Path) -> list[dict[str, Any]]:
    daily_dir = customer_dir / "daily"
    if not daily_dir.exists():
        return []
    entries: list[dict[str, Any]] = []
    for path in sorted(daily_dir.glob("*.json")):
        data = _read_json(path)
        if data:
            entries.append(data)
    entries.sort(key=lambda item: item.get("report_date", ""))
    return entries


def _history_entries_for_window(entries: list[dict[str, Any]], report_date: date, history_days: int) -> list[dict[str, Any]]:
    start = report_date - timedelta(days=max(history_days, 1))
    result: list[dict[str, Any]] = []
    for entry in entries:
        entry_day = _entry_date(entry)
        if not entry_day or entry_day >= report_date or entry_day < start:
            continue
        result.append(entry)
    result.sort(key=lambda item: item.get("report_date", ""))
    return result


def _history_overview(entries: list[dict[str, Any]], report_date: date, history_days: int) -> dict[str, Any]:
    recent_entries = _history_entries_for_window(entries, report_date, history_days)
    active_entries = [
        entry
        for entry in recent_entries
        if (entry.get("log") or {}).get("status") == "ok" and (entry.get("log") or {}).get("messages")
    ]
    history_messages = _flatten_messages(active_entries)
    last_active_date = active_entries[-1].get("report_date") if active_entries else None
    highlights: list[str] = []
    for entry in reversed(active_entries[-3:]):
        messages = (entry.get("log") or {}).get("messages") or []
        snippets = [_trim_text(_flatten_text(message.get("content") or ""), 24) for message in messages[:3] if isinstance(message, dict)]
        preview = " / ".join(snippets) if snippets else "当天无可用消息"
        highlights.append(f"{entry.get('report_date')}: {len(messages)} 条，{preview}")
    return {
        "window_days": history_days,
        "active_days": len(active_entries),
        "message_count": len(history_messages),
        "last_active_date": last_active_date,
        "highlights": highlights,
        "messages": history_messages,
    }


def load_knowledge_assets(knowledge_dir: Path | str | None = None) -> dict[str, Any]:
    root = resolve_knowledge_dir(knowledge_dir)
    chip_path = root / "chip_catalog.json"
    case_path = root / "project_cases.json"
    if not chip_path.exists():
        chip_path = root / "chip_catalog.virtual.json"
    if not case_path.exists():
        case_path = root / "project_cases.virtual.json"

    chip_payload = _read_json(chip_path) or {}
    case_payload = _read_json(case_path) or {}

    chips = chip_payload.get("chips") if isinstance(chip_payload.get("chips"), list) else []
    cases = case_payload.get("cases") if isinstance(case_payload.get("cases"), list) else []

    alias_map: dict[str, dict[str, Any]] = {}
    normalized_chips: list[dict[str, Any]] = []
    for raw_chip in chips:
        if not isinstance(raw_chip, dict):
            continue
        model = str(raw_chip.get("model") or "").strip()
        if not model:
            continue
        aliases = [str(item).strip() for item in raw_chip.get("aliases") or [] if str(item).strip()]
        capabilities_raw = raw_chip.get("capabilities") or {}
        capabilities = {str(key): bool(value) for key, value in capabilities_raw.items()} if isinstance(capabilities_raw, dict) else {}
        entry = {
            "model": model,
            "aliases": aliases,
            "family": raw_chip.get("family"),
            "capabilities": capabilities,
            "fit_scenarios": [str(item).strip() for item in raw_chip.get("fit_scenarios") or [] if str(item).strip()],
            "not_fit_scenarios": [str(item).strip() for item in raw_chip.get("not_fit_scenarios") or [] if str(item).strip()],
            "notes": str(raw_chip.get("notes") or "").strip(),
            "virtual": bool(raw_chip.get("virtual", chip_payload.get("virtual", False))),
        }
        normalized_chips.append(entry)
        for alias in [model, *aliases]:
            alias_map[alias.lower()] = entry

    normalized_cases: list[dict[str, Any]] = []
    for raw_case in cases:
        if not isinstance(raw_case, dict):
            continue
        case_id = str(raw_case.get("id") or "").strip()
        title = str(raw_case.get("title") or case_id).strip()
        if not title:
            continue
        normalized_cases.append(
            {
                "id": case_id or _slugify(title),
                "title": title,
                "summary": str(raw_case.get("summary") or "").strip(),
                "outcome": str(raw_case.get("outcome") or "").strip(),
                "scenario_tags": [str(item).strip() for item in raw_case.get("scenario_tags") or [] if str(item).strip()],
                "chips": [str(item).strip() for item in raw_case.get("chips") or [] if str(item).strip()],
                "attention_points": [str(item).strip() for item in raw_case.get("attention_points") or [] if str(item).strip()],
                "recommended_when": [str(item).strip() for item in raw_case.get("recommended_when") or [] if str(item).strip()],
                "not_recommended_when": [str(item).strip() for item in raw_case.get("not_recommended_when") or [] if str(item).strip()],
                "virtual": bool(raw_case.get("virtual", case_payload.get("virtual", False))),
            }
        )

    return {
        "knowledge_dir": str(root),
        "chip_file": str(chip_path),
        "case_file": str(case_path),
        "virtual": bool(chip_payload.get("virtual", False) or case_payload.get("virtual", False)),
        "chips": normalized_chips,
        "cases": normalized_cases,
        "chip_alias_map": alias_map,
    }


def _message_texts(messages: list[dict[str, Any]]) -> list[str]:
    texts: list[str] = []
    for message in messages:
        text = _flatten_text(message.get("content") or "")
        if text:
            texts.append(text)
    return texts


def _matching_messages(messages: list[dict[str, Any]], patterns: list[re.Pattern[str]], limit: int = 3) -> list[str]:
    matches: list[str] = []
    for message in messages:
        content = _flatten_text(message.get("content") or "")
        if not content:
            continue
        if any(pattern.search(content) for pattern in patterns):
            matches.append(_trim_text(content))
            if len(_dedupe_preserve(matches)) >= limit:
                break
    return _dedupe_preserve(matches)[:limit]


def _detect_capabilities(messages: list[dict[str, Any]], extra_texts: list[str] | None = None) -> list[str]:
    texts = _message_texts(messages)
    if extra_texts:
        texts.extend(str(item).strip() for item in extra_texts if str(item).strip())
    detected: list[str] = []
    for capability, patterns in CAPABILITY_PATTERNS.items():
        if any(pattern.search(text) for text in texts for pattern in patterns):
            detected.append(capability)
    return detected


def _infer_scenario(capabilities: list[str], extra_texts: list[str] | None = None) -> dict[str, Any]:
    text_blob = " ".join(extra_texts or []).lower()
    cap_set = set(capabilities)
    if ("wifi" in cap_set or "ethernet" in cap_set) and (
        {"video_encode", "camera"} & cap_set or "音视频" in text_blob or "推流" in text_blob
    ):
        scenario_id = "wifi_audio_video"
    elif {"camera", "video_encode", "video_decode"} & cap_set:
        scenario_id = "video_device"
    elif {"audio_capture", "audio_playback"} & cap_set:
        scenario_id = "audio_terminal"
    elif "ai" in cap_set:
        scenario_id = "edge_ai"
    elif {"wifi", "ble", "ethernet"} & cap_set:
        scenario_id = "networked_device"
    else:
        scenario_id = "general_presales"
    return {
        "id": scenario_id,
        "title": SCENARIO_TITLE_MAP.get(scenario_id, GENERIC_PROJECT_TITLE),
        "required_capabilities": list(capabilities),
    }


def _extract_artifacts(messages: list[dict[str, Any]], customer: CustomerConfig) -> list[str]:
    seeds: list[str] = []
    if customer.company:
        seeds.append(customer.company)
    seeds.extend(customer.project_hints)
    for message in messages:
        content = _flatten_text(message.get("content") or "")
        if not content:
            continue
        for pattern in (
            r"([\u4e00-\u9fffA-Za-z0-9_-]{2,16}(?:项目|方案|模组|模块|设备|终端|平台|demo|Demo))",
            r"([\u4e00-\u9fffA-Za-z0-9_-]{2,16}(?:WiFi|音视频|摄像头|语音|门铃|对讲|网关))",
        ):
            for match in re.findall(pattern, content, flags=re.IGNORECASE):
                seeds.append(str(match))
    return _dedupe_preserve([item for item in seeds if len(item.strip()) >= 2])[:8]


def _extract_chip_mentions(
    messages: list[dict[str, Any]],
    customer: CustomerConfig,
    knowledge_assets: dict[str, Any],
) -> list[dict[str, Any]]:
    alias_map = knowledge_assets.get("chip_alias_map") or {}
    mentions: list[dict[str, Any]] = []
    seen: set[str] = set()
    search_texts = _message_texts(messages)
    search_texts.extend(customer.chip_focus)
    search_texts.extend(customer.project_hints)
    for text in search_texts:
        lowered = text.lower()
        for alias, chip in alias_map.items():
            if alias and alias in lowered:
                model = str(chip.get("model") or "").strip()
                if model and model not in seen:
                    mentions.append(
                        {
                            "model": model,
                            "matched_by": "alias",
                            "known": True,
                            "chip": chip,
                        }
                    )
                    seen.add(model)
        for token in CHIP_REGEX.findall(text):
            normalized = token.upper()
            if normalized in seen:
                continue
            chip = alias_map.get(token.lower())
            if chip:
                model = str(chip.get("model") or normalized).strip()
                if model not in seen:
                    mentions.append(
                        {
                            "model": model,
                            "matched_by": "regex+catalog",
                            "known": True,
                            "chip": chip,
                        }
                    )
                    seen.add(model)
            else:
                mentions.append(
                    {
                        "model": normalized,
                        "matched_by": "regex",
                        "known": False,
                        "chip": None,
                    }
                )
                seen.add(normalized)
    return mentions[:6]


def _evaluate_chip_selection(
    scenario: dict[str, Any],
    capabilities: list[str],
    chip_mentions: list[dict[str, Any]],
    knowledge_assets: dict[str, Any],
) -> dict[str, Any]:
    required = set(capabilities)
    scenario_id = str(scenario.get("id") or "general_presales")
    evaluations: list[dict[str, Any]] = []
    risks: list[str] = []
    for item in chip_mentions:
        chip = item.get("chip")
        model = str(item.get("model") or "").strip()
        if not chip:
            risks.append(f"{model}: 未命中知识库，当前无法自动校验选型。")
            evaluations.append(
                {
                    "model": model,
                    "known": False,
                    "fit": "unknown",
                    "missing_capabilities": list(required),
                    "scenario_risk": False,
                    "notes": "未命中知识库，等待客户提供真实芯片资料。",
                }
            )
            continue
        chip_caps = {key for key, value in (chip.get("capabilities") or {}).items() if value}
        missing = sorted(required - chip_caps)
        scenario_risk = scenario_id in set(chip.get("not_fit_scenarios") or [])
        fit = not missing and not scenario_risk
        if missing:
            labels = [CAPABILITY_LABELS.get(name, name) for name in missing]
            risks.append(f"{model}: 缺少 {', '.join(labels)} 能力。")
        if scenario_risk:
            risks.append(f"{model}: 知识库标记为不建议用于 {scenario.get('title')}。")
        evaluations.append(
            {
                "model": model,
                "known": True,
                "fit": "fit" if fit else "risk",
                "family": chip.get("family"),
                "supported_capabilities": [CAPABILITY_LABELS.get(name, name) for name in sorted(chip_caps & required)],
                "missing_capabilities": [CAPABILITY_LABELS.get(name, name) for name in missing],
                "scenario_risk": scenario_risk,
                "notes": chip.get("notes") or "",
                "virtual": bool(chip.get("virtual")),
            }
        )
    return {
        "required_capabilities": [CAPABILITY_LABELS.get(name, name) for name in capabilities],
        "chips": evaluations,
        "risks": _dedupe_preserve(risks),
        "knowledge_virtual": bool(knowledge_assets.get("virtual")),
    }


def _score_similar_cases(
    scenario: dict[str, Any],
    chip_mentions: list[dict[str, Any]],
    knowledge_assets: dict[str, Any],
) -> list[dict[str, Any]]:
    scenario_id = str(scenario.get("id") or "general_presales")
    chip_models = {str(item.get("model") or "").strip() for item in chip_mentions if item.get("model")}
    ranked: list[tuple[int, dict[str, Any]]] = []
    for case in knowledge_assets.get("cases") or []:
        score = 0
        if scenario_id in set(case.get("scenario_tags") or []):
            score += 3
        score += len(chip_models & set(case.get("chips") or [])) * 2
        if score <= 0:
            continue
        ranked.append(
            (
                score,
                {
                    "id": case.get("id"),
                    "title": case.get("title"),
                    "summary": case.get("summary"),
                    "outcome": case.get("outcome"),
                    "chips": list(case.get("chips") or []),
                    "attention_points": list(case.get("attention_points") or []),
                    "recommended_when": list(case.get("recommended_when") or []),
                    "not_recommended_when": list(case.get("not_recommended_when") or []),
                    "score": score,
                    "virtual": bool(case.get("virtual")),
                },
            )
        )
    ranked.sort(key=lambda item: (-item[0], str(item[1].get("title") or "")))
    return [payload for _, payload in ranked[:3]]


def _assess_requirement_clarity(messages: list[dict[str, Any]]) -> dict[str, Any]:
    demand_hits = _matching_messages(messages, DEMAND_PATTERNS, limit=5)
    vague_hits = _matching_messages(messages, VAGUE_PATTERNS, limit=4)
    question_hits = _matching_messages(messages, QUESTION_PATTERNS, limit=4)
    risk_hits = _matching_messages(messages, RISK_PATTERNS, limit=3)

    missing_fields: list[str] = []
    if not demand_hits:
        missing_fields.append("业务目标")
    if vague_hits:
        missing_fields.append("功能边界")
    if question_hits:
        missing_fields.append("确认结论")
    if risk_hits:
        missing_fields.append("风险闭环")

    if not messages:
        level = "none"
    elif len(missing_fields) >= 3:
        level = "low"
    elif len(missing_fields) >= 1:
        level = "medium"
    else:
        level = "high"

    return {
        "level": level,
        "demand_hits": demand_hits,
        "vague_hits": vague_hits,
        "question_hits": question_hits,
        "missing_fields": _dedupe_preserve(missing_fields),
    }


def _build_business_digest(messages: list[dict[str, Any]]) -> dict[str, Any]:
    demand_items = _matching_messages(messages, DEMAND_PATTERNS, limit=5)
    business_items = _matching_messages(messages, BUSINESS_PATTERNS, limit=5)
    schedule_items = _matching_messages(messages, SCHEDULE_PATTERNS + ADDRESS_PATTERNS, limit=5)
    tech_items = _matching_messages(messages, TECH_PATTERNS, limit=5)
    urgent_items = _matching_messages(messages, URGENT_PATTERNS, limit=4)
    risk_items = _matching_messages(messages, RISK_PATTERNS, limit=4)
    open_questions = _matching_messages(messages, QUESTION_PATTERNS, limit=4)
    closure_signals = _matching_messages(messages, CLOSURE_PATTERNS, limit=3)

    next_actions = _dedupe_preserve(
        [
            *[f"跟进需求确认: {item}" for item in open_questions[:2]],
            *[f"推进约访/时间确认: {item}" for item in schedule_items[:2]],
            *[f"处理风险项: {item}" for item in risk_items[:2]],
        ]
    )[:5]

    highlights = _dedupe_preserve(
        demand_items[:2] + business_items[:2] + schedule_items[:2] + tech_items[:2]
    )[:6]

    return {
        "highlights": highlights,
        "demand_items": demand_items,
        "business_items": business_items,
        "schedule_items": schedule_items,
        "technical_items": tech_items,
        "urgent_items": urgent_items,
        "risk_items": risk_items,
        "open_questions": open_questions,
        "closure_signals": closure_signals,
        "next_actions": next_actions,
    }


def _infer_stage(
    log: CustomerDailyLog,
    digest: dict[str, Any],
    clarity: dict[str, Any],
    selection_review: dict[str, Any],
    history: dict[str, Any],
) -> str:
    if log.status in {"error", "not_found"}:
        return "抓取失败待处理"
    if log.status == "empty":
        return "当天无新增"
    if digest.get("schedule_items"):
        return "约访推进"
    if selection_review.get("risks") or digest.get("technical_items"):
        return "技术评估"
    if digest.get("business_items"):
        return "商务推进"
    if clarity.get("level") in {"low", "medium"} and digest.get("demand_items"):
        return "需求澄清"
    if history.get("message_count"):
        return "持续跟进"
    return "初次建联"


def _severity_for_text(text: str) -> str:
    normalized = text.lower()
    if any(pattern.search(normalized) for pattern in URGENT_PATTERNS + RISK_PATTERNS):
        return "high"
    if any(pattern.search(normalized) for pattern in TECH_PATTERNS + QUESTION_PATTERNS):
        return "medium"
    return "low"


def _build_issue(
    category: str,
    title: str,
    *,
    report_date: date,
    needs_engineering: bool = False,
    project_ids: list[str] | None = None,
) -> dict[str, Any]:
    issue_id = hashlib.sha1(f"{category}:{title}".encode("utf-8")).hexdigest()[:12]
    return {
        "id": issue_id,
        "category": category,
        "title": _trim_text(title, 80),
        "severity": _severity_for_text(title),
        "status": "open",
        "needs_engineering": needs_engineering,
        "project_ids": list(project_ids or []),
        "first_seen_date": report_date.isoformat(),
        "last_seen_date": report_date.isoformat(),
        "evidence": [_trim_text(title, 80)],
        "history": [{"date": report_date.isoformat(), "status": "open"}],
    }


def _build_projects(
    customer: CustomerConfig,
    report_date: date,
    stage: str,
    scenario: dict[str, Any],
    digest: dict[str, Any],
    clarity: dict[str, Any],
    selection_review: dict[str, Any],
    similar_cases: list[dict[str, Any]],
    artifacts: list[str],
) -> list[dict[str, Any]]:
    titles = _dedupe_preserve([*customer.project_hints, *artifacts, str(scenario.get("title") or GENERIC_PROJECT_TITLE)])
    selected_titles = titles[:3] if titles else [GENERIC_PROJECT_TITLE]
    projects: list[dict[str, Any]] = []
    for title in selected_titles:
        project_id = _slugify(title)
        projects.append(
            {
                "id": project_id,
                "title": title,
                "customer_id": customer.id,
                "owner": customer.owner,
                "stage": stage,
                "scenario": scenario,
                "required_capabilities": list(selection_review.get("required_capabilities") or []),
                "chip_candidates": [chip.get("model") for chip in selection_review.get("chips") or [] if chip.get("model")],
                "selection_risks": list(selection_review.get("risks") or []),
                "highlights": list(digest.get("highlights") or []),
                "next_actions": list(digest.get("next_actions") or []),
                "clarity_level": clarity.get("level"),
                "last_updated": report_date.isoformat(),
                "similar_cases": similar_cases,
            }
        )
    return projects


def _build_todays_issues(
    report_date: date,
    digest: dict[str, Any],
    clarity: dict[str, Any],
    selection_review: dict[str, Any],
    project_ids: list[str],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for item in digest.get("urgent_items") or []:
        issues.append(_build_issue("urgent", item, report_date=report_date, project_ids=project_ids))
    for item in digest.get("risk_items") or []:
        issues.append(_build_issue("risk", item, report_date=report_date, needs_engineering=True, project_ids=project_ids))
    for item in digest.get("technical_items") or []:
        issues.append(_build_issue("technical", item, report_date=report_date, needs_engineering=True, project_ids=project_ids))
    for item in digest.get("open_questions") or []:
        issues.append(_build_issue("open_question", item, report_date=report_date, project_ids=project_ids))
    for item in selection_review.get("risks") or []:
        issues.append(_build_issue("selection_risk", item, report_date=report_date, needs_engineering=True, project_ids=project_ids))
    if clarity.get("level") in {"low", "medium"} and clarity.get("missing_fields"):
        title = f"需求信息仍不完整，缺少: {', '.join(clarity.get('missing_fields') or [])}"
        issues.append(_build_issue("clarification", title, report_date=report_date, project_ids=project_ids))

    deduped: dict[str, dict[str, Any]] = {}
    for issue in issues:
        deduped[issue["id"]] = issue
    return list(deduped.values())


def _merge_issue_state(
    existing_payload: dict[str, Any] | None,
    todays_issues: list[dict[str, Any]],
    *,
    report_date: date,
    digest: dict[str, Any],
    retention_days: int,
) -> dict[str, Any]:
    existing_items = existing_payload.get("issues") if isinstance(existing_payload, dict) else []
    merged: dict[str, dict[str, Any]] = {}
    for item in existing_items or []:
        if not isinstance(item, dict):
            continue
        last_seen_raw = item.get("last_seen_date")
        try:
            last_seen = date.fromisoformat(str(last_seen_raw))
        except ValueError:
            last_seen = report_date
        if (report_date - last_seen).days > retention_days:
            continue
        merged[str(item.get("id") or "")] = dict(item)

    for issue in todays_issues:
        current = merged.get(issue["id"])
        if current:
            current["last_seen_date"] = report_date.isoformat()
            current["severity"] = min(
                [str(current.get("severity") or "low"), str(issue.get("severity") or "low")],
                key=lambda value: SEVERITY_ORDER.get(value, 99),
            )
            current["needs_engineering"] = bool(current.get("needs_engineering")) or bool(issue.get("needs_engineering"))
            current["project_ids"] = _dedupe_preserve(list(current.get("project_ids") or []) + list(issue.get("project_ids") or []))
            evidence = list(current.get("evidence") or []) + list(issue.get("evidence") or [])
            current["evidence"] = _dedupe_preserve([_trim_text(item, 80) for item in evidence])[:6]
            history = list(current.get("history") or [])
            history.append({"date": report_date.isoformat(), "status": "open"})
            current["history"] = history[-10:]
            current["status"] = "open"
        else:
            merged[issue["id"]] = issue

    closure_signals = digest.get("closure_signals") or []
    if closure_signals and not todays_issues:
        for item in merged.values():
            if item.get("status") == "open":
                item["status"] = "resolved_candidate"
                history = list(item.get("history") or [])
                history.append({"date": report_date.isoformat(), "status": "resolved_candidate"})
                item["history"] = history[-10:]

    issues = list(merged.values())
    issues.sort(key=lambda item: (SEVERITY_ORDER.get(str(item.get("severity") or "low"), 99), str(item.get("title") or "")))
    return {
        "report_date": report_date.isoformat(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "open_count": sum(1 for item in issues if item.get("status") == "open"),
        "issues": issues,
    }


def _build_triage(
    digest: dict[str, Any],
    clarity: dict[str, Any],
    selection_review: dict[str, Any],
    issues_payload: dict[str, Any],
) -> dict[str, Any]:
    urgent_count = len(digest.get("urgent_items") or [])
    risk_count = len(digest.get("risk_items") or []) + len(selection_review.get("risks") or [])
    tech_count = len(digest.get("technical_items") or [])
    open_issue_count = int(issues_payload.get("open_count") or 0)
    if urgent_count or risk_count >= 2:
        priority = "high"
    elif tech_count or open_issue_count:
        priority = "medium"
    else:
        priority = "low"
    return {
        "priority": priority,
        "urgent_count": urgent_count,
        "risk_count": risk_count,
        "technical_count": tech_count,
        "open_issue_count": open_issue_count,
        "needs_engineering_followup": any(
            bool(item.get("needs_engineering"))
            for item in issues_payload.get("issues") or []
        ),
        "requirement_clarity": clarity.get("level"),
    }


def _build_execution_split(
    customer: CustomerConfig,
    stage: str,
    triage: dict[str, Any],
    projects: list[dict[str, Any]],
    issues_payload: dict[str, Any],
    knowledge_assets: dict[str, Any],
) -> dict[str, Any]:
    project_titles = [project.get("title") for project in projects if project.get("title")]
    return {
        "code_can_do": [
            "按客户抓取当天微信聊天并按日归档。",
            "从聊天中抽取需求、商务、技术、风险、紧急事项并生成结构化摘要。",
            "维护客户时间轴、项目快照、issue 列表、日报和周报草稿。",
            "根据知识库规则做芯片能力匹配和相似案例召回。",
        ],
        "llm_can_do": [
            "结合完整上下文改写成面向销售/FAE的自然语言报告。",
            "对模糊需求做更细致的补全推断，并给出沟通话术。",
            "根据业务背景判断优先级、责任归属和升级路径。",
            "在代码已提取的结构化信号上生成周会纪要、客户汇报或待办清单。",
        ],
        "suggested_llm_tasks": [
            f"基于 {customer.display_name} 当前阶段“{stage}”，输出一版给销售自己看的客户跟进纪要。",
            f"结合项目 {', '.join(project_titles[:2]) if project_titles else GENERIC_PROJECT_TITLE}，补写建议回复话术和下一步推进顺序。",
            f"围绕 {triage.get('priority')} 优先级问题，判断哪些事项需要技术团队参与并给出升级建议。",
        ],
        "current_context": {
            "stage": stage,
            "priority": triage.get("priority"),
            "open_issue_count": issues_payload.get("open_count"),
            "project_count": len(projects),
            "knowledge_virtual": bool(knowledge_assets.get("virtual")),
        },
        "constraints": [
            "发送者身份仍不可得，报告只能基于对话整体而非逐句归因。",
            "时间粒度依赖 UIA 时间分隔块，不是每条消息精确时间。",
            "芯片/案例评估只在知识库命中时可靠；当前未命中的型号只会提示人工补资料。",
        ],
    }


def _analyze_daily_log(
    customer: CustomerConfig,
    log: CustomerDailyLog,
    report_date: date,
    history: dict[str, Any],
    knowledge_assets: dict[str, Any],
    existing_issues: dict[str, Any] | None,
    issue_retention_days: int,
) -> dict[str, Any]:
    messages = list(log.messages or [])
    extra_texts = list(customer.project_hints) + list(customer.chip_focus)
    artifacts = _extract_artifacts(messages, customer)
    capabilities = _detect_capabilities(messages, extra_texts=extra_texts + artifacts)
    scenario = _infer_scenario(capabilities, extra_texts=extra_texts + artifacts)
    chip_mentions = _extract_chip_mentions(messages, customer, knowledge_assets)
    selection_review = _evaluate_chip_selection(scenario, capabilities, chip_mentions, knowledge_assets)
    similar_cases = _score_similar_cases(scenario, chip_mentions, knowledge_assets)
    clarity = _assess_requirement_clarity(messages)
    digest = _build_business_digest(messages)
    stage = _infer_stage(log, digest, clarity, selection_review, history)
    projects = _build_projects(
        customer,
        report_date,
        stage,
        scenario,
        digest,
        clarity,
        selection_review,
        similar_cases,
        artifacts,
    )
    project_ids = [project["id"] for project in projects]
    todays_issues = _build_todays_issues(report_date, digest, clarity, selection_review, project_ids)
    issues_payload = _merge_issue_state(
        existing_issues,
        todays_issues,
        report_date=report_date,
        digest=digest,
        retention_days=issue_retention_days,
    )
    triage = _build_triage(digest, clarity, selection_review, issues_payload)
    execution_split = _build_execution_split(customer, stage, triage, projects, issues_payload, knowledge_assets)
    return {
        "stage": stage,
        "artifacts": artifacts,
        "capabilities": [CAPABILITY_LABELS.get(name, name) for name in capabilities],
        "scenario": scenario,
        "clarity": clarity,
        "digest": digest,
        "selection_review": selection_review,
        "similar_cases": similar_cases,
        "projects": projects,
        "issues": issues_payload,
        "triage": triage,
        "execution_split": execution_split,
    }


def _entry_summary(entry: dict[str, Any]) -> str:
    analysis = entry.get("analysis") or {}
    digest = analysis.get("digest") or {}
    highlights = list(digest.get("highlights") or [])
    if highlights:
        return " / ".join(highlights[:3])
    log = entry.get("log") or {}
    messages = log.get("messages") or []
    if messages:
        first = messages[0]
        return _trim_text(_flatten_text(first.get("content") or ""), 60)
    return "当天无可用内容"


def _render_timeline_markdown(customer: CustomerConfig, entries: list[dict[str, Any]]) -> str:
    lines = [
        f"# {customer.display_name} 客户时间轴",
        "",
        f"- customer_id: `{customer.id}`",
        f"- target: `{customer.target}`",
        f"- owner: `{customer.owner or '未指定'}`",
        f"- tags: {', '.join(customer.tags) if customer.tags else '无'}",
        f"- company: {customer.company or '未填写'}",
        "",
    ]
    for entry in sorted(entries, key=lambda item: item.get("report_date", ""), reverse=True):
        report_day = str(entry.get("report_date") or "")
        log = entry.get("log") or {}
        analysis = entry.get("analysis") or {}
        issues = (analysis.get("issues") or {}).get("issues") or []
        projects = analysis.get("projects") or []
        digest = analysis.get("digest") or {}
        lines.extend(
            [
                f"## {report_day}",
                "",
                f"- status: `{log.get('status', 'unknown')}`",
                f"- message_count: `{log.get('message_count', 0)}`",
                f"- stage: `{analysis.get('stage', '未识别')}`",
                f"- summary: {_entry_summary(entry)}",
                f"- projects: {', '.join(project.get('title') for project in projects if project.get('title')) or '无'}",
                f"- open_issues: {sum(1 for item in issues if item.get('status') == 'open')}",
                "",
            ]
        )
        highlights = list(digest.get("highlights") or [])
        if highlights:
            lines.append("### 重点摘录")
            lines.append("")
            for item in highlights[:5]:
                lines.append(f"- {item}")
            lines.append("")
        for message in log.get("messages") or []:
            time_label = str(message.get("time") or "").strip() or "--:--"
            content = _flatten_text(message.get("content") or "")
            if not content:
                continue
            lines.append(f"- `{time_label}` {content}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_project_overview_markdown(customer: CustomerConfig, projects: list[dict[str, Any]]) -> str:
    lines = [
        f"# {customer.display_name} 项目档案",
        "",
        "当前项目快照由规则提炼生成，适合作为销售/FAE的持续上下文底稿。",
        "",
    ]
    for project in projects:
        lines.extend(
            [
                f"## {project.get('title')}",
                "",
                f"- stage: `{project.get('stage')}`",
                f"- owner: `{project.get('owner') or '未指定'}`",
                f"- scenario: `{((project.get('scenario') or {}).get('title') or GENERIC_PROJECT_TITLE)}`",
                f"- clarity_level: `{project.get('clarity_level') or 'unknown'}`",
                f"- chip_candidates: {', '.join(project.get('chip_candidates') or []) or '无'}",
                "",
            ]
        )
        if project.get("highlights"):
            lines.append("### 关键进展")
            lines.append("")
            for item in project.get("highlights") or []:
                lines.append(f"- {item}")
            lines.append("")
        if project.get("selection_risks"):
            lines.append("### 选型风险")
            lines.append("")
            for item in project.get("selection_risks") or []:
                lines.append(f"- {item}")
            lines.append("")
        if project.get("next_actions"):
            lines.append("### 下一步")
            lines.append("")
            for item in project.get("next_actions") or []:
                lines.append(f"- {item}")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_daily_report_markdown(customer: CustomerConfig, payload: dict[str, Any]) -> str:
    log = payload.get("log") or {}
    analysis = payload.get("analysis") or {}
    digest = analysis.get("digest") or {}
    triage = analysis.get("triage") or {}
    clarity = analysis.get("clarity") or {}
    selection_review = analysis.get("selection_review") or {}
    issues_payload = analysis.get("issues") or {}
    execution_split = analysis.get("execution_split") or {}

    lines = [
        f"# {customer.display_name} 每日客户跟进报告",
        "",
        f"- report_date: `{payload.get('report_date')}`",
        f"- status: `{log.get('status')}`",
        f"- stage: `{analysis.get('stage')}`",
        f"- priority: `{triage.get('priority')}`",
        f"- message_count: `{log.get('message_count')}`",
        f"- owner: `{customer.owner or '未指定'}`",
        "",
        "## 今日概览",
        "",
    ]
    for item in digest.get("highlights") or ["当天未识别到有效业务摘要。"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## 风险与紧急事项",
            "",
        ]
    )
    risk_items = _dedupe_preserve((digest.get("urgent_items") or []) + (digest.get("risk_items") or []) + (selection_review.get("risks") or []))
    for item in risk_items or ["当天未识别到显著风险。"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## 需求与技术判断",
            "",
            f"- clarity_level: `{clarity.get('level')}`",
            f"- missing_fields: {', '.join(clarity.get('missing_fields') or []) or '无'}",
            f"- required_capabilities: {', '.join(selection_review.get('required_capabilities') or []) or '未识别'}",
            "",
        ]
    )
    tech_block = _dedupe_preserve((digest.get("technical_items") or []) + (digest.get("open_questions") or []))
    for item in tech_block or ["当天无明显技术问题或待确认问题。"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## 项目与 issue",
            "",
        ]
    )
    for project in analysis.get("projects") or []:
        lines.append(f"- 项目 {project.get('title')}: 阶段 `{project.get('stage')}`，下一步 {', '.join(project.get('next_actions') or []) or '待补充'}")
    if not analysis.get("projects"):
        lines.append("- 当前未建立项目快照。")
    for issue in (issues_payload.get("issues") or [])[:6]:
        lines.append(f"- issue[{issue.get('severity')}|{issue.get('status')}]: {issue.get('title')}")
    if not issues_payload.get("issues"):
        lines.append("- 当前没有持续跟踪的 issue。")
    lines.extend(
        [
            "",
            "## 芯片与案例提示",
            "",
            f"- knowledge_virtual: `{selection_review.get('knowledge_virtual')}`",
        ]
    )
    for chip in selection_review.get("chips") or []:
        lines.append(
            f"- 芯片 {chip.get('model')}: 评估 `{chip.get('fit')}`，缺失能力 {', '.join(chip.get('missing_capabilities') or []) or '无'}"
        )
    if not selection_review.get("chips"):
        lines.append("- 当天未识别到可评估的芯片型号。")
    for case in analysis.get("similar_cases") or []:
        lines.append(f"- 相似案例 {case.get('title')}: {case.get('summary') or case.get('outcome') or '无摘要'}")
    if not analysis.get("similar_cases"):
        lines.append("- 暂无命中的相似案例。")
    lines.extend(
        [
            "",
            "## 代码层与大模型层分工",
            "",
            "### 代码已完成",
            "",
        ]
    )
    for item in execution_split.get("code_can_do") or []:
        lines.append(f"- {item}")
    lines.extend(["", "### 建议交给大模型继续完成", ""])
    for item in execution_split.get("suggested_llm_tasks") or []:
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def _render_weekly_report_markdown(customer: CustomerConfig, weekly_payload: dict[str, Any]) -> str:
    lines = [
        f"# {customer.display_name} 周跟进报告",
        "",
        f"- report_date: `{weekly_payload.get('report_date')}`",
        f"- window_start: `{weekly_payload.get('window_start')}`",
        f"- active_days: `{weekly_payload.get('active_days')}`",
        f"- message_count: `{weekly_payload.get('message_count')}`",
        f"- latest_stage: `{weekly_payload.get('latest_stage')}`",
        "",
        "## 本周重点",
        "",
    ]
    for item in weekly_payload.get("weekly_highlights") or ["本周暂无高价值摘要。"]:
        lines.append(f"- {item}")
    lines.extend(["", "## 持续风险", ""])
    for item in weekly_payload.get("open_issues") or ["本周没有持续未闭环 issue。"]:
        lines.append(f"- {item}")
    lines.extend(["", "## 项目推进", ""])
    for item in weekly_payload.get("project_updates") or ["本周没有新的项目更新。"]:
        lines.append(f"- {item}")
    lines.extend(["", "## 下周建议", ""])
    for item in weekly_payload.get("next_week_actions") or ["下周继续按日刷新客户跟进记录。"]:
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def _build_weekly_payload(
    customer: CustomerConfig,
    report_date: date,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    window_start = report_date - timedelta(days=6)
    weekly_entries = [
        entry
        for entry in entries
        if (entry_day := _entry_date(entry)) is not None and window_start <= entry_day <= report_date
    ]
    weekly_entries.sort(key=lambda item: item.get("report_date", ""))

    highlights: list[str] = []
    project_updates: list[str] = []
    open_issues: list[str] = []
    next_week_actions: list[str] = []
    latest_stage = "无记录"
    message_count = 0
    active_days = 0

    for entry in weekly_entries:
        log = entry.get("log") or {}
        analysis = entry.get("analysis") or {}
        if log.get("status") == "ok":
            active_days += 1
        message_count += int(log.get("message_count") or 0)
        stage = str(analysis.get("stage") or "").strip()
        if stage:
            latest_stage = stage
        digest = analysis.get("digest") or {}
        highlights.extend([f"{entry.get('report_date')}: {item}" for item in list(digest.get("highlights") or [])[:2]])
        next_week_actions.extend(list(digest.get("next_actions") or [])[:2])
        for project in analysis.get("projects") or []:
            title = str(project.get("title") or "").strip()
            if title:
                project_updates.append(f"{title}: 阶段 {project.get('stage')}")
        for issue in (analysis.get("issues") or {}).get("issues") or []:
            if issue.get("status") == "open":
                open_issues.append(str(issue.get("title") or ""))

    return {
        "report_date": report_date.isoformat(),
        "window_start": window_start.isoformat(),
        "active_days": active_days,
        "message_count": message_count,
        "latest_stage": latest_stage,
        "weekly_highlights": _dedupe_preserve(highlights)[:8],
        "project_updates": _dedupe_preserve(project_updates)[:8],
        "open_issues": _dedupe_preserve(open_issues)[:8],
        "next_week_actions": _dedupe_preserve(next_week_actions)[:8],
        "virtual_knowledge": any(
            bool(((entry.get("analysis") or {}).get("selection_review") or {}).get("knowledge_virtual"))
            for entry in weekly_entries
        ),
    }


def persist_customer_followup(
    output_root: Path | str,
    report_date: date,
    customer: CustomerConfig,
    log: CustomerDailyLog,
    *,
    history_days: int = DEFAULT_HISTORY_DAYS,
    issue_retention_days: int = DEFAULT_ISSUE_RETENTION_DAYS,
    knowledge_dir: Path | str | None = None,
) -> dict[str, Any]:
    root = Path(output_root).resolve()
    customer_dir = root / "customers" / customer.id
    report_dir = root / "reports" / report_date.isoformat()
    weekly_dir = root / "reports" / "weekly" / report_date.isoformat()
    customer_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    weekly_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = customer_dir / "customer.json"
    issues_dir = customer_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    (issues_dir / "history").mkdir(parents=True, exist_ok=True)
    projects_dir = customer_dir / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    existing_entries = [entry for entry in load_customer_entries(customer_dir) if entry.get("report_date") != report_date.isoformat()]
    history = _history_overview(existing_entries, report_date, history_days)
    existing_issues = _read_json(issues_dir / "current.json")
    knowledge_assets = load_knowledge_assets(knowledge_dir)
    analysis = _analyze_daily_log(
        customer,
        log,
        report_date,
        history,
        knowledge_assets,
        existing_issues,
        issue_retention_days,
    )

    daily_payload = {
        "report_date": report_date.isoformat(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "customer": _customer_metadata(customer),
        "log": asdict(log),
        "history": {key: value for key, value in history.items() if key != "messages"},
        "analysis": analysis,
        "source": {
            "knowledge_dir": knowledge_assets.get("knowledge_dir"),
            "knowledge_virtual": bool(knowledge_assets.get("virtual")),
        },
    }

    daily_path = customer_dir / "daily" / f"{report_date.isoformat()}.json"
    _write_json(daily_path, daily_payload)

    entries = sorted(existing_entries + [daily_payload], key=lambda item: item.get("report_date", ""))
    timeline_path = customer_dir / "timeline.md"
    timeline_path.write_text(_render_timeline_markdown(customer, entries), encoding="utf-8")

    projects = analysis.get("projects") or []
    for project in projects:
        _write_json(projects_dir / f"{project['id']}.json", project)
    projects_overview_payload = {
        "customer_id": customer.id,
        "report_date": report_date.isoformat(),
        "project_count": len(projects),
        "projects": projects,
    }
    projects_overview_json = projects_dir / "overview.json"
    projects_overview_md = projects_dir / "overview.md"
    _write_json(projects_overview_json, projects_overview_payload)
    projects_overview_md.write_text(_render_project_overview_markdown(customer, projects), encoding="utf-8")

    issues_current_path = issues_dir / "current.json"
    issues_history_path = issues_dir / "history" / f"{report_date.isoformat()}.json"
    _write_json(issues_current_path, analysis.get("issues") or {})
    _write_json(issues_history_path, analysis.get("issues") or {})

    report_json_path = report_dir / f"{customer.id}.json"
    report_md_path = report_dir / f"{customer.id}.md"
    _write_json(report_json_path, daily_payload)
    report_md_path.write_text(_render_daily_report_markdown(customer, daily_payload), encoding="utf-8")

    weekly_payload = _build_weekly_payload(customer, report_date, entries)
    weekly_json_path = weekly_dir / f"{customer.id}.json"
    weekly_md_path = weekly_dir / f"{customer.id}.md"
    _write_json(weekly_json_path, weekly_payload)
    weekly_md_path.write_text(_render_weekly_report_markdown(customer, weekly_payload), encoding="utf-8")

    existing_meta = _read_json(metadata_path) or {}
    customer_meta = {
        **_customer_metadata(customer),
        "created_at": existing_meta.get("created_at") or datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "last_report_date": report_date.isoformat(),
        "last_stage": analysis.get("stage"),
        "last_status": log.status,
        "timeline_file": str(timeline_path),
        "latest_daily_file": str(daily_path),
        "latest_report_file": str(report_md_path),
        "projects_overview_file": str(projects_overview_md),
        "issues_file": str(issues_current_path),
        "weekly_report_file": str(weekly_md_path),
    }
    _write_json(metadata_path, customer_meta)

    return {
        "id": customer.id,
        "display_name": customer.display_name,
        "status": log.status,
        "message_count": log.message_count,
        "stage": analysis.get("stage"),
        "priority": (analysis.get("triage") or {}).get("priority"),
        "knowledge_virtual": bool(knowledge_assets.get("virtual")),
        "timeline_file": str(timeline_path),
        "daily_file": str(daily_path),
        "report_file": str(report_md_path),
        "report_json_file": str(report_json_path),
        "projects_overview_file": str(projects_overview_md),
        "projects_overview_json_file": str(projects_overview_json),
        "issues_file": str(issues_current_path),
        "issues_history_file": str(issues_history_path),
        "weekly_report_file": str(weekly_md_path),
        "weekly_report_json_file": str(weekly_json_path),
    }


def write_daily_index(
    output_root: Path | str,
    report_date: date,
    customer_outputs: list[dict[str, Any]],
    *,
    source_config: str,
    request_args: dict[str, Any],
) -> dict[str, Any]:
    root = Path(output_root).resolve()
    report_dir = root / "reports" / report_date.isoformat()
    report_dir.mkdir(parents=True, exist_ok=True)
    batch_file = report_dir / "batch.json"
    index_file = report_dir / "index.md"

    payload = {
        "report_date": report_date.isoformat(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_config": source_config,
        "request_args": request_args,
        "customers": customer_outputs,
    }
    _write_json(batch_file, payload)

    lines = [
        f"# 客户跟进总览 {report_date.isoformat()}",
        "",
        f"- source_config: `{source_config}`",
        f"- customer_count: `{len(customer_outputs)}`",
        "",
        "| 客户 | 状态 | 阶段 | 优先级 | 每日报告 | 时间轴 | 项目档案 | issues | 周报 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in customer_outputs:
        lines.append(
            "| {name} | {status} | {stage} | {priority} | [{daily}]({daily_path}) | "
            "[timeline]({timeline_path}) | [projects]({projects_path}) | [issues]({issues_path}) | [weekly]({weekly_path}) |".format(
                name=item.get("display_name"),
                status=item.get("status"),
                stage=item.get("stage") or "未识别",
                priority=item.get("priority") or "low",
                daily="report",
                daily_path=item.get("report_file"),
                timeline_path=item.get("timeline_file"),
                projects_path=item.get("projects_overview_file"),
                issues_path=item.get("issues_file"),
                weekly_path=item.get("weekly_report_file"),
            )
        )
    index_file.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return {"index_file": str(index_file), "batch_file": str(batch_file)}


def write_weekly_index(
    output_root: Path | str,
    report_date: date,
    customer_outputs: list[dict[str, Any]],
    *,
    source_config: str,
    request_args: dict[str, Any],
) -> dict[str, Any]:
    root = Path(output_root).resolve()
    weekly_dir = root / "reports" / "weekly" / report_date.isoformat()
    weekly_dir.mkdir(parents=True, exist_ok=True)
    batch_file = weekly_dir / "batch.json"
    index_file = weekly_dir / "index.md"

    payload = {
        "report_date": report_date.isoformat(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_config": source_config,
        "request_args": request_args,
        "customers": customer_outputs,
    }
    _write_json(batch_file, payload)

    lines = [
        f"# 客户周报总览 {report_date.isoformat()}",
        "",
        "| 客户 | 状态 | 阶段 | 周报 | 项目档案 | issues |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in customer_outputs:
        lines.append(
            "| {name} | {status} | {stage} | [weekly]({weekly_path}) | [projects]({projects_path}) | [issues]({issues_path}) |".format(
                name=item.get("display_name"),
                status=item.get("status"),
                stage=item.get("stage") or "未识别",
                weekly_path=item.get("weekly_report_file"),
                projects_path=item.get("projects_overview_file"),
                issues_path=item.get("issues_file"),
            )
        )
    index_file.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return {"index_file": str(index_file), "batch_file": str(batch_file)}
