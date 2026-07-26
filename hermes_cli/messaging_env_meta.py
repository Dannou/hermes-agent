"""Shared UI metadata for messaging-platform env vars.

Every messaging platform ships the same handful of optional knobs
(``*_HOME_CHANNEL``, ``*_ALLOW_ALL_USERS``, ``*_REPLY_TO_MODE``, ``*_PROXY``).
They all have a working fallback, or Hermes sets them for the user later
(``/sethome`` on the first chat writes the home channel) — so a setup surface
that lists them next to the bot token reads as several more things you must
fill in before the platform will work.

This module is the single source of truth for two facts about such a var:

- ``advanced`` — the surface may collapse/skip it by default.
- ``default`` / ``choices`` — what Hermes actually does when it is left blank,
  and the fixed value set when one exists.

The dashboard/Desktop channel forms and the ``hermes setup gateway`` CLI wizard
both read from here. Keeping it in one place is deliberate: the Desktop app
previously carried its own hardcoded list of "advanced" keys, which drifted
from the backend by construction and silently missed every plugin platform.

Matching is **suffix-driven** so plugin adapters nobody enumerated (IRC,
SimpleX, LINE, …) get the same treatment for free.
"""

from typing import Any

# Suffix -> {default, choices}. Values mirror the gateway's own fallbacks:
# PlatformConfig.reply_to_mode defaults to "first", the allow-all bypass is off
# unless explicitly truthy, and the home-channel display name falls back to
# "Home" (see gateway/config.py::_apply_env_overrides). Longer suffixes come
# first so ``*_HOME_CHANNEL_NAME`` isn't swallowed by ``*_HOME_CHANNEL``.
MESSAGING_ENV_CONVENTIONS: dict[str, dict[str, Any]] = {
    "_REPLY_TO_MODE": {"default": "first", "choices": ["off", "first", "all"]},
    "_ALLOW_ALL_USERS": {"default": "false", "choices": ["false", "true"]},
    "_HOME_CHANNEL_THREAD_ID": {},
    "_HOME_CHANNEL_NAME": {"default": "Home"},
    "_HOME_CHANNEL": {},
    "_PROXY": {},
}

# Advanced keys that don't fit a suffix convention. WHATSAPP_ENABLED/_MODE are
# driven by the platform toggle and the bridge's own onboarding, so a user
# typing into them by hand is the exception, not the setup path. Defaults match
# the runtime fallbacks (gateway/platforms/whatsapp_common.py reads
# WHATSAPP_MODE with a "self-chat" default; WHATSAPP_ENABLED is off unless
# explicitly truthy).
MESSAGING_ENV_ADVANCED_KEYS: dict[str, dict[str, Any]] = {
    "WHATSAPP_ENABLED": {"default": "false", "choices": ["false", "true"]},
    "WHATSAPP_MODE": {"default": "self-chat", "choices": ["bot", "self-chat"]},
    # Mattermost's threading knob is spelled _REPLY_MODE (no "TO") and takes a
    # different value set than the _REPLY_TO_MODE family — off/thread, not
    # off/first/all. Listed explicitly so the suffix rule can't mislabel it.
    # Default mirrors plugins/platforms/mattermost/adapter.py.
    "MATTERMOST_REPLY_MODE": {"default": "off", "choices": ["off", "thread"]},
}


def messaging_env_ui_hints(key: str) -> dict[str, Any]:
    """Return ``{advanced, default, choices}`` for a messaging env var.

    ``advanced`` is True for the convenience knobs described in the module
    docstring and False for anything a platform genuinely needs (tokens, URLs,
    allowlists). ``default`` is the empty string when the var has no meaningful
    fallback, and ``choices`` is empty unless the var accepts a fixed set.
    """
    hints: dict[str, Any] = {"advanced": False, "default": "", "choices": []}

    def _apply(meta: dict[str, Any]) -> None:
        # Copy the choices list — ``update`` would alias the module-level table
        # and let one caller's mutation leak into every later lookup.
        hints.update(meta)
        hints["choices"] = list(meta.get("choices", ()))
        hints["advanced"] = True

    explicit = MESSAGING_ENV_ADVANCED_KEYS.get(key)
    if explicit is not None:
        _apply(explicit)
        return hints
    for suffix, meta in MESSAGING_ENV_CONVENTIONS.items():
        if key.endswith(suffix):
            _apply(meta)
            break
    return hints


def describe_default(key: str) -> str:
    """Human-readable "what happens if I leave this blank" for a var.

    Returns an empty string when the var has no documented fallback, so callers
    can omit the hint rather than print a misleading one.
    """
    hints = messaging_env_ui_hints(key)
    default = hints["default"]
    if not default:
        return ""
    choices = hints["choices"]
    if choices:
        return f"default: {default} (options: {', '.join(choices)})"
    return f"default: {default}"
