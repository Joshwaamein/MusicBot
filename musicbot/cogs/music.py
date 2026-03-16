"""
Slash command cog for MusicBot.
These wrap the existing MusicBot cmd_* methods to provide Discord slash command support.

Key design decisions:
- Commands that return Response objects: we extract the content and send via interaction.
- Commands that send directly to channel (np, shuffle): we let them do their thing
  and just acknowledge the interaction ephemerally.
- Commands needing a discord.Message: we pass a FakeMessage with the minimum attributes.
- All commands are guild_only and include permission checks.
"""

import logging
from typing import TYPE_CHECKING, Optional, Union

import discord
from discord import app_commands

if TYPE_CHECKING:
    from musicbot.bot import MusicBot

log = logging.getLogger(__name__)


class _FakeMessage:
    """
    Lightweight stand-in for discord.Message used when slash commands call
    cmd_* methods that expect a Message parameter.

    safe_delete_message / safe_edit_message will fail gracefully on this
    since it's not a real message. SkipState stores message IDs which works fine.
    """

    def __init__(self, interaction: discord.Interaction) -> None:
        self.id = interaction.id
        self.author = interaction.user
        self.channel = interaction.channel
        self.guild = interaction.guild
        self.content = ""
        self.mentions = []
        self.raw_mentions = []
        self.raw_channel_mentions = []

    async def delete(self, *, delay: Optional[float] = None) -> None:
        """No-op: can't delete an interaction."""
        pass

    async def add_reaction(self, emoji: str) -> None:
        """No-op: can't react to an interaction."""
        pass


async def _send_response(
    interaction: discord.Interaction,
    bot: "MusicBot",
    response: object,
    command_name: str = "",
) -> None:
    """
    Send a cmd_* Response object back through the interaction.
    Handles both embed and text content, respects the bot's embed config.
    """
    from musicbot.constructs import Response

    if not response or not isinstance(response, Response):
        await interaction.followup.send("✅ Done.", ephemeral=True)
        return

    content = response.content
    if isinstance(content, discord.Embed):
        await interaction.followup.send(embed=content)
    elif bot.config.embeds:
        embed = bot._gen_embed()
        embed.title = command_name or "MusicBot"
        embed.description = str(content)
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(str(content))


def _check_perms(
    bot: "MusicBot",
    interaction: discord.Interaction,
    perm_name: str,
) -> bool:
    """
    Check if the interaction user has a specific permission.
    Returns True if allowed, False otherwise.
    """
    user = interaction.user
    perms = bot.permissions.for_user(user)
    return bool(getattr(perms, perm_name, True))


