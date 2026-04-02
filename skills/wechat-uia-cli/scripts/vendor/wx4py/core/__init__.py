# -*- coding: utf-8 -*-
"""Core module - window management and UIAutomation wrapper"""

from .exceptions import (
    WeChatError,
    WeChatNotFoundError,
    WeChatNotConnectedError,
    UIAError,
    ControlNotFoundError,
    TargetNotFoundError,
    RegistryError,
)

__all__ = [
    "WeChatWindow",
    "UIAWrapper",
    "WeChatError",
    "WeChatNotFoundError",
    "WeChatNotConnectedError",
    "UIAError",
    "ControlNotFoundError",
    "TargetNotFoundError",
    "RegistryError",
]


def __getattr__(name):
    """Lazily import heavy Windows/UIA modules on first access."""
    if name == "WeChatWindow":
        from .window import WeChatWindow

        return WeChatWindow
    if name == "UIAWrapper":
        from .uia_wrapper import UIAWrapper

        return UIAWrapper
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
