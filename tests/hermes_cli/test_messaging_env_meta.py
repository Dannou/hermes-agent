"""Contract tests for the shared messaging env-var UI metadata.

These pin *relationships* (a required credential is never advanced; a published
default is one the runtime actually uses), not a snapshot of the table — adding
a platform or a knob should not break them.
"""

import pytest

from hermes_cli.messaging_env_meta import (
    MESSAGING_ENV_ADVANCED_KEYS,
    MESSAGING_ENV_CONVENTIONS,
    describe_default,
    messaging_env_ui_hints,
)


class TestMessagingEnvUiHints:
    def test_credential_shaped_vars_are_never_advanced(self):
        """Tokens/URLs/allowlists must stay in the primary form.

        Surfaces collapse or skip `advanced` fields, so tagging a required
        credential advanced would hide the one field the platform can't
        start without.
        """
        for key in (
            "DISCORD_BOT_TOKEN",
            "TELEGRAM_BOT_TOKEN",
            "SLACK_BOT_TOKEN",
            "SLACK_APP_TOKEN",
            "MATTERMOST_URL",
            "MATTERMOST_TOKEN",
            "DISCORD_ALLOWED_USERS",
            "SLACK_ALLOWED_USERS",
        ):
            assert messaging_env_ui_hints(key)["advanced"] is False, key

    def test_convention_suffixes_mark_knobs_advanced(self):
        for key in (
            "DISCORD_REPLY_TO_MODE",
            "DISCORD_ALLOW_ALL_USERS",
            "DISCORD_HOME_CHANNEL",
            "DISCORD_HOME_CHANNEL_NAME",
            "TELEGRAM_PROXY",
        ):
            assert messaging_env_ui_hints(key)["advanced"] is True, key

    def test_convention_applies_to_unenumerated_plugin_platforms(self):
        """Suffix matching is the point: plugins get this without a code change.

        IRC/SimpleX/LINE ship their own env vars and are never named in the
        table; they must still be classified correctly.
        """
        for key in (
            "IRC_ALLOW_ALL_USERS",
            "SIMPLEX_HOME_CHANNEL",
            "LINE_ALLOW_ALL_USERS",
            "NTFY_HOME_CHANNEL_NAME",
        ):
            assert messaging_env_ui_hints(key)["advanced"] is True, key

    def test_longer_suffix_wins_over_shorter_prefix_of_it(self):
        """`*_HOME_CHANNEL_NAME` must not be swallowed by `*_HOME_CHANNEL`.

        The name has a real default ("Home"); the ID has none. Matching the
        shorter suffix first would drop the default and show an empty hint.
        """
        assert messaging_env_ui_hints("DISCORD_HOME_CHANNEL_NAME")["default"] == "Home"
        assert messaging_env_ui_hints("DISCORD_HOME_CHANNEL")["default"] == ""

    def test_every_published_default_is_among_its_choices(self):
        """A picker whose default isn't selectable is a broken picker."""
        for table in (MESSAGING_ENV_CONVENTIONS, MESSAGING_ENV_ADVANCED_KEYS):
            for key, meta in table.items():
                choices = meta.get("choices")
                if choices:
                    assert meta.get("default") in choices, key

    def test_hint_shape_is_stable_for_unknown_keys(self):
        hints = messaging_env_ui_hints("SOME_UNRELATED_SETTING")
        assert hints == {"advanced": False, "default": "", "choices": []}

    def test_callers_cannot_mutate_the_shared_tables(self):
        """Hints are handed out per-call; a caller editing one must not poison
        the table for every later caller."""
        first = messaging_env_ui_hints("DISCORD_REPLY_TO_MODE")
        first["choices"].append("bogus")
        first["default"] = "bogus"
        second = messaging_env_ui_hints("DISCORD_REPLY_TO_MODE")
        assert "bogus" not in second["choices"]
        assert second["default"] == "first"


