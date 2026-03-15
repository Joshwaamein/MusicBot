"""
Tests for the _FakeMessage class in musicbot.cogs.music.

_FakeMessage is a lightweight stand-in for discord.Message, used when slash
commands call cmd_* methods that expect a Message parameter. It must:
- Expose the same attributes the on_message handler populates
- Have no-op async methods for delete() and add_reaction()
- Not crash when used by safe_delete_message / safe_edit_message
"""

import asyncio

import discord
import pytest

from musicbot.cogs.music import _FakeMessage

from conftest import make_mock_interaction, make_mock_member


class TestFakeMessageAttributes:
    """Verify _FakeMessage exposes the correct attributes."""

    def test_id_matches_interaction(self):
        interaction = make_mock_interaction()
        msg = _FakeMessage(interaction)
        assert msg.id == interaction.id

    def test_author_is_interaction_user(self):
        member = make_mock_member(user_id=42, name="Alice")
        interaction = make_mock_interaction(user=member)
        msg = _FakeMessage(interaction)
        assert msg.author is member
        assert msg.author.id == 42

    def test_channel_is_interaction_channel(self):
        interaction = make_mock_interaction()
        msg = _FakeMessage(interaction)
        assert msg.channel is interaction.channel

    def test_guild_is_interaction_guild(self):
        interaction = make_mock_interaction()
        msg = _FakeMessage(interaction)
        assert msg.guild is interaction.guild

    def test_content_is_empty_string(self):
        interaction = make_mock_interaction()
        msg = _FakeMessage(interaction)
        assert msg.content == ""

    def test_mentions_is_empty_list(self):
        interaction = make_mock_interaction()
        msg = _FakeMessage(interaction)
        assert msg.mentions == []

    def test_raw_mentions_is_empty_list(self):
        interaction = make_mock_interaction()
        msg = _FakeMessage(interaction)
        assert msg.raw_mentions == []

    def test_raw_channel_mentions_is_empty_list(self):
        interaction = make_mock_interaction()
        msg = _FakeMessage(interaction)
        assert msg.raw_channel_mentions == []


class TestFakeMessageNoOpMethods:
    """Verify that async no-op methods don't raise."""

    @pytest.mark.asyncio
    async def test_delete_is_noop(self):
        interaction = make_mock_interaction()
        msg = _FakeMessage(interaction)
        # Should not raise
        result = await msg.delete()
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_with_delay_is_noop(self):
        interaction = make_mock_interaction()
        msg = _FakeMessage(interaction)
        result = await msg.delete(delay=5.0)
        assert result is None

    @pytest.mark.asyncio
    async def test_add_reaction_is_noop(self):
        interaction = make_mock_interaction()
        msg = _FakeMessage(interaction)
        result = await msg.add_reaction("👍")
        assert result is None


class TestFakeMessageEdgeCases:
    """Edge cases and robustness tests."""

    def test_different_interactions_produce_different_messages(self):
        i1 = make_mock_interaction()
        i1.id = 111
        i2 = make_mock_interaction()
        i2.id = 222

        m1 = _FakeMessage(i1)
        m2 = _FakeMessage(i2)

        assert m1.id != m2.id
        assert m1.id == 111
        assert m2.id == 222

    def test_guild_can_be_none(self):
        """If interaction.guild is None (DM context), FakeMessage should handle it."""
        interaction = make_mock_interaction()
        interaction.guild = None
        msg = _FakeMessage(interaction)
        assert msg.guild is None
