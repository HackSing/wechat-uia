# -*- coding: utf-8 -*-
"""
wx4py - Python 微信自动化工具

基于 UIAutomation 的微信自动化 Python 库，支持 Windows Qt 版本微信客户端。
"""

from ._version import __version__
from .core.exceptions import (
    WeChatError,
    WeChatNotFoundError,
    WeChatNotConnectedError,
    ControlNotFoundError,
    TargetNotFoundError,
    RegistryError,
)

__author__ = "wx4py Team"

__all__ = [
    "WeChatClient",
    "WeChatError",
    "WeChatNotFoundError",
    "WeChatNotConnectedError",
    "ControlNotFoundError",
    "TargetNotFoundError",
    "RegistryError",
]


def __getattr__(name):
    """Lazily import heavy modules on first access."""
    if name == "WeChatClient":
        from .client import WeChatClient

        return WeChatClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
