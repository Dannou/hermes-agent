"""
RTK Rewrite Plugin for Hermes (JarvisV3 Edition)

Transparently rewrites terminal tool commands to RTK equivalents
before execution, achieving 60-90% LLM token savings.

All rewrite logic lives in `rtk rewrite` (the RTK binary).
This plugin is a thin delegate — to add or change rules, edit the
Rust registry in RTK itself, not this file.

Installation:
    # 1. Install RTK
    brew install rtk
    # or: curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh

    # 2. Restart Hermes — the plugin auto-registers, no config needed

How it works:
    Agent runs: terminal(command="cargo test --nocapture")
      → Plugin intercepts pre_tool_call hook
      → Calls `rtk rewrite "cargo test --nocapture"`
      → Mutates args["command"] = "rtk cargo test --nocapture"
      → Agent executes the rewritten command
      → Filtered output reaches LLM (~90% fewer tokens)

IMPORTANT — TEMPERATURE RULE (Immutable):
    This plugin NEVER modifies model temperature.
    The temperature MUST remain at 0.6 for kimi-for-code.
    This is a non-negotiable requirement.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from typing import Optional

__version__ = "1.0.0"

logger = logging.getLogger(__name__)

_rtk_available: Optional[bool] = None


def _check_rtk() -> bool:
    """Check if rtk binary is available in PATH. Result is cached."""
    global _rtk_available
    if _rtk_available is not None:
        return _rtk_available
    _rtk_available = shutil.which("rtk") is not None
    return _rtk_available


def _try_rewrite(command: str) -> Optional[str]:
    """Delegate to `rtk rewrite` and return the rewritten command, or None."""
    try:
        result = subprocess.run(
            ["rtk", "rewrite", command],
            capture_output=True,
            text=True,
            timeout=2,
        )
        rewritten = result.stdout.strip()
        if result.returncode == 0 and rewritten and rewritten != command:
            return rewritten
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def _pre_tool_call(*, tool_name: str, args: dict, task_id: str, **_kwargs) -> None:
    """pre_tool_call hook: rewrite terminal commands to use RTK.

    Mutates ``args["command"]`` in-place when RTK provides a rewrite.
    The dict is mutable, so changes propagate to the caller without
    needing a return value.
    
    TEMPERATURE SAFETY: This hook NEVER touches temperature settings.
    Temperature must remain at 0.6 for kimi-for-code compatibility.
    """
    if tool_name != "terminal":
        return

    command = args.get("command")
    if not isinstance(command, str) or not command:
        return

    rewritten = _try_rewrite(command)
    if rewritten:
        logger.debug("[rtk] %s -> %s", command, rewritten)
        args["command"] = rewritten


def register(ctx) -> None:
    """Entry point called by Hermes plugin system."""
    if not _check_rtk():
        logger.warning("[rtk] rtk binary not found in PATH — plugin disabled")
        logger.warning("[rtk] Install RTK: brew install rtk")
        logger.warning("[rtk] Or: curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh")
        return

    ctx.register_hook("pre_tool_call", _pre_tool_call)
    logger.info("[rtk] Hermes plugin registered — token savings active")
