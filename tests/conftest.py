"""
Shared test fixtures for MusicBot slash command tests.

These fixtures create mock objects that simulate Discord's API
without requiring a real connection or bot token.
"""

import asyncio
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import discord
import pytest


# ── Mock Factories ──────────────────────────────────────────────────────────


def make_mock_member(
    user_id: int = 123456789,
    name: str = "TestUser",
    in_voice: bool = True,
) -> MagicMock:
    """Create a mock discord.Member, optionally in a voice channel."""
    member = MagicMock(spec=discord.Member)
    member.id = user_id
    member.name = name
    member.display_name = name
    member.mention = f"<@{user_id}>"

    if in_voice:
        voice_state = MagicMock()
        voice_channel = MagicMock(spec=discord.VoiceChannel)
        voice_channel.id = 999888777
        voice_channel.name = "General"
        voice_channel.guild = MagicMock(spec=discord.Guild)
        voice_state.channel = voice_channel
        member.voice = voice_state
    else:
        member.voice = None

    return member


def make_mock_interaction(
    user: Optional[MagicMock] = None,
    guild: Optional[MagicMock] = None,
) -> MagicMock:
    """Create a mock discord.Interaction with response and followup."""
    interaction = MagicMock(spec=discord.Interaction)
    interaction.id = 111222333444

    # User
    interaction.user = user or make_mock_member()

    # Guild
    if guild is None:
        guild = MagicMock(spec=discord.Guild)
        guild.id = 555666777888
        guild.name = "TestGuild"
        guild.me = MagicMock(spec=discord.Member)
        guild.me.voice = None
    interaction.guild = guild

    # Channel
    channel = MagicMock()
    channel.id = 444555666
    channel.name = "bot-commands"
    interaction.channel = channel

    # Response (for defer / send_message)
    interaction.response = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()

    # Followup (for post-defer messages)
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()

    return interaction


def make_mock_bot() -> MagicMock:
    """
    Create a mock MusicBot with the minimum attributes needed
    for slash command tests.
    """
    bot = MagicMock()

    # Config
    bot.config = MagicMock()
    bot.config.embeds = True
    bot.config.owner_id = 146710156439322624

    # Permissions
    perm_group = MagicMock()
    perm_group.instaskip = True
    bot.permissions = MagicMock()
    bot.permissions.for_user = MagicMock(return_value=perm_group)

    # Command tree
    bot.tree = MagicMock(spec=discord.app_commands.CommandTree)
    bot.tree.command = MagicMock()
    bot.tree.get_commands = MagicMock(return_value=[])

    # Player methods
    bot.get_player_in = MagicMock(return_value=None)
    bot.get_player = AsyncMock(return_value=MagicMock())

    # Embed generation
    embed = MagicMock(spec=discord.Embed)
    embed.title = ""
    embed.description = ""
    bot._gen_embed = MagicMock(return_value=embed)

    return bot


# ── Pytest Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def mock_member():
    """A mock discord.Member in a voice channel."""
    return make_mock_member()


@pytest.fixture
def mock_member_no_voice():
    """A mock discord.Member NOT in a voice channel."""
    return make_mock_member(in_voice=False)


@pytest.fixture
def mock_interaction(mock_member):
    """A mock discord.Interaction with a member in voice."""
    return make_mock_interaction(user=mock_member)


@pytest.fixture
def mock_interaction_no_voice(mock_member_no_voice):
    """A mock discord.Interaction with a member NOT in voice."""
    return make_mock_interaction(user=mock_member_no_voice)


@pytest.fixture
def mock_bot():
    """A mock MusicBot instance."""
    return make_mock_bot()
