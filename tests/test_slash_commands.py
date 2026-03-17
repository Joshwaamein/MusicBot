"""
Tests for slash command registration in musicbot.cogs.music.

The setup() function registers 20 slash commands on bot.tree.
We verify:
- All expected commands are registered
- Commands have the correct names and descriptions
- @guild_only() is applied (no DM usage)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import discord
from discord import app_commands
import pytest

from conftest import make_mock_bot


# All 20 expected slash command names
EXPECTED_COMMANDS = sorted([
    "autoplaylist",
    "blocksong",
    "blockuser",
    "botlatency",
    "botversion",
    "cache",
    "clean",
    "clear",
    "config",
    "disconnect",
    "follow",
    "help",
    "id",
    "joinserver",
    "karaoke",
    "latency",
    "leaveserver",
    "listids",
    "np",
    "option",
    "pause",
    "perms",
    "play",
    "playnext",
    "playnow",
    "pldump",
    "queue",
    "reboot",
    "repeat",
    "resetplaylist",
    "restart",
    "resume",
    "search",
    "seek",
    "setavatar",
    "setname",
    "setnick",
    "setperms",
    "setprefix",
    "shuffle",
    "shuffleplay",
    "skip",
    "speed",
    "stream",
    "summon",
    "uptime",
    "volume",
])


def _make_tree_with_bot():
    """
    Create a real CommandTree attached to a mock bot.

    CommandTree.__init__ needs client.http and client._connection._command_tree.
    We use MagicMock without spec (so .http auto-creates) but must explicitly
    set _connection._command_tree = None so CommandTree doesn't think one
    already exists.
    """
    mock_client = MagicMock()
    mock_client.application_id = None
    mock_client._connection._command_tree = None
    tree = app_commands.CommandTree(mock_client)

    bot = make_mock_bot()
    bot.tree = tree

    return bot, tree


class TestSetupRegistration:
    """Verify that setup() registers all expected commands."""

    @pytest.mark.asyncio
    async def test_setup_registers_commands(self):
        """
        setup() should call @bot.tree.command() to register each slash command.
        We use a real CommandTree to verify the commands are actually registered.
        """
        bot, tree = _make_tree_with_bot()

        from musicbot.cogs.music import setup
        await setup(bot)

        registered = sorted([cmd.name for cmd in tree.get_commands()])

        assert registered == EXPECTED_COMMANDS, (
            f"Expected {len(EXPECTED_COMMANDS)} commands, got {len(registered)}.\n"
            f"Missing: {set(EXPECTED_COMMANDS) - set(registered)}\n"
            f"Extra: {set(registered) - set(EXPECTED_COMMANDS)}"
        )

    @pytest.mark.asyncio
    async def test_setup_registers_exactly_47_commands(self):
        bot, tree = _make_tree_with_bot()

        from musicbot.cogs.music import setup
        await setup(bot)

        assert len(tree.get_commands()) == 47


class TestCommandDescriptions:
    """Verify all commands have non-empty descriptions."""

    @pytest.mark.asyncio
    async def test_all_commands_have_descriptions(self):
        bot, tree = _make_tree_with_bot()

        from musicbot.cogs.music import setup
        await setup(bot)

        for cmd in tree.get_commands():
            assert cmd.description, f"Command /{cmd.name} has no description"
            assert len(cmd.description) > 5, (
                f"Command /{cmd.name} description too short: '{cmd.description}'"
            )


class TestCommandParameters:
    """Verify key commands have the expected parameters."""

    @pytest.mark.asyncio
    async def test_play_has_song_parameter(self):
        bot, tree = _make_tree_with_bot()

        from musicbot.cogs.music import setup
        await setup(bot)

        play_cmd = next(c for c in tree.get_commands() if c.name == "play")
        param_names = [p.name for p in play_cmd.parameters]
        assert "song" in param_names, f"play params: {param_names}"

    @pytest.mark.asyncio
    async def test_volume_has_optional_level_parameter(self):
        bot, tree = _make_tree_with_bot()

        from musicbot.cogs.music import setup
        await setup(bot)

        vol_cmd = next(c for c in tree.get_commands() if c.name == "volume")
        param_names = [p.name for p in vol_cmd.parameters]
        assert "level" in param_names

        level_param = next(p for p in vol_cmd.parameters if p.name == "level")
        assert not level_param.required, "volume 'level' should be optional"

    @pytest.mark.asyncio
    async def test_skip_has_optional_force_parameter(self):
        bot, tree = _make_tree_with_bot()

        from musicbot.cogs.music import setup
        await setup(bot)

        skip_cmd = next(c for c in tree.get_commands() if c.name == "skip")
        param_names = [p.name for p in skip_cmd.parameters]
        assert "force" in param_names

        force_param = next(p for p in skip_cmd.parameters if p.name == "force")
        assert not force_param.required, "skip 'force' should be optional"

    @pytest.mark.asyncio
    async def test_repeat_has_mode_choices(self):
        bot, tree = _make_tree_with_bot()

        from musicbot.cogs.music import setup
        await setup(bot)

        repeat_cmd = next(c for c in tree.get_commands() if c.name == "repeat")
        mode_param = next(p for p in repeat_cmd.parameters if p.name == "mode")
        assert mode_param.choices, "repeat 'mode' should have choices"
        choice_values = [c.value for c in mode_param.choices]
        assert "song" in choice_values
        assert "all" in choice_values
        assert "on" in choice_values
        assert "off" in choice_values

    @pytest.mark.asyncio
    async def test_search_has_query_and_service(self):
        bot, tree = _make_tree_with_bot()

        from musicbot.cogs.music import setup
        await setup(bot)

        search_cmd = next(c for c in tree.get_commands() if c.name == "search")
        param_names = [p.name for p in search_cmd.parameters]
        assert "query" in param_names
        assert "service" in param_names

    @pytest.mark.asyncio
    async def test_seek_has_time_parameter(self):
        bot, tree = _make_tree_with_bot()

        from musicbot.cogs.music import setup
        await setup(bot)

        seek_cmd = next(c for c in tree.get_commands() if c.name == "seek")
        param_names = [p.name for p in seek_cmd.parameters]
        assert "time" in param_names

    @pytest.mark.asyncio
    async def test_speed_has_rate_parameter(self):
        bot, tree = _make_tree_with_bot()

        from musicbot.cogs.music import setup
        await setup(bot)

        speed_cmd = next(c for c in tree.get_commands() if c.name == "speed")
        param_names = [p.name for p in speed_cmd.parameters]
        assert "rate" in param_names


class TestGuildOnlyEnforcement:
    """Verify commands that require a guild context are guild_only."""

    @pytest.mark.asyncio
    async def test_all_commands_are_guild_only(self):
        """Every registered slash command should be guild-only."""
        bot, tree = _make_tree_with_bot()

        from musicbot.cogs.music import setup
        await setup(bot)

        for cmd in tree.get_commands():
            assert cmd.guild_only, (
                f"Command /{cmd.name} is NOT guild_only — "
                "all MusicBot commands should be guild-only"
            )
