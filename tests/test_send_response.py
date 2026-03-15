"""
Tests for the _send_response helper in musicbot.cogs.music.

_send_response converts a cmd_* method's Response object into an appropriate
interaction followup message. It must handle:
- None / non-Response objects → ephemeral "Done" message
- Text content with embeds enabled → embed followup
- Text content with embeds disabled → plain text followup
- discord.Embed content → embed followup directly
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from musicbot.constructs import Response
from musicbot.cogs.music import _send_response

from conftest import make_mock_bot, make_mock_interaction


class TestSendResponseNoneInput:
    """When response is None or not a Response, send ephemeral Done."""

    @pytest.mark.asyncio
    async def test_none_response_sends_done(self):
        interaction = make_mock_interaction()
        bot = make_mock_bot()

        await _send_response(interaction, bot, None, "test")

        interaction.followup.send.assert_called_once()
        call_kwargs = interaction.followup.send.call_args
        assert "Done" in str(call_kwargs)
        assert call_kwargs.kwargs.get("ephemeral") is True

    @pytest.mark.asyncio
    async def test_non_response_object_sends_done(self):
        interaction = make_mock_interaction()
        bot = make_mock_bot()

        await _send_response(interaction, bot, "just a string", "test")

        interaction.followup.send.assert_called_once()
        call_kwargs = interaction.followup.send.call_args
        assert call_kwargs.kwargs.get("ephemeral") is True


class TestSendResponseTextContent:
    """When response has text content, behaviour depends on bot.config.embeds."""

    @pytest.mark.asyncio
    async def test_text_with_embeds_enabled(self):
        """With embeds enabled, should send an embed with description."""
        interaction = make_mock_interaction()
        bot = make_mock_bot()
        bot.config.embeds = True

        response = Response("Now playing: Bohemian Rhapsody")

        await _send_response(interaction, bot, response, "play")

        interaction.followup.send.assert_called_once()
        call_kwargs = interaction.followup.send.call_args
        # Should have called with embed= keyword
        assert "embed" in call_kwargs.kwargs
        # Should have set the title on the embed
        bot._gen_embed.assert_called_once()

    @pytest.mark.asyncio
    async def test_text_with_embeds_disabled(self):
        """With embeds disabled, should send plain text."""
        interaction = make_mock_interaction()
        bot = make_mock_bot()
        bot.config.embeds = False

        response = Response("Volume set to 50%")

        await _send_response(interaction, bot, response, "volume")

        interaction.followup.send.assert_called_once()
        call_args = interaction.followup.send.call_args
        # First positional arg should be the text
        assert "Volume set to 50%" in str(call_args)
        # Should NOT have embed kwarg
        assert "embed" not in call_args.kwargs


class TestSendResponseEmbedContent:
    """When response contains a discord.Embed directly."""

    @pytest.mark.asyncio
    async def test_embed_content_sent_directly(self):
        """A Response with an Embed as content should send the embed as-is."""
        interaction = make_mock_interaction()
        bot = make_mock_bot()

        embed = discord.Embed(title="Queue", description="Song 1\nSong 2")
        response = Response(embed)

        await _send_response(interaction, bot, response, "queue")

        interaction.followup.send.assert_called_once()
        call_kwargs = interaction.followup.send.call_args
        assert call_kwargs.kwargs.get("embed") is embed


class TestSendResponseCommandName:
    """The command_name parameter should be used as the embed title."""

    @pytest.mark.asyncio
    async def test_command_name_becomes_embed_title(self):
        interaction = make_mock_interaction()
        bot = make_mock_bot()
        bot.config.embeds = True

        mock_embed = MagicMock(spec=discord.Embed)
        mock_embed.title = ""
        mock_embed.description = ""
        bot._gen_embed = MagicMock(return_value=mock_embed)

        response = Response("Shuffled the queue!")

        await _send_response(interaction, bot, response, "shuffle")

        # The embed's title should be set to the command name
        assert mock_embed.title == "shuffle"

    @pytest.mark.asyncio
    async def test_empty_command_name_uses_default(self):
        interaction = make_mock_interaction()
        bot = make_mock_bot()
        bot.config.embeds = True

        mock_embed = MagicMock(spec=discord.Embed)
        mock_embed.title = ""
        mock_embed.description = ""
        bot._gen_embed = MagicMock(return_value=mock_embed)

        response = Response("Something happened")

        await _send_response(interaction, bot, response, "")

        # Empty command name should fall back to "MusicBot"
        assert mock_embed.title == "MusicBot"