class TestRuntimeAgreement:
    def test_reply_mode_default_matches_gateway_platform_config(self):
        """Displaying a default the gateway doesn't use is worse than silence."""
        from gateway.config import PlatformConfig

        assert (
            messaging_env_ui_hints("DISCORD_REPLY_TO_MODE")["default"]
            == PlatformConfig().reply_to_mode
        )

    def test_mattermost_reply_mode_is_not_confused_with_reply_to_mode(self):
        """MATTERMOST_REPLY_MODE is a different knob: off/thread, not off/first/all.

        It ends in `_REPLY_MODE`, so a careless suffix rule would hand it the
        wrong value set and a default it does not accept.
        """
        hints = messaging_env_ui_hints("MATTERMOST_REPLY_MODE")
        assert hints["choices"] == ["off", "thread"]
        assert hints["default"] == "off"


class TestDescribeDefault:
    def test_describes_choices_when_the_var_has_a_fixed_set(self):
        text = describe_default("DISCORD_REPLY_TO_MODE")
        assert "first" in text
        assert "off" in text and "all" in text

    def test_describes_a_bare_default_without_inventing_choices(self):
        assert describe_default("DISCORD_HOME_CHANNEL_NAME") == "default: Home"

    def test_is_empty_when_there_is_no_documented_default(self):
        """Callers omit the hint entirely rather than print something false."""
        assert describe_default("DISCORD_HOME_CHANNEL") == ""
        assert describe_default("DISCORD_BOT_TOKEN") == ""


class TestCliWizardSkipsAdvancedByDefault:
    """The `hermes setup gateway` wizard must ask only what's required.

    Drives the real `_setup_standard_platform` with scripted stdin against a
    temp HERMES_HOME and asserts on the .env it actually writes.
    """

    @pytest.fixture
    def wizard_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        return tmp_path

    def _run(self, answers, monkeypatch):
        import io

        from hermes_cli import gateway as gw

        platform = next(p for p in gw._PLATFORMS if p["key"] == "mattermost")
        monkeypatch.setattr("sys.stdin", io.StringIO("\n".join(answers) + "\n"))
        gw._setup_standard_platform(dict(platform))

    def _written(self, home):
        env_file = home / ".env"
        if not env_file.exists():
            return {}
        out = {}
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k] = v
        return out

    BASE = ["https://mm.example.com", "tok-abc", "user26charidabcdefghijklmn"]

    def test_declining_advanced_writes_only_required_values(
        self, wizard_env, monkeypatch, capsys
    ):
        self._run(self.BASE + ["n"], monkeypatch)
        written = self._written(wizard_env)

        assert written.get("MATTERMOST_URL") == "https://mm.example.com"
        assert written.get("MATTERMOST_TOKEN") == "tok-abc"
        # The knobs are neither asked about individually nor written.
        assert "MATTERMOST_HOME_CHANNEL" not in written
        assert "MATTERMOST_REPLY_MODE" not in written

        out = capsys.readouterr().out
        # ...but the user is told what the defaults are and how to change them.
        assert "optional setting" in out
        assert "default: off" in out

    def test_opting_in_still_reaches_every_advanced_knob(
        self, wizard_env, monkeypatch
    ):
        self._run(self.BASE + ["y", "chan-xyz", "thread"], monkeypatch)
        written = self._written(wizard_env)

        assert written.get("MATTERMOST_HOME_CHANNEL") == "chan-xyz"
        assert written.get("MATTERMOST_REPLY_MODE") == "thread"

    def test_blank_advanced_answer_does_not_write_an_empty_value(
        self, wizard_env, monkeypatch
    ):
        """An empty string in .env is not the same as unset — it can shadow
        the default the user was told they'd get."""
        self._run(self.BASE + ["y", "", ""], monkeypatch)
        written = self._written(wizard_env)

        assert "MATTERMOST_HOME_CHANNEL" not in written
        assert "MATTERMOST_REPLY_MODE" not in written

    def test_required_token_still_gates_setup(self, wizard_env, monkeypatch):
        """Proves the token wasn't swept into the advanced bucket."""
        self._run(["https://mm.example.com", ""], monkeypatch)
        written = self._written(wizard_env)

        assert "MATTERMOST_TOKEN" not in written
