# -*- coding: utf-8 -*-
"""
Daily report fetcher.

Batch-collects chat history for a configured list of customers, wrapping
`ChatWindow.get_chat_history` with:

  * YAML/JSON config loading (with aliases, tags, groups, per-customer overrides)
  * Candidate-target fallback (tries `target`, then each entry in `aliases`)
  * Structured per-customer status (ok / empty / not_found / error)
  * Cross-customer error isolation (one failing customer does not abort the batch)
  * Day-scoped cache (skip customers already fetched successfully today)

This module does NOT generate the report itself. It produces a structured
JSON payload intended to be consumed by an upstream AI layer that will
format the actual evening report.

Limitation inherited from wx4py: WeChat 4.x UIA does not expose the sender
of each message. The returned `messages` arrays are sender-agnostic.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Optional

from ..core.exceptions import TargetNotFoundError
from ..utils.logger import get_logger

logger = get_logger(__name__)


CUSTOMER_STATUSES = ("ok", "empty", "not_found", "error")


@dataclass
class CustomerConfig:
    """One customer entry parsed from customers.yaml / customers.json."""

    id: str
    display_name: str
    target: str
    aliases: list[str] = field(default_factory=list)
    target_type: str = "contact"
    tags: list[str] = field(default_factory=list)
    priority: str = "medium"
    company: Optional[str] = None
    notes: Optional[str] = None
    max_count: Optional[int] = None
    since: Optional[str] = None


@dataclass
class CustomerDailyLog:
    """Per-customer fetch result, serialized into the CLI JSON output."""

    id: str
    display_name: str
    status: str  # one of CUSTOMER_STATUSES
    target_type: str = "contact"
    target_used: Optional[str] = None
    tried_targets: list[str] = field(default_factory=list)
    message_count: int = 0
    first_message_time: Optional[str] = None
    last_message_time: Optional[str] = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    truncated: bool = False
    error: Optional[str] = None
    error_type: Optional[str] = None
    # Mirror of config metadata so downstream consumers have everything in one blob.
    tags: list[str] = field(default_factory=list)
    priority: str = "medium"
    company: Optional[str] = None
    notes: Optional[str] = None
    # Bookkeeping.
    from_cache: bool = False
    fetched_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def load_customers_config(config_path: Path) -> tuple[list[CustomerConfig], dict[str, Any]]:
    """
    Load customers config from a YAML or JSON file.

    Returns:
        (customers, meta) where meta contains:
            - version: int
            - defaults: dict[str, Any]
            - groups: dict[str, list[str]]   # group_name -> customer ids
    """
    if not config_path.exists():
        raise FileNotFoundError(f"config file not found: {config_path}")

    suffix = config_path.suffix.lower()
    raw_text = config_path.read_text(encoding="utf-8")

    if suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError as exc:  # pragma: no cover - bootstrap should install
            raise ImportError(
                "pyyaml is required to read YAML config; install it or use a .json config instead"
            ) from exc
        data = yaml.safe_load(raw_text) or {}
    elif suffix == ".json":
        data = json.loads(raw_text)
    else:
        raise ValueError(f"unsupported config extension: {suffix} (use .yaml or .json)")

    if not isinstance(data, dict):
        raise ValueError("config root must be a mapping")

    defaults = data.get("defaults") or {}
    if not isinstance(defaults, dict):
        raise ValueError("config.defaults must be a mapping")

    groups_raw = data.get("groups") or {}
    if not isinstance(groups_raw, dict):
        raise ValueError("config.groups must be a mapping")
    groups: dict[str, list[str]] = {}
    for name, members in groups_raw.items():
        if not isinstance(members, list):
            raise ValueError(f"config.groups['{name}'] must be a list of customer ids")
        groups[str(name)] = [str(m) for m in members]

    raw_customers = data.get("customers") or []
    if not isinstance(raw_customers, list):
        raise ValueError("config.customers must be a list")

    customers: list[CustomerConfig] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_customers):
        if not isinstance(item, dict):
            raise ValueError(f"customers[{index}] must be a mapping")

        cust_id = str(item.get("id") or "").strip()
        if not cust_id:
            raise ValueError(f"customers[{index}].id is required")
        if cust_id in seen_ids:
            raise ValueError(f"duplicate customer id: {cust_id}")
        seen_ids.add(cust_id)

        target = str(item.get("target") or "").strip()
        if not target:
            raise ValueError(f"customers[{cust_id}].target is required")

        display_name = str(item.get("display_name") or target).strip()

        aliases_raw = item.get("aliases") or []
        if not isinstance(aliases_raw, list):
            raise ValueError(f"customers[{cust_id}].aliases must be a list")
        aliases = [str(a).strip() for a in aliases_raw if str(a).strip()]

        tags_raw = item.get("tags") or []
        if not isinstance(tags_raw, list):
            raise ValueError(f"customers[{cust_id}].tags must be a list")
        tags = [str(t).strip() for t in tags_raw if str(t).strip()]

        target_type = str(item.get("target_type") or defaults.get("target_type") or "contact")
        if target_type not in ("contact", "group"):
            raise ValueError(f"customers[{cust_id}].target_type must be 'contact' or 'group'")

        max_count_raw = item.get("max_count")
        max_count_val: Optional[int] = None
        if max_count_raw is not None:
            try:
                max_count_val = int(max_count_raw)
            except (TypeError, ValueError):
                raise ValueError(f"customers[{cust_id}].max_count must be an integer")

        since_val = item.get("since")
        if since_val is not None and not isinstance(since_val, str):
            raise ValueError(f"customers[{cust_id}].since must be a string")

        customers.append(
            CustomerConfig(
                id=cust_id,
                display_name=display_name,
                target=target,
                aliases=aliases,
                target_type=target_type,
                tags=tags,
                priority=str(item.get("priority") or "medium"),
                company=item.get("company") if isinstance(item.get("company"), str) else None,
                notes=item.get("notes") if isinstance(item.get("notes"), str) else None,
                max_count=max_count_val,
                since=since_val,
            )
        )

    meta = {
        "version": int(data.get("version", 1)),
        "defaults": defaults,
        "groups": groups,
    }
    return customers, meta


def filter_customers(
    customers: list[CustomerConfig],
    meta: dict[str, Any],
    *,
    ids: Optional[Iterable[str]] = None,
    group: Optional[str] = None,
    tags: Optional[Iterable[str]] = None,
) -> list[CustomerConfig]:
    """
    Filter customers by explicit ids, a named group, or tags.

    Precedence:
        - If `ids` is given, return exactly those (error if any id is unknown).
        - Else apply `group` AND `tags` as an intersection.
        - If none given, return all customers.
    """
    if ids:
        id_list = [str(i) for i in ids]
        known_ids = {c.id for c in customers}
        missing = [i for i in id_list if i not in known_ids]
        if missing:
            raise ValueError(f"unknown customer ids: {missing}")
        id_set = set(id_list)
        # Preserve input order (matches config order).
        return [c for c in customers if c.id in id_set]

    selected = list(customers)

    if group:
        group_ids = meta.get("groups", {}).get(group)
        if group_ids is None:
            raise ValueError(f"unknown group: {group}")
        group_id_set = set(group_ids)
        selected = [c for c in selected if c.id in group_id_set]

    if tags:
        tag_set = {str(t) for t in tags}
        selected = [c for c in selected if any(t in tag_set for t in c.tags)]

    return selected


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------


class DailyReportFetcher:
    """Fetch daily chat messages for a configured list of customers."""

    def __init__(self, client) -> None:
        self._client = client

    def fetch_one(
        self,
        customer: CustomerConfig,
        *,
        since: str,
        max_count: int,
    ) -> CustomerDailyLog:
        """
        Fetch a single customer.

        Never raises on per-customer issues. Returns a CustomerDailyLog with
        `status` set to one of ok / empty / not_found / error.

        Resolution order for searchable names:
            1. customer.target
            2. each entry in customer.aliases (in order)
        """
        log = CustomerDailyLog(
            id=customer.id,
            display_name=customer.display_name,
            status="error",
            target_type=customer.target_type,
            tags=list(customer.tags),
            priority=customer.priority,
            company=customer.company,
            notes=customer.notes,
        )

        effective_since = customer.since or since
        effective_max = int(customer.max_count) if customer.max_count else int(max_count)

        # Build unique candidate list preserving order.
        candidates: list[str] = []
        for name in (customer.target, *customer.aliases):
            if name and name not in candidates:
                candidates.append(name)

        tried: list[str] = []
        last_not_found: Optional[Exception] = None

        for candidate in candidates:
            tried.append(candidate)
            try:
                messages = self._client.chat_window.get_chat_history(
                    candidate,
                    target_type=customer.target_type,
                    since=effective_since,
                    max_count=effective_max,
                )
            except TargetNotFoundError as exc:
                logger.info(
                    f"customer {customer.id}: target '{candidate}' not found, trying next candidate"
                )
                last_not_found = exc
                continue
            except Exception as exc:
                logger.warning(
                    f"customer {customer.id}: error while fetching '{candidate}': {type(exc).__name__}: {exc}"
                )
                log.tried_targets = tried
                log.target_used = candidate
                log.status = "error"
                log.error = str(exc)
                log.error_type = type(exc).__name__
                log.fetched_at = datetime.now().isoformat(timespec="seconds")
                return log

            # Success path: messages may still be an empty list.
            log.tried_targets = tried
            log.target_used = candidate
            log.messages = messages
            log.message_count = len(messages)
            log.truncated = len(messages) >= effective_max
            log.fetched_at = datetime.now().isoformat(timespec="seconds")
            if messages:
                log.status = "ok"
                log.first_message_time = messages[0].get("time") or None
                log.last_message_time = messages[-1].get("time") or None
            else:
                log.status = "empty"
            return log

        # All candidates exhausted with TargetNotFoundError.
        log.tried_targets = tried
        log.status = "not_found"
        if last_not_found is not None:
            log.error = str(last_not_found)
            log.error_type = type(last_not_found).__name__
        else:
            log.error = "no candidate targets configured"
            log.error_type = "ValueError"
        log.fetched_at = datetime.now().isoformat(timespec="seconds")
        return log

    def fetch_all(
        self,
        customers: list[CustomerConfig],
        *,
        since: str = "today",
        max_count: int = 300,
        stop_on_error: bool = False,
        cache: Optional[dict[str, CustomerDailyLog]] = None,
        use_cache: bool = True,
    ) -> list[CustomerDailyLog]:
        """
        Fetch all customers in order, honoring cache and error isolation.

        Cache semantics:
            - Entries with status `ok` or `empty` in `cache` are reused
              (their `from_cache` flag is flipped to True).
            - Entries with status `not_found` or `error` are always re-fetched
              (errors should be given a second chance next run).

        Does not raise on per-customer errors. If `stop_on_error` is True and
        a customer ends in `error` status, the loop breaks early and the
        remaining customers are NOT in the returned list.
        """
        logs: list[CustomerDailyLog] = []
        cache = cache or {}

        for customer in customers:
            cached = cache.get(customer.id) if use_cache else None
            if cached and cached.status in ("ok", "empty"):
                cached.from_cache = True
                logs.append(cached)
                logger.info(
                    f"customer {customer.id}: reused cached result (status={cached.status}, "
                    f"messages={cached.message_count})"
                )
                continue

            log = self.fetch_one(customer, since=since, max_count=max_count)
            log.from_cache = False
            logs.append(log)

            logger.info(
                f"customer {customer.id}: fetched (status={log.status}, messages={log.message_count})"
            )

            if log.status == "error" and stop_on_error:
                logger.warning(f"stop_on_error: aborting batch after {customer.id}")
                break

        return logs


# ---------------------------------------------------------------------------
# JSON & cache helpers
# ---------------------------------------------------------------------------


def logs_to_json(logs: list[CustomerDailyLog]) -> list[dict[str, Any]]:
    """Serialize CustomerDailyLog objects into plain dicts for JSON output."""
    return [asdict(log) for log in logs]


def load_cache(cache_dir: Path, report_date: date) -> dict[str, CustomerDailyLog]:
    """
    Load cached customer logs for a given date, keyed by customer id.

    Returns an empty dict if the cache file does not exist or cannot be parsed.
    Cache files whose internal `report_date` does not match are discarded.
    """
    cache_file = cache_dir / f"{report_date.isoformat()}.json"
    if not cache_file.exists():
        return {}
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(f"failed to read cache file {cache_file}: {exc}")
        return {}

    if not isinstance(data, dict):
        return {}
    if data.get("report_date") != report_date.isoformat():
        logger.warning(f"cache file {cache_file} has mismatched report_date, ignoring")
        return {}

    customers_raw = data.get("customers") or []
    if not isinstance(customers_raw, list):
        return {}

    known_fields = {f.name for f in fields(CustomerDailyLog)}
    result: dict[str, CustomerDailyLog] = {}
    for item in customers_raw:
        if not isinstance(item, dict):
            continue
        cust_id = item.get("id")
        if not cust_id:
            continue
        try:
            filtered = {k: v for k, v in item.items() if k in known_fields}
            result[str(cust_id)] = CustomerDailyLog(**filtered)
        except Exception as exc:
            logger.warning(f"failed to parse cache entry {cust_id}: {exc}")
            continue
    return result


def save_cache(
    cache_dir: Path,
    report_date: date,
    logs: list[CustomerDailyLog],
    *,
    existing: Optional[dict[str, CustomerDailyLog]] = None,
) -> Path:
    """
    Merge new logs into existing cache entries and write to disk atomically.

    `existing` should be the dict previously returned by `load_cache`. Entries
    in `logs` overwrite matching `existing` entries by customer id.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{report_date.isoformat()}.json"

    merged: dict[str, CustomerDailyLog] = dict(existing or {})
    for log in logs:
        merged[log.id] = log

    payload = {
        "report_date": report_date.isoformat(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "customers": [asdict(log) for log in merged.values()],
    }

    tmp_file = cache_file.with_suffix(".json.tmp")
    tmp_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp_file.replace(cache_file)
    return cache_file
