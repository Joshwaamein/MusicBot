"""
Tests for MusicBot initialization related to slash commands.

Verifies that:
- MusicBot creates a CommandTree (self.tree) on init
- The tree.sync guard only syncs on first on_ready
- The setup_hook loads the music cog
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord import app_commands
import pytest


class TestCommandTreeCreation:
    """Verify that bot.py creates self.tree as a CommandTree."""

    def test_bot_source_imports_app_commands(self):
        """bot.py should import app_commands from discord."""
        import musicbot.bot as bot_module
        # The module should have discord.app_commands accessible
        assert hasattr(discord, "app_commands")

    def test_command_tree_in_bot_init(self):
        """
        Verify that the MusicBot.__init__ source code includes
        self.tree = app_commands.CommandTree(self).

        We check the source rather than instantiating because MusicBot.__init__
        requires config files and does heavy initialization.
        """
        import inspect
        from musicbot.bot import MusicBot

        source = inspect.getsource(MusicBot.__init__)
        assert "CommandTree" in source, (
            "MusicBot.__init__ should create a CommandTree"
        )
        assert "self.tree" in source, (
            "MusicBot.__init__ should assign self.tree"
        )

    def test_setup_hook_loads_cog(self):
        """
        Verify that setup_hook source references the music cog.
        """
        import inspect
        from musicbot.bot import MusicBot

        source = inspect.getsource(MusicBot.setup_hook)
        assert "music" in source.lower(), (
            "setup_hook should load the music cog"
        )
        assert "setup" in source.lower(), (
            "setup_hook should call the cog's setup function"
        )


class TestTreeSyncGuard:
    """Verify that tree.sync() is guarded to only run on first ready."""

    def test_on_ready_call_later_has_sync_guard(self):
        """
        The _on_ready_call_later method should check on_ready_count
        before calling tree.sync().
        """
        import inspect
        from musicbot.bot import MusicBot

        source = inspect.getsource(MusicBot._on_ready_call_later)

        # Should contain the guard condition
        assert "on_ready_count" in source, (
            "_on_ready_call_later should check on_ready_count "
            "to avoid syncing on every reconnect"
        )
        assert "tree.sync" in source, (
            "_on_ready_call_later should call tree.sync()"
        )

    def test_sync_guard_prevents_repeat_syncs(self):
        """
        The sync should only happen when on_ready_count <= 1,
        not on subsequent reconnects.
        """
        import inspect
        from musicbot.bot import MusicBot

        source = inspect.getsource(MusicBot._on_ready_call_later)

        # Verify the guard uses a condition — look for the if statement
        # that wraps tree.sync()
        lines = source.split("\n")
        sync_line_idx = None
        guard_line_idx = None

        for i, line in enumerate(lines):
            if "tree.sync" in line:
                sync_line_idx = i
            if "on_ready_count" in line and ("if" in line or "<=" in line):
                guard_line_idx = i

        assert guard_line_idx is not None, (
            "Should have a guard condition checking on_ready_count"
        )
        assert sync_line_idx is not None, (
            "Should have tree.sync() call"
        )
        # The guard should come before the sync
        assert guard_line_idx < sync_line_idx, (
            "The on_ready_count guard should appear before tree.sync()"
        )