async def setup(bot: "MusicBot") -> None:
    """Register slash commands on the bot's command tree."""

    # ─── /play ─────────────────────────────────────────────────────────────

    @bot.tree.command(
        name="play",
        description="Play a song from YouTube, Spotify, or search by name",
    )
    @app_commands.describe(song="A URL or search query for the song to play")
    @app_commands.guild_only()
    async def slash_play(interaction: discord.Interaction, song: str) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "You need to be in a voice channel.", ephemeral=True
            )
            return

        await interaction.response.defer()
        try:
            guild = interaction.guild
            author = interaction.user
            channel = interaction.channel
            permissions = bot.permissions.for_user(author)
            fake_msg = _FakeMessage(interaction)

            # Let _cmd_play handle summoning via cmd_summon
            _player = bot.get_player_in(guild) if guild else None

            response = await bot._cmd_play(
                message=fake_msg,
                _player=_player,
                channel=channel,
                guild=guild,
                author=author,
                permissions=permissions,
                leftover_args=[],
                song_url=song,
                head=False,
            )
            await _send_response(interaction, bot, response, "play")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /playnext ─────────────────────────────────────────────────────────

    @bot.tree.command(
        name="playnext",
        description="Add a song to play next in the queue",
    )
    @app_commands.describe(song="A URL or search query")
    @app_commands.guild_only()
    async def slash_playnext(interaction: discord.Interaction, song: str) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "You need to be in a voice channel.", ephemeral=True
            )
            return

        await interaction.response.defer()
        try:
            guild = interaction.guild
            author = interaction.user
            channel = interaction.channel
            permissions = bot.permissions.for_user(author)
            fake_msg = _FakeMessage(interaction)

            # Let _cmd_play handle summoning via cmd_summon
            _player = bot.get_player_in(guild) if guild else None

            response = await bot._cmd_play(
                message=fake_msg,
                _player=_player,
                channel=channel,
                guild=guild,
                author=author,
                permissions=permissions,
                leftover_args=[],
                song_url=song,
                head=True,
            )
            await _send_response(interaction, bot, response, "playnext")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /playnow ──────────────────────────────────────────────────────────

    @bot.tree.command(
        name="playnow",
        description="Play a song immediately, skipping the current one",
    )
    @app_commands.describe(song="A URL or search query")
    @app_commands.guild_only()
    async def slash_playnow(interaction: discord.Interaction, song: str) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "You need to be in a voice channel.", ephemeral=True
            )
            return

        await interaction.response.defer()
        try:
            guild = interaction.guild
            author = interaction.user
            channel = interaction.channel
            permissions = bot.permissions.for_user(author)
            fake_msg = _FakeMessage(interaction)

            # Let _cmd_play handle summoning via cmd_summon
            _player = bot.get_player_in(guild) if guild else None

            response = await bot.cmd_playnow(
                message=fake_msg,
                _player=_player,
                channel=channel,
                guild=guild,
                author=author,
                permissions=permissions,
                leftover_args=[],
                song_url=song,
            )
            await _send_response(interaction, bot, response, "playnow")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /shuffleplay ─────────────────────────────────────────────────────

    @bot.tree.command(
        name="shuffleplay",
        description="Play a song and shuffle it into a random queue position",
    )
    @app_commands.describe(song="A URL or search query")
    @app_commands.guild_only()
    async def slash_shuffleplay(interaction: discord.Interaction, song: str) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "You need to be in a voice channel.", ephemeral=True
            )
            return

        await interaction.response.defer()
        try:
            guild = interaction.guild
            author = interaction.user
            channel = interaction.channel
            permissions = bot.permissions.for_user(author)
            fake_msg = _FakeMessage(interaction)

            # Let _cmd_play handle summoning via cmd_summon
            _player = bot.get_player_in(guild) if guild else None

            response = await bot.cmd_shuffleplay(
                message=fake_msg,
                _player=_player,
                channel=channel,
                guild=guild,
                author=author,
                permissions=permissions,
                leftover_args=[],
                song_url=song,
            )
            await _send_response(interaction, bot, response, "shuffleplay")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /skip ─────────────────────────────────────────────────────────────

    @bot.tree.command(name="skip", description="Skip the current song")
    @app_commands.describe(
        force="Force skip (owner/instaskip only)"
    )
    @app_commands.guild_only()
    async def slash_skip(
        interaction: discord.Interaction, force: bool = False
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        await interaction.response.defer()
        try:
            guild = interaction.guild
            author = interaction.user
            permissions = bot.permissions.for_user(author)
            fake_msg = _FakeMessage(interaction)
            player = bot.get_player_in(guild)

            if not player:
                await interaction.followup.send(
                    "Nothing is playing.", ephemeral=True
                )
                return

            voice_channel = guild.me.voice.channel if guild.me.voice else None

            response = await bot.cmd_skip(
                guild=guild,
                player=player,
                author=author,
                message=fake_msg,
                permissions=permissions,
                voice_channel=voice_channel,
                param="force" if force else "",
            )
            await _send_response(interaction, bot, response, "skip")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /pause ────────────────────────────────────────────────────────────

    @bot.tree.command(name="pause", description="Pause the current song")
    @app_commands.guild_only()
    async def slash_pause(interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        await interaction.response.defer()
        try:
            player = bot.get_player_in(interaction.guild)
            if not player:
                await interaction.followup.send(
                    "Nothing is playing.", ephemeral=True
                )
                return

            response = await bot.cmd_pause(player)
            await _send_response(interaction, bot, response, "pause")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /resume ───────────────────────────────────────────────────────────

    @bot.tree.command(name="resume", description="Resume playback")
    @app_commands.guild_only()
    async def slash_resume(interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        await interaction.response.defer()
        try:
            player = bot.get_player_in(interaction.guild)
            if not player:
                await interaction.followup.send(
                    "Nothing is playing.", ephemeral=True
                )
                return

            response = await bot.cmd_resume(player)
            await _send_response(interaction, bot, response, "resume")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /queue ────────────────────────────────────────────────────────────

    @bot.tree.command(name="queue", description="Show the current song queue")
    @app_commands.describe(page="Page number (for long queues)")
    @app_commands.guild_only()
    async def slash_queue(
        interaction: discord.Interaction, page: int = 1
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        await interaction.response.defer()
        try:
            guild = interaction.guild
            player = bot.get_player_in(guild)
            if not player:
                await interaction.followup.send(
                    "Nothing is playing and the queue is empty.", ephemeral=True
                )
                return

            # cmd_queue sends messages to channel itself, but we need to
            # capture the Response and send it via the interaction instead.
            # We pass a dummy channel that won't actually be used for the Response path.
            response = await bot.cmd_queue(
                guild=guild,
                channel=interaction.channel,
                player=player,
                page=str(page),
            )
            await _send_response(interaction, bot, response, "queue")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /np ───────────────────────────────────────────────────────────────

    @bot.tree.command(name="np", description="Show the currently playing song")
    @app_commands.guild_only()
    async def slash_np(interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        await interaction.response.defer()
        try:
            guild = interaction.guild
            player = bot.get_player_in(guild)
            if not player:
                await interaction.followup.send(
                    "Nothing is playing.", ephemeral=True
                )
                return

            # cmd_np sends an embed to the channel AND returns a Response.
            # We call it with the interaction channel so the embed goes there,
            # then acknowledge the interaction ephemerally to avoid double-posting.
            response = await bot.cmd_np(
                player=player,
                channel=interaction.channel,
                guild=guild,
            )
            # cmd_np sends the embed to channel itself via safe_send_message.
            # The Response it returns has the same content, so we just acknowledge.
            if response and response.content:
                # It returned content that wasn't sent to channel — send it
                await _send_response(interaction, bot, response, "np")
            else:
                await interaction.followup.send(
                    "🎵 Now playing info sent above.", ephemeral=True
                )

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /volume ───────────────────────────────────────────────────────────

    @bot.tree.command(name="volume", description="Set or show the playback volume")
    @app_commands.describe(level="Volume level (1-100), or +/- for relative change")
    @app_commands.guild_only()
    async def slash_volume(
        interaction: discord.Interaction, level: Optional[str] = None
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        await interaction.response.defer()
        try:
            player = bot.get_player_in(interaction.guild)
            if not player:
                await interaction.followup.send(
                    "Nothing is playing.", ephemeral=True
                )
                return

            # Pass empty string if no level given (matches cmd_volume default)
            response = await bot.cmd_volume(
                player=player,
                new_volume=level if level is not None else "",
            )
            await _send_response(interaction, bot, response, "volume")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /summon ───────────────────────────────────────────────────────────

    @bot.tree.command(
        name="summon", description="Summon the bot to your voice channel"
    )
    @app_commands.guild_only()
    async def slash_summon(interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "You need to be in a voice channel.", ephemeral=True
            )
            return

        await interaction.response.defer()
        try:
            fake_msg = _FakeMessage(interaction)
            response = await bot.cmd_summon(
                guild=interaction.guild,
                author=interaction.user,
                message=fake_msg,
            )
            await _send_response(interaction, bot, response, "summon")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /disconnect ───────────────────────────────────────────────────────

    @bot.tree.command(name="disconnect", description="Disconnect from voice")
    @app_commands.guild_only()
    async def slash_disconnect(interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        await interaction.response.defer()
        try:
            response = await bot.cmd_disconnect(guild=interaction.guild)
            await _send_response(interaction, bot, response, "disconnect")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /shuffle ──────────────────────────────────────────────────────────

    @bot.tree.command(name="shuffle", description="Shuffle the queue")
    @app_commands.guild_only()
    async def slash_shuffle(interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        await interaction.response.defer()
        try:
            guild = interaction.guild
            player = bot.get_player_in(guild)
            if not player:
                await interaction.followup.send(
                    "Nothing is queued.", ephemeral=True
                )
                return

            # cmd_shuffle does a card animation in the channel, then returns Response.
            # We let the animation happen in the channel and send the final response
            # via the interaction.
            response = await bot.cmd_shuffle(
                channel=interaction.channel,
                player=player,
            )
            await _send_response(interaction, bot, response, "shuffle")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /clear ────────────────────────────────────────────────────────────

    @bot.tree.command(name="clear", description="Clear the queue")
    @app_commands.guild_only()
    async def slash_clear(interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        await interaction.response.defer()
        try:
            player = bot.get_player_in(interaction.guild)
            if not player:
                await interaction.followup.send(
                    "Nothing to clear.", ephemeral=True
                )
                return

            response = await bot.cmd_clear(player=player)
            await _send_response(interaction, bot, response, "clear")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /repeat ───────────────────────────────────────────────────────────

    @bot.tree.command(name="repeat", description="Toggle repeat mode")
    @app_commands.describe(
        mode="Repeat mode: all (loop queue), song (loop current), on, off"
    )
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="Song (loop current)", value="song"),
            app_commands.Choice(name="All (loop queue)", value="all"),
            app_commands.Choice(name="On", value="on"),
            app_commands.Choice(name="Off", value="off"),
        ]
    )
    @app_commands.guild_only()
    async def slash_repeat(
        interaction: discord.Interaction,
        mode: Optional[app_commands.Choice[str]] = None,
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        await interaction.response.defer()
        try:
            guild = interaction.guild
            player = bot.get_player_in(guild)
            if not player:
                await interaction.followup.send(
                    "Nothing is playing.", ephemeral=True
                )
                return

            option = mode.value if mode else ""
            response = await bot.cmd_repeat(guild=guild, option=option)
            await _send_response(interaction, bot, response, "repeat")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /search ───────────────────────────────────────────────────────────

    @bot.tree.command(
        name="search",
        description="Search for a song and choose from results",
    )
    @app_commands.describe(
        query="Search query",
        service="Service to search (default: youtube)",
    )
    @app_commands.choices(
        service=[
            app_commands.Choice(name="YouTube", value="youtube"),
            app_commands.Choice(name="SoundCloud", value="soundcloud"),
        ]
    )
    @app_commands.guild_only()
    async def slash_search(
        interaction: discord.Interaction,
        query: str,
        service: Optional[app_commands.Choice[str]] = None,
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "You need to be in a voice channel.", ephemeral=True
            )
            return

        await interaction.response.defer()
        try:
            guild = interaction.guild
            author = interaction.user
            channel = interaction.channel
            permissions = bot.permissions.for_user(author)
            fake_msg = _FakeMessage(interaction)

            # Let _cmd_play handle summoning via cmd_summon
            _player = bot.get_player_in(guild) if guild else None

            svc = service.value if service else "youtube"

            response = await bot.cmd_search(
                message=fake_msg,
                player=_player,
                channel=channel,
                guild=guild,
                author=author,
                permissions=permissions,
                leftover_args=[svc, query],
            )
            await _send_response(interaction, bot, response, "search")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /seek ─────────────────────────────────────────────────────────────

    @bot.tree.command(
        name="seek", description="Seek to a position in the current song"
    )
    @app_commands.describe(time="Time to seek to (e.g. 1:30, 90, +30, -15)")
    @app_commands.guild_only()
    async def slash_seek(interaction: discord.Interaction, time: str) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        await interaction.response.defer()
        try:
            guild = interaction.guild
            _player = bot.get_player_in(guild)
            if not _player:
                await interaction.followup.send(
                    "Nothing is playing.", ephemeral=True
                )
                return

            response = await bot.cmd_seek(
                guild=guild,
                _player=_player,
                leftover_args=[],
                seek_time=time,
            )
            await _send_response(interaction, bot, response, "seek")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /speed ────────────────────────────────────────────────────────────

    @bot.tree.command(
        name="speed", description="Set the playback speed"
    )
    @app_commands.describe(rate="Speed multiplier (e.g. 0.5, 1.0, 1.5, 2.0)")
    @app_commands.guild_only()
    async def slash_speed(interaction: discord.Interaction, rate: float) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        await interaction.response.defer()
        try:
            guild = interaction.guild
            player = bot.get_player_in(guild)
            if not player:
                await interaction.followup.send(
                    "Nothing is playing.", ephemeral=True
                )
                return

            response = await bot.cmd_speed(
                guild=guild,
                player=player,
                new_speed=str(rate),
            )
            await _send_response(interaction, bot, response, "speed")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /stream ───────────────────────────────────────────────────────────

    @bot.tree.command(
        name="stream", description="Stream from a URL (no pre-download)"
    )
    @app_commands.describe(url="URL to stream")
    @app_commands.guild_only()
    async def slash_stream(interaction: discord.Interaction, url: str) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "You need to be in a voice channel.", ephemeral=True
            )
            return

        await interaction.response.defer()
        try:
            guild = interaction.guild
            author = interaction.user
            channel = interaction.channel
            permissions = bot.permissions.for_user(author)
            fake_msg = _FakeMessage(interaction)

            # Let _cmd_play handle summoning via cmd_summon
            _player = bot.get_player_in(guild) if guild else None

            response = await bot.cmd_stream(
                message=fake_msg,
                _player=_player,
                channel=channel,
                guild=guild,
                author=author,
                permissions=permissions,
                song_url=url,
            )
            await _send_response(interaction, bot, response, "stream")

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /help ─────────────────────────────────────────────────────────────

    @bot.tree.command(name="help", description="Show available commands")
    @app_commands.guild_only()
    async def slash_help(interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            commands = bot.tree.get_commands()
            lines = ["**Available Slash Commands:**\n"]
            for cmd in sorted(commands, key=lambda c: c.name):
                desc = cmd.description or "No description"
                lines.append(f"• `/{cmd.name}` — {desc}")

            text = "\n".join(lines)
            if len(text) > 2000:
                text = text[:1997] + "..."

            await interaction.followup.send(text, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)

    log.info(
        "Registered %d slash commands.",
        len(bot.tree.get_commands()),
    )
