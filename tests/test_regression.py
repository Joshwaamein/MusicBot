"""
Regression tests to prevent previously-fixed bugs from recurring.

These tests verify:
- No get_player(create=True) in slash commands (caused broken voice)
- Input validation functions work correctly
- New /restart and /reboot commands are registered
"""

import pytest

from musicbot.cogs.music import (
    _validate_song_input,
    _validate_url,
    _validate_search_query,
    _validate_seek_time,
    _validate_speed,
    MAX_SONG_QUERY_LEN,
    MAX_SEARCH_QUERY_LEN,
    MAX_URL_LEN,
    SPEED_MIN,
    SPEED_MAX,
)


class TestNoCreateTrueRegression:
    """
    Regression test: slash commands must NOT use get_player(create=True).
    This bypasses cmd_summon and causes 'Not connected to voice' errors.
    """

    def test_no_create_true_in_cog(self):
        import inspect
        from musicbot.cogs.music import setup

        source = inspect.getsource(setup)
        assert "create=True" not in source, (
            "REGRESSION: Found 'create=True' in music.py cog. "
            "Slash commands must NOT call get_player(create=True). "
            "Let _cmd_play handle summon via its built-in cmd_summon logic."
        )


class TestValidateSongInput:
    """Test _validate_song_input."""

    def test_valid_song(self):
        assert _validate_song_input("bohemian rhapsody") == "bohemian rhapsody"

    def test_strips_whitespace(self):
        assert _validate_song_input("  hello  ") == "hello"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_song_input("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_song_input("   ")

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="too long"):
            _validate_song_input("x" * (MAX_SONG_QUERY_LEN + 1))

    def test_max_length_ok(self):
        result = _validate_song_input("x" * MAX_SONG_QUERY_LEN)
        assert len(result) == MAX_SONG_QUERY_LEN


class TestValidateUrl:
    """Test _validate_url."""

    def test_valid_https(self):
        assert _validate_url("https://youtube.com/watch?v=abc") == "https://youtube.com/watch?v=abc"

    def test_valid_http(self):
        assert _validate_url("http://example.com") == "http://example.com"

    def test_valid_spotify(self):
        assert _validate_url("spotify:track:abc123") == "spotify:track:abc123"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_url("")

    def test_invalid_protocol_raises(self):
        with pytest.raises(ValueError, match="must start with"):
            _validate_url("ftp://example.com")

    def test_no_protocol_raises(self):
        with pytest.raises(ValueError, match="must start with"):
            _validate_url("youtube.com/watch?v=abc")

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="too long"):
            _validate_url("https://x.com/" + "a" * MAX_URL_LEN)


class TestValidateSearchQuery:
    """Test _validate_search_query."""

    def test_valid_query(self):
        assert _validate_search_query("lofi beats") == "lofi beats"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_search_query("")

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="too long"):
            _validate_search_query("x" * (MAX_SEARCH_QUERY_LEN + 1))


class TestValidateSeekTime:
    """Test _validate_seek_time."""

    def test_seconds(self):
        assert _validate_seek_time("90") == "90"

    def test_minutes_seconds(self):
        assert _validate_seek_time("1:30") == "1:30"

    def test_positive_offset(self):
        assert _validate_seek_time("+30") == "+30"

    def test_negative_offset(self):
        assert _validate_seek_time("-15") == "-15"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid time"):
            _validate_seek_time("abc")

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="Invalid time"):
            _validate_seek_time("")


class TestValidateSpeed:
    """Test _validate_speed."""

    def test_normal_speed(self):
        assert _validate_speed(1.0) == 1.0

    def test_min_speed(self):
        assert _validate_speed(SPEED_MIN) == SPEED_MIN

    def test_max_speed(self):
        assert _validate_speed(SPEED_MAX) == SPEED_MAX

    def test_below_min_raises(self):
        with pytest.raises(ValueError, match="between"):
            _validate_speed(0.1)

    def test_above_max_raises(self):
        with pytest.raises(ValueError, match="between"):
            _validate_speed(200.0)


class TestNewCommandsRegistered:
    """Verify /restart and /reboot are registered."""

    @pytest.mark.asyncio
    async def test_restart_command_registered(self):
        from unittest.mock import MagicMock
        from discord import app_commands
        from conftest import make_mock_bot
        from musicbot.cogs.music import setup

        mock_client = MagicMock()
        mock_client.application_id = None
        mock_client._connection._command_tree = None
        tree = app_commands.CommandTree(mock_client)
        bot = make_mock_bot()
        bot.tree = tree

        await setup(bot)

        cmd_names = [c.name for c in tree.get_commands()]
        assert "restart" in cmd_names, f"restart not found in: {cmd_names}"

    @pytest.mark.asyncio
    async def test_reboot_command_registered(self):
        from unittest.mock import MagicMock
        from discord import app_commands
        from conftest import make_mock_bot
        from musicbot.cogs.music import setup

        mock_client = MagicMock()
        mock_client.application_id = None
        mock_client._connection._command_tree = None
        tree = app_commands.CommandTree(mock_client)
        bot = make_mock_bot()
        bot.tree = tree

        await setup(bot)

        cmd_names = [c.name for c in tree.get_commands()]
        assert "reboot" in cmd_names, f"reboot not found in: {cmd_names}"

    @pytest.mark.asyncio
    async def test_total_commands_is_22(self):
        """We should now have 22 commands (20 original + restart + reboot)."""
        from unittest.mock import MagicMock
        from discord import app_commands
        from conftest import make_mock_bot
        from musicbot.cogs.music import setup

        mock_client = MagicMock()
        mock_client.application_id = None
        mock_client._connection._command_tree = None
        tree = app_commands.CommandTree(mock_client)
        bot = make_mock_bot()
        bot.tree = tree

        await setup(bot)

        assert len(tree.get_commands()) == 22
