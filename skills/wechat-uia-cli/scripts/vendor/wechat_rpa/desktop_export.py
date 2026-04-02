"""Dedicated RPA flow for WeChat desktop export dialogs."""
from __future__ import annotations

import logging
import time
from importlib import import_module
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class FlowStepResult:
    """One flow step execution result."""

    step: str
    ok: bool
    detail: str


class DesktopExportFlow:
    """Drive the WeChat desktop export-chat-history flow via UI Automation."""

    def __init__(self, wx_client: Any):
        self.wx = wx_client
        self.window = wx_client.window
        self.root = wx_client.window.uia.root
        package_name = wx_client.__class__.__module__.split(".", 1)[0]
        self.uia = import_module(f"{package_name}.core.uiautomation")

    def run(
        self,
        targets: list[str],
        time_range_label: str,
        content_scope_label: str,
        max_scrolls: int = 25,
        step_delay: float = 0.8,
    ) -> dict[str, Any]:
        """Execute the full desktop export flow."""
        steps: list[FlowStepResult] = []

        def record(step: str, ok: bool, detail: str) -> bool:
            steps.append(FlowStepResult(step=step, ok=ok, detail=detail))
            return ok

        self.window.activate()
        time.sleep(step_delay)

        if not record("open_more", self.open_more_menu(), "click 更多"):
            return self._result(False, steps, targets)
        if not record("open_chat_history_manager", self.open_chat_history_manager_from_more(), "click 聊天记录管理"):
            return self._result(False, steps, targets)
        if self.is_visible(["选择需要导出的聊天记录"], scope="desktop", exact_first=True):
            record("enter_target_selector", True, "selector opened directly")
        else:
            if not record("open_export_chat_history", self.click_named(["导出聊天记录"], scope="desktop"), "click 导出聊天记录"):
                return self._result(False, steps, targets)
            if not self.is_visible(["选择需要导出的聊天记录"], scope="desktop", exact_first=True):
                if not record(
                    "select_targeted_export",
                    self.click_named(["仅导出指定聊天记录", "仅导出指定聊天"], scope="desktop", exact_first=True),
                    "click 仅导出指定聊天",
                ):
                    return self._result(False, steps, targets)
        if not record(
            "open_time_range_dropdown",
            self.open_combo_value(["全部时间", "时间范围"], preferred_rect=(880, 280, 1020, 360)),
            "open time range dropdown",
        ):
            return self._result(False, steps, targets)
        if not record(
            "select_time_range",
            self.select_popup_option(time_range_label),
            f"select time range {time_range_label}",
        ):
            return self._result(False, steps, targets)
        if not record(
            "open_content_scope_dropdown",
            self.open_combo_value(["全部聊天记录", "全部聊天内容", "聊天内容"], preferred_rect=(1000, 280, 1160, 360)),
            "open content scope dropdown",
        ):
            return self._result(False, steps, targets)
        if not record(
            "select_content_scope",
            self.select_popup_option(content_scope_label),
            f"select content scope {content_scope_label}",
        ):
            return self._result(False, steps, targets)

        select_result = self.select_targets(targets, max_scrolls=max_scrolls, step_delay=step_delay)
        steps.extend(select_result["steps"])
        if not select_result["ok"]:
            return self._result(False, steps, targets)

        if not record("click_start", self.click_start_button(), "click 开始"):
            return self._result(False, steps, targets)

        return self._result(True, steps, targets)

    def _result(self, ok: bool, steps: list[FlowStepResult], targets: list[str]) -> dict[str, Any]:
        """Build final result payload."""
        return {
            "ok": ok,
            "targets": targets,
            "steps": [step.__dict__ for step in steps],
        }

    def _walk_controls(self, root: Any, max_depth: int = 15) -> list[tuple[Any, int]]:
        """Enumerate descendants defensively."""
        result: list[tuple[Any, int]] = []

        def visit(ctrl: Any, depth: int) -> None:
            if depth > max_depth:
                return
            result.append((ctrl, depth))
            try:
                children = list(ctrl.GetChildren())
            except Exception:
                return

            for child in children:
                try:
                    visit(child, depth + 1)
                except Exception:
                    continue

        visit(root, 0)
        return result

    def _iter_scope_controls(self, scope: str) -> list[Any]:
        """Return controls from the requested search scope."""
        if scope == "main":
            return [ctrl for ctrl, _ in self._walk_controls(self.root)]
        if scope == "desktop":
            desktop_root = self.uia.GetRootControl()
            return [ctrl for ctrl, _ in self._walk_controls(desktop_root)]
        raise ValueError(f"unsupported scope: {scope}")

    def _normalize_name(self, ctrl: Any) -> str:
        """Return normalized control name."""
        try:
            return (getattr(ctrl, "Name", "") or "").strip()
        except Exception:
            return ""

    def _visible_rect(self, ctrl: Any) -> Any:
        """Return bounding rectangle when present."""
        try:
            rect = getattr(ctrl, "BoundingRectangle", None)
        except Exception:
            return None
        if not rect:
            return None
        try:
            if rect.right <= rect.left or rect.bottom <= rect.top:
                return None
        except Exception:
            return None
        return rect

    def _match_candidates(self, labels: list[str], scope: str, exact_first: bool = False) -> list[Any]:
        """Find visible controls matching labels."""
        controls = self._iter_scope_controls(scope)
        exact_matches: list[Any] = []
        contains_matches: list[Any] = []

        for ctrl in controls:
            name = self._normalize_name(ctrl)
            if not name:
                continue
            if not self._visible_rect(ctrl):
                continue

            for label in labels:
                if name == label:
                    exact_matches.append(ctrl)
                    break
                if label in name:
                    contains_matches.append(ctrl)
                    break

        if exact_first and exact_matches:
            return exact_matches
        return exact_matches + contains_matches

    def _sort_candidates(self, controls: list[Any], strategy: str) -> list[Any]:
        """Sort candidates for more predictable clicking."""
        def key(ctrl: Any) -> tuple[int, int]:
            rect = self._visible_rect(ctrl)
            if not rect:
                return (0, 0)
            cx = int((rect.left + rect.right) / 2)
            cy = int((rect.top + rect.bottom) / 2)
            return (cx, cy)

        if strategy == "bottom_left":
            return sorted(controls, key=lambda ctrl: (key(ctrl)[1], -key(ctrl)[0]), reverse=True)
        if strategy == "top_right":
            return sorted(controls, key=lambda ctrl: (key(ctrl)[1], key(ctrl)[0]))
        if strategy == "bottom_right":
            return sorted(controls, key=lambda ctrl: (key(ctrl)[1], key(ctrl)[0]), reverse=True)
        return controls

    def is_visible(self, labels: list[str], scope: str = "desktop", exact_first: bool = False) -> bool:
        """Return whether any matching visible control exists."""
        return bool(self._match_candidates(labels, scope=scope, exact_first=exact_first))

    def _match_candidates_in_rect(
        self,
        labels: list[str],
        rect_range: tuple[int, int, int, int],
        scope: str = "desktop",
        exact_first: bool = False,
    ) -> list[Any]:
        """Find visible controls matching labels inside a rectangle."""
        left, top, right, bottom = rect_range
        matches = []
        for ctrl in self._match_candidates(labels, scope=scope, exact_first=exact_first):
            rect = self._visible_rect(ctrl)
            if not rect:
                continue
            cx = int((rect.left + rect.right) / 2)
            cy = int((rect.top + rect.bottom) / 2)
            if left <= cx <= right and top <= cy <= bottom:
                matches.append(ctrl)
        return matches

    def click_named(
        self,
        labels: list[str],
        scope: str = "desktop",
        strategy: str = "first",
        exact_first: bool = False,
        retries: int = 3,
        delay: float = 0.8,
    ) -> bool:
        """Find a control by visible name and click it."""
        for _ in range(retries):
            matches = self._match_candidates(labels, scope=scope, exact_first=exact_first)
            matches = self._sort_candidates(matches, strategy)
            if matches:
                logger.debug(
                    "Candidates for %s: %s",
                    labels,
                    [
                        {
                            "name": self._normalize_name(ctrl),
                            "type": getattr(ctrl, "ControlTypeName", "") or "",
                            "class_name": getattr(ctrl, "ClassName", "") or "",
                            "rect": (
                                None
                                if not self._visible_rect(ctrl)
                                else (
                                    self._visible_rect(ctrl).left,
                                    self._visible_rect(ctrl).top,
                                    self._visible_rect(ctrl).right,
                                    self._visible_rect(ctrl).bottom,
                                )
                            ),
                        }
                        for ctrl in matches[:5]
                    ],
                )
            if matches:
                ctrl = matches[0]
                try:
                    ctrl.SetFocus()
                except Exception:
                    pass
                try:
                    ctrl.Click()
                    time.sleep(delay)
                    logger.info("Clicked control: %s", self._normalize_name(ctrl))
                    return True
                except Exception as exc:
                    logger.debug("Direct click failed for %s: %s", self._normalize_name(ctrl), exc)
                    rect = self._visible_rect(ctrl)
                    if rect:
                        self.uia.Click(int((rect.left + rect.right) / 2), int((rect.top + rect.bottom) / 2))
                        time.sleep(delay)
                        logger.info("Clicked by coordinates: %s", self._normalize_name(ctrl))
                        return True
            time.sleep(delay)
        return False

    def open_combo_value(self, labels: list[str], preferred_rect: tuple[int, int, int, int], delay: float = 0.8) -> bool:
        """Open a combo box by clicking the currently displayed value in a known area."""
        matches = self._match_candidates_in_rect(labels, preferred_rect, scope="desktop", exact_first=True)
        if not matches:
            matches = self._match_candidates(labels, scope="desktop", exact_first=True)
        matches = self._sort_candidates(matches, "top_right")
        if not matches:
            return False

        ctrl = matches[0]
        rect = self._visible_rect(ctrl)
        try:
            ctrl.Click()
            time.sleep(delay)
            return True
        except Exception:
            if rect:
                self.uia.Click(int((rect.left + rect.right) / 2), int((rect.top + rect.bottom) / 2))
                time.sleep(delay)
                return True
        return False

    def select_popup_option(self, label: str, delay: float = 0.8) -> bool:
        """Select a dropdown option from the export popup menu."""
        for _ in range(3):
            matches = []
            for ctrl in self._match_candidates([label], scope="desktop", exact_first=True):
                rect = self._visible_rect(ctrl)
                if not rect:
                    continue
                control_type = self._safe_attr(ctrl, "ControlTypeName")
                class_name = self._safe_attr(ctrl, "ClassName")
                if control_type in {"MenuItemControl", "TextControl", "ButtonControl"} or "Menu" in class_name:
                    matches.append(ctrl)
            matches = self._sort_candidates(matches, "top_right")
            if matches:
                ctrl = matches[0]
                rect = self._visible_rect(ctrl)
                try:
                    ctrl.Click()
                    time.sleep(delay)
                    return True
                except Exception:
                    if rect:
                        self.uia.Click(int((rect.left + rect.right) / 2), int((rect.top + rect.bottom) / 2))
                        time.sleep(delay)
                        return True
            time.sleep(delay)
        return False

    def _candidate_scroll_container(self) -> Any | None:
        """Pick the largest visible list-like control on the desktop."""
        controls = self._iter_scope_controls("desktop")
        candidates = []
        for ctrl in controls:
            rect = self._visible_rect(ctrl)
            if not rect:
                continue
            control_type = getattr(ctrl, "ControlTypeName", "") or ""
            class_name = getattr(ctrl, "ClassName", "") or ""
            if control_type in {"ListControl", "PaneControl", "GroupControl"} or "List" in class_name:
                area = (rect.right - rect.left) * (rect.bottom - rect.top)
                candidates.append((area, ctrl))

        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _scroll_container(self, ctrl: Any, delta: int = -360, steps: int = 3, step_delay: float = 0.15, settle_time: float = 0.6) -> bool:
        """Scroll a list-like control by mouse wheel."""
        rect = self._visible_rect(ctrl)
        if not rect:
            return False

        import win32api
        import win32con

        cx = int((rect.left + rect.right) / 2)
        cy = int((rect.top + rect.bottom) / 2)
        win32api.SetCursorPos((cx, cy))
        for _ in range(steps):
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
            time.sleep(step_delay)
        time.sleep(settle_time)
        return True

    def _try_select_target(self, target: str) -> bool:
        """Try to select one visible target row or checkbox."""
        matches = self._match_candidates([target], scope="desktop", exact_first=True)
        if not matches:
            return False

        ctrl = matches[0]
        rect = self._visible_rect(ctrl)

        # The export selector uses a row-level checkbox on the left side.
        if rect:
            checkbox_x = int(rect.left + 24)
            checkbox_y = int((rect.top + rect.bottom) / 2)
            self.uia.Click(checkbox_x, checkbox_y)
            time.sleep(0.4)
            if self._selected_target_count() > 0:
                return True

        for child in [ctrl] + list(getattr(ctrl, "GetChildren", lambda: [])()):
            try:
                control_type = getattr(child, "ControlTypeName", "") or ""
                if control_type == "CheckBoxControl":
                    child.Click()
                    time.sleep(0.4)
                    if self._selected_target_count() > 0:
                        return True
            except Exception:
                continue

        try:
            selection_pattern = ctrl.GetSelectionItemPattern()
            if selection_pattern:
                selection_pattern.Select()
                time.sleep(0.4)
                if self._selected_target_count() > 0:
                    return True
        except Exception:
            pass

        try:
            ctrl.Click()
            time.sleep(0.4)
            return self._selected_target_count() > 0
        except Exception:
            if rect:
                self.uia.Click(int((rect.left + rect.right) / 2), int((rect.top + rect.bottom) / 2))
                time.sleep(0.4)
                return self._selected_target_count() > 0

        return False

    def select_targets(self, targets: list[str], max_scrolls: int = 25, step_delay: float = 0.8) -> dict[str, Any]:
        """Scroll through the selector and click all requested targets."""
        remaining = list(dict.fromkeys(targets))
        steps: list[FlowStepResult] = []

        container = self._candidate_scroll_container()
        if not container:
            steps.append(FlowStepResult("find_target_list", False, "no visible scroll container found"))
            return {"ok": False, "steps": steps}

        for target in list(remaining):
            if self._try_select_target(target):
                steps.append(FlowStepResult("select_target", True, f"selected visible target '{target}'"))
                remaining.remove(target)

        scroll_count = 0
        while remaining and scroll_count < max_scrolls:
            if not self._scroll_container(container):
                break
            time.sleep(step_delay)
            scroll_count += 1

            for target in list(remaining):
                if self._try_select_target(target):
                    steps.append(FlowStepResult("select_target", True, f"selected '{target}' after scroll {scroll_count}"))
                    remaining.remove(target)

        if remaining:
            steps.append(FlowStepResult("select_target", False, f"targets not found: {remaining}"))
            return {"ok": False, "steps": steps}

        return {"ok": True, "steps": steps}

    def click_start_button(self, delay: float = 0.8) -> bool:
        """Click the start button in the bottom-right of the export window."""
        matches = self._match_candidates_in_rect(["开始"], (1080, 760, 1240, 860), scope="desktop", exact_first=True)
        if not matches:
            matches = self._match_candidates(["开始"], scope="desktop", exact_first=True)
        matches = self._sort_candidates(matches, "bottom_right")
        if not matches:
            return False

        ctrl = matches[0]
        rect = self._visible_rect(ctrl)
        try:
            ctrl.Click()
            time.sleep(delay)
            return True
        except Exception:
            if rect:
                self.uia.Click(int((rect.left + rect.right) / 2), int((rect.top + rect.bottom) / 2))
                time.sleep(delay)
                return True
        return False

    def _selected_target_count(self) -> int:
        """Read the currently selected target count from the footer."""
        for ctrl in self._iter_scope_controls("desktop"):
            name = self._normalize_name(ctrl)
            if not name.startswith("已选 "):
                continue
            if " 个聊天" not in name:
                continue
            try:
                count_text = name.replace("已选 ", "").replace(" 个聊天", "").strip()
                return int(count_text)
            except ValueError:
                continue
        return 0

    def open_more_menu(self) -> bool:
        """Open the bottom-left '更多' menu from the WeChat navigation bar."""
        root_controls = self._iter_scope_controls("main")
        candidates = []

        for ctrl in root_controls:
            rect = self._visible_rect(ctrl)
            if not rect:
                continue

            class_name = self._safe_attr(ctrl, "ClassName")
            automation_id = self._safe_attr(ctrl, "AutomationId")
            control_type = self._safe_attr(ctrl, "ControlTypeName")
            name = self._normalize_name(ctrl)

            if rect.right > 220:
                continue
            if rect.top < 650:
                continue

            if (
                name == "更多"
                or "tabbar_setting" in automation_id
                or "MainTabBarSettingView" in class_name
                or (control_type == "ButtonControl" and 110 <= rect.left <= 170 and rect.height() if hasattr(rect, "height") else True)
            ):
                candidates.append(ctrl)

        candidates = self._sort_candidates(candidates, "bottom_left")
        if candidates:
            ctrl = candidates[0]
            rect = self._visible_rect(ctrl)
            logger.debug(
                "More-menu candidates: %s",
                [
                    {
                        "name": self._normalize_name(item),
                        "type": self._safe_attr(item, "ControlTypeName"),
                        "class_name": self._safe_attr(item, "ClassName"),
                        "automation_id": self._safe_attr(item, "AutomationId"),
                        "rect": (
                            None
                            if not self._visible_rect(item)
                            else (
                                self._visible_rect(item).left,
                                self._visible_rect(item).top,
                                self._visible_rect(item).right,
                                self._visible_rect(item).bottom,
                            )
                        ),
                    }
                    for item in candidates[:5]
                ],
            )
            try:
                ctrl.Click()
                time.sleep(0.8)
                logger.info("Clicked more-menu control: %s", self._normalize_name(ctrl))
                return True
            except Exception:
                if rect:
                    self.uia.Click(int((rect.left + rect.right) / 2), int((rect.top + rect.bottom) / 2))
                    time.sleep(0.8)
                    logger.info("Clicked more-menu control by coordinates")
                    return True

        # Last-resort hard-coded click inside the bottom navigation slot.
        try:
            nav = self.root.ToolBarControl(AutomationId="MainView.main_tabbar")
            if nav.Exists(maxSearchSeconds=0.5):
                nav_rect = nav.BoundingRectangle
                x = int((nav_rect.left + nav_rect.right) / 2)
                y = int(nav_rect.bottom - 34)
                self.uia.Click(x, y)
                time.sleep(0.8)
                logger.info("Clicked more-menu fallback point")
                return True
        except Exception:
            pass

        return False

    def open_chat_history_manager(self) -> bool:
        """Open the chat-history backup management panel from WeChat settings."""
        if self.click_named(["聊天记录管理"], scope="desktop", exact_first=True):
            return True

        # Settings -> storage space uses row-level "管理" buttons.
        # Prefer the lower "聊天记录备份文件" row instead of the upper "聊天数据" row.
        controls = self._iter_scope_controls("desktop")
        backup_label = None
        manage_buttons = []

        for ctrl in controls:
            name = self._normalize_name(ctrl)
            rect = self._visible_rect(ctrl)
            if not rect:
                continue
            ctype = getattr(ctrl, "ControlTypeName", "") or ""
            if name == "聊天记录备份文件":
                backup_label = rect
            if name == "管理" and ctype == "ButtonControl":
                manage_buttons.append((rect, ctrl))

        if backup_label and manage_buttons:
            same_row = [
                (rect, ctrl)
                for rect, ctrl in manage_buttons
                if abs(rect.top - backup_label.top) <= 25 or abs(rect.bottom - backup_label.bottom) <= 25
            ]
            if same_row:
                same_row.sort(key=lambda item: item[0].left, reverse=True)
                try:
                    same_row[0][1].Click()
                    time.sleep(0.8)
                    logger.info("Clicked backup manage button")
                    return True
                except Exception:
                    rect = same_row[0][0]
                    self.uia.Click(int((rect.left + rect.right) / 2), int((rect.top + rect.bottom) / 2))
                    time.sleep(0.8)
                    logger.info("Clicked backup manage button by coordinates")
                    return True

        return self.click_named(["管理"], scope="desktop", strategy="bottom_right", exact_first=True)

    def open_chat_history_manager_from_more(self) -> bool:
        """Open chat-history management from the 更多 popover."""
        controls = self._iter_scope_controls("desktop")
        candidates = []

        for ctrl in controls:
            rect = self._visible_rect(ctrl)
            if not rect:
                continue

            if self._normalize_name(ctrl) != "聊天记录管理":
                continue

            class_name = self._safe_attr(ctrl, "ClassName")
            control_type = self._safe_attr(ctrl, "ControlTypeName")
            if class_name == "mmui::XButton" or control_type == "ButtonControl":
                candidates.append(ctrl)

        if candidates:
            ctrl = candidates[0]
            rect = self._visible_rect(ctrl)
            try:
                ctrl.Click()
                time.sleep(1.0)
                logger.info("Clicked 聊天记录管理 menu item")
                return True
            except Exception:
                if rect:
                    self.uia.Click(int((rect.left + rect.right) / 2), int((rect.top + rect.bottom) / 2))
                    time.sleep(1.0)
                    logger.info("Clicked 聊天记录管理 menu item by coordinates")
                    return True

        self.uia.Click(225, 665)
        time.sleep(1.0)
        return self.is_visible(["选择需要导出的聊天记录", "聊天记录迁移与备份", "存储空间"], scope="desktop")

    def _safe_attr(self, ctrl: Any, attr: str) -> str:
        """Read a control attribute defensively."""
        try:
            return getattr(ctrl, attr, "") or ""
        except Exception:
            return ""
