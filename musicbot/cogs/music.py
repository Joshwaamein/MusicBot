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
import re as _re
import subprocess
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands

if TYPE_CHECKING:
    from musicbot.bot import MusicBot

log = logging.getLogger(__name__)


# ── Input Validation ────────────────────────────────────────────────────────
MAX_SONG_QUERY_LEN = 500
MAX_SEARCH_QUERY_LEN = 200
MAX_URL_LEN = 2000
SPEED_MIN = 0.5
SPEED_MAX = 100.0
SEEK_PATTERN = _re.compile(r"^[+-]?(\d{1,2}:)?\d{1,4}(:\d{2})?$")


def _validate_song_input(song: str) -> str:
    """Validate and sanitize song/URL input."""
    song = song.strip()
    if not song:
        raise ValueError("Song query cannot be empty.")
    if len(song) > MAX_SONG_QUERY_LEN:
        raise ValueError(f"Song query too long (max {MAX_SONG_QUERY_LEN} chars).")
    return song


def _validate_url(url: str) -> str:
    """Validate URL input."""
    url = url.strip()
    if not url:
        raise ValueError("URL cannot be empty.")
    if len(url) > MAX_URL_LEN:
        raise ValueError(f"URL too long (max {MAX_URL_LEN} chars).")
    if not url.startswith(("http://", "https://", "spotify:")):
        raise ValueError("URL must start with http://, https://, or spotify:")
    return url


def _validate_search_query(query: str) -> str:
    """Validate search query input."""
    query = query.strip()
    if not query:
        raise ValueError("Search query cannot be empty.")
    if len(query) > MAX_SEARCH_QUERY_LEN:
        raise ValueError(f"Search query too long (max {MAX_SEARCH_QUERY_LEN} chars).")
    return query


def _validate_seek_time(time_str: str) -> str:
    """Validate seek time format."""
    time_str = time_str.strip()
    if not SEEK_PATTERN.match(time_str):
        raise ValueError("Invalid time format. Use e.g. 1:30, 90, +30, -15")
    return time_str


def _validate_speed(rate: float) -> float:
    """Validate speed rate."""
    if rate < SPEED_MIN or rate > SPEED_MAX:
        raise ValueError(f"Speed must be between {SPEED_MIN} and {SPEED_MAX}.")
    return rate



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
            song = _validate_song_input(song)
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
            song = _validate_song_input(song)
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
            song = _validate_song_input(song)
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
            song = _validate_song_input(song)
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
            guild = interaction.guild
            player = bot.get_player_in(guild)
            if not player:
                await interaction.followup.send(
                    "Nothing to clear.", ephemeral=True
                )
                return

            # Stop radio session if active (prevents auto-refill)
            radio_was_active = False
            if guild and guild.id in bot._radio_sessions:
                del bot._radio_sessions[guild.id]
                radio_was_active = True

            response = await bot.cmd_clear(player=player)

            # Add radio stop notice to the response
            if radio_was_active:
                from musicbot.constructs import Response
                response = Response(
                    "Cleared the queue and stopped the radio. \U0001f4fb",
                    delete_after=20,
                )

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

            query = _validate_search_query(query)
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

            time = _validate_seek_time(time)
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

            rate = _validate_speed(rate)
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

            url = _validate_url(url)
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


    # ─── /restart ──────────────────────────────────────────────────────────

    @bot.tree.command(
        name="restart",
        description="Restart the bot (soft restart by default)",
    )
    @app_commands.describe(
        mode="Restart mode"
    )
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="Soft (reload config)", value="soft"),
            app_commands.Choice(name="Full (restart process)", value="full"),
            app_commands.Choice(name="Upgrade all", value="upgrade"),
            app_commands.Choice(name="Upgrade pip packages", value="uppip"),
            app_commands.Choice(name="Upgrade via git", value="upgit"),
        ]
    )
    @app_commands.guild_only()
    async def slash_restart(
        interaction: discord.Interaction,
        mode: Optional[app_commands.Choice[str]] = None,
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        await interaction.response.defer()
        try:
            opt = mode.value if mode else "soft"
            _player = bot.get_player_in(interaction.guild) if interaction.guild else None

            response = await bot.cmd_restart(
                _player=_player,
                channel=interaction.channel,
                opt=opt,
            )
            if response:
                await _send_response(interaction, bot, response, "restart")
            else:
                await interaction.followup.send(
                    f"\U0001f504 Bot is restarting ({opt})...", ephemeral=True
                )

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /reboot ───────────────────────────────────────────────────────────

    @bot.tree.command(
        name="reboot",
        description="Reboot the server (requires confirmation)",
    )
    @app_commands.describe(
        confirm="Type 'yes' to confirm server reboot"
    )
    @app_commands.guild_only()
    async def slash_reboot(
        interaction: discord.Interaction,
        confirm: str = "",
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        if confirm.strip().lower() != "yes":
            await interaction.response.send_message(
                "\u26a0\ufe0f **Server Reboot**\n"
                "This will reboot the entire server, not just the bot.\n"
                "To confirm, use: `/reboot confirm:yes`",
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        try:
            await interaction.followup.send(
                "\U0001f504 **Server is rebooting now!** The bot will come back online automatically.",
            )
            # Give Discord a moment to send the message
            import asyncio
            await asyncio.sleep(2)
            # Reboot the server
            subprocess.Popen(["reboot"])

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)


    # ═══════════════════════════════════════════════════════════════════════
    # Phase 3: Playlist & Configuration Commands
    # ═══════════════════════════════════════════════════════════════════════

    # ─── /autoplaylist ─────────────────────────────────────────────────────

    @bot.tree.command(
        name="autoplaylist",
        description="Manage the auto-playlist (add/remove/show songs)",
    )
    @app_commands.describe(
        action="What to do",
        url="URL of the song (optional, uses current song if empty)",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Add song", value="add"),
            app_commands.Choice(name="Remove song", value="remove"),
            app_commands.Choice(name="Add entire queue", value="add all"),
            app_commands.Choice(name="Show playlist", value="show"),
        ]
    )
    @app_commands.guild_only()
    async def slash_autoplaylist(
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        url: Optional[str] = None,
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            guild = interaction.guild
            _player = bot.get_player_in(guild) if guild else None
            # autoplaylist needs both _player and player params
            response = await bot.cmd_autoplaylist(
                guild=guild,
                author=interaction.user,
                _player=_player,
                player=_player,
                option=action.value,
                opt_url=url or "",
            )
            await _send_response(interaction, bot, response, "autoplaylist")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /resetplaylist ────────────────────────────────────────────────────

    @bot.tree.command(
        name="resetplaylist",
        description="Reset the auto-playlist to the default",
    )
    @app_commands.guild_only()
    async def slash_resetplaylist(interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            guild = interaction.guild
            player = bot.get_player_in(guild)
            if not player:
                await interaction.followup.send("Nothing is playing.", ephemeral=True)
                return
            response = await bot.cmd_resetplaylist(guild=guild, player=player)
            await _send_response(interaction, bot, response, "resetplaylist")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /karaoke ──────────────────────────────────────────────────────────

    @bot.tree.command(
        name="karaoke",
        description="Toggle karaoke mode",
    )
    @app_commands.guild_only()
    async def slash_karaoke(interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            player = bot.get_player_in(interaction.guild)
            if not player:
                await interaction.followup.send("Nothing is playing.", ephemeral=True)
                return
            response = await bot.cmd_karaoke(player=player)
            await _send_response(interaction, bot, response, "karaoke")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /follow ───────────────────────────────────────────────────────────

    @bot.tree.command(
        name="follow",
        description="Tell the bot to follow a user between voice channels",
    )
    @app_commands.describe(user="User to follow (leave empty to stop following)")
    @app_commands.guild_only()
    async def slash_follow(
        interaction: discord.Interaction, user: Optional[discord.Member] = None
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            mentions = [user] if user else []
            response = await bot.cmd_follow(
                guild=interaction.guild,
                author=interaction.user,
                user_mentions=mentions,
            )
            await _send_response(interaction, bot, response, "follow")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /setprefix ────────────────────────────────────────────────────────

    @bot.tree.command(
        name="setprefix",
        description="Set a custom command prefix for this server",
    )
    @app_commands.describe(prefix="New command prefix")
    @app_commands.guild_only()
    async def slash_setprefix(interaction: discord.Interaction, prefix: str) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            response = await bot.cmd_setprefix(guild=interaction.guild, prefix=prefix)
            await _send_response(interaction, bot, response, "setprefix")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /setnick ──────────────────────────────────────────────────────────

    @bot.tree.command(
        name="setnick",
        description="Set the bot\'s nickname on this server",
    )
    @app_commands.describe(nick="New nickname (leave empty to reset)")
    @app_commands.guild_only()
    async def slash_setnick(
        interaction: discord.Interaction, nick: Optional[str] = None
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            response = await bot.cmd_setnick(guild=interaction.guild, nick=nick or "")
            await _send_response(interaction, bot, response, "setnick")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /perms ────────────────────────────────────────────────────────────

    @bot.tree.command(
        name="perms",
        description="Show permissions for a user",
    )
    @app_commands.describe(user="User to check (leave empty for yourself)")
    @app_commands.guild_only()
    async def slash_perms(
        interaction: discord.Interaction, user: Optional[discord.Member] = None
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            mentions = [user] if user else []
            permissions = bot.permissions.for_user(interaction.user)
            response = await bot.cmd_perms(
                author=interaction.user,
                channel=interaction.channel,
                user_mentions=mentions,
                guild=interaction.guild,
                permissions=permissions,
            )
            await _send_response(interaction, bot, response, "perms")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /id ───────────────────────────────────────────────────────────────

    @bot.tree.command(
        name="id",
        description="Show the ID of a user or yourself",
    )
    @app_commands.describe(user="User to get ID for")
    @app_commands.guild_only()
    async def slash_id(
        interaction: discord.Interaction, user: Optional[discord.Member] = None
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            mentions = [user] if user else []
            response = await bot.cmd_id(
                author=interaction.user,
                user_mentions=mentions,
            )
            await _send_response(interaction, bot, response, "id")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ═══════════════════════════════════════════════════════════════════════
    # Phase 4: Moderation Commands
    # ═══════════════════════════════════════════════════════════════════════

    # ─── /blockuser ────────────────────────────────────────────────────────

    @bot.tree.command(
        name="blockuser",
        description="Block or unblock a user from using the bot",
    )
    @app_commands.describe(
        action="Add to blocklist, remove from blocklist, or check status",
        user="The user to block/unblock",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Block user", value="add"),
            app_commands.Choice(name="Unblock user", value="remove"),
            app_commands.Choice(name="Check status", value="status"),
        ]
    )
    @app_commands.guild_only()
    async def slash_blockuser(
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        user: discord.Member,
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            response = await bot.cmd_blockuser(
                author=interaction.user,
                user_mentions=[user],
                option=action.value,
            )
            await _send_response(interaction, bot, response, "blockuser")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /blocksong ────────────────────────────────────────────────────────

    @bot.tree.command(
        name="blocksong",
        description="Block or unblock a song/URL from being played",
    )
    @app_commands.describe(
        action="Add or remove from blocklist",
        subject="URL, video ID, or phrase to block",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Block", value="add"),
            app_commands.Choice(name="Unblock", value="remove"),
        ]
    )
    @app_commands.guild_only()
    async def slash_blocksong(
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        subject: str,
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            response = await bot.cmd_blocksong(
                option=action.value,
                leftover_args=[subject],
            )
            await _send_response(interaction, bot, response, "blocksong")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /clean ────────────────────────────────────────────────────────────

    @bot.tree.command(
        name="clean",
        description="Clean up bot messages from the channel",
    )
    @app_commands.describe(count="Number of messages to search through (default 50)")
    @app_commands.guild_only()
    async def slash_clean(
        interaction: discord.Interaction, count: Optional[int] = None
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer(ephemeral=True)
        try:
            fake_msg = _FakeMessage(interaction)
            response = await bot.cmd_clean(
                message=fake_msg,
                channel=interaction.channel,
                guild=interaction.guild,
                author=interaction.user,
                search_range_str=str(count) if count else "50",
            )
            await _send_response(interaction, bot, response, "clean")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /pldump ───────────────────────────────────────────────────────────

    @bot.tree.command(
        name="pldump",
        description="Dump all URLs from a playlist link",
    )
    @app_commands.describe(url="Playlist URL to dump")
    @app_commands.guild_only()
    async def slash_pldump(interaction: discord.Interaction, url: str) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            url = _validate_url(url)
            response = await bot.cmd_pldump(song_url=url)
            await _send_response(interaction, bot, response, "pldump")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /listids ──────────────────────────────────────────────────────────

    @bot.tree.command(
        name="listids",
        description="List server/channel/role/user IDs",
    )
    @app_commands.describe(category="What to list IDs for")
    @app_commands.choices(
        category=[
            app_commands.Choice(name="Everything", value="all"),
            app_commands.Choice(name="Users", value="users"),
            app_commands.Choice(name="Roles", value="roles"),
            app_commands.Choice(name="Channels", value="channels"),
        ]
    )
    @app_commands.guild_only()
    async def slash_listids(
        interaction: discord.Interaction,
        category: Optional[app_commands.Choice[str]] = None,
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer(ephemeral=True)
        try:
            cat = category.value if category else "all"
            response = await bot.cmd_listids(
                guild=interaction.guild,
                author=interaction.user,
                leftover_args=[],
                cat=cat,
            )
            await _send_response(interaction, bot, response, "listids")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ═══════════════════════════════════════════════════════════════════════
    # Phase 5: Admin Commands (require server Administrator permission)
    # ═══════════════════════════════════════════════════════════════════════

    # ─── /config ───────────────────────────────────────────────────────────

    @bot.tree.command(
        name="config",
        description="View or change bot configuration",
    )
    @app_commands.describe(
        option="Config option to view/change",
        value="New value (leave empty to view current)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def slash_config(
        interaction: discord.Interaction,
        option: str,
        value: Optional[str] = None,
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            args = [value] if value else []
            response = await bot.cmd_config(
                user_mentions=[],
                channel_mentions=[],
                option=option,
                leftover_args=args,
            )
            await _send_response(interaction, bot, response, "config")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /setperms ─────────────────────────────────────────────────────────

    @bot.tree.command(
        name="setperms",
        description="View or change bot permissions groups",
    )
    @app_commands.describe(
        action="Action to perform",
        args="Additional arguments (group name, permission, value)",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="List groups", value="list"),
            app_commands.Choice(name="Show group details", value="show"),
            app_commands.Choice(name="Set a permission", value="set"),
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def slash_setperms(
        interaction: discord.Interaction,
        action: Optional[app_commands.Choice[str]] = None,
        args: Optional[str] = None,
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            opt = action.value if action else "list"
            leftover = args.split() if args else []
            response = await bot.cmd_setperms(
                user_mentions=[],
                leftover_args=leftover,
                option=opt,
            )
            await _send_response(interaction, bot, response, "setperms")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /option ───────────────────────────────────────────────────────────

    @bot.tree.command(
        name="option",
        description="Toggle a bot option on/off",
    )
    @app_commands.describe(
        option="Option name",
        value="on/off/yes/no",
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def slash_option(
        interaction: discord.Interaction, option: str, value: str
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            response = await bot.cmd_option(
                guild=interaction.guild,
                option=option,
                value=value,
            )
            await _send_response(interaction, bot, response, "option")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /cache ────────────────────────────────────────────────────────────

    @bot.tree.command(
        name="cache",
        description="View or manage the audio cache",
    )
    @app_commands.describe(action="Cache action")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Show info", value="info"),
            app_commands.Choice(name="Update", value="update"),
            app_commands.Choice(name="Clear cache", value="clear"),
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def slash_cache(
        interaction: discord.Interaction,
        action: Optional[app_commands.Choice[str]] = None,
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            opt = action.value if action else "info"
            response = await bot.cmd_cache(opt=opt)
            await _send_response(interaction, bot, response, "cache")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /setname ──────────────────────────────────────────────────────────

    @bot.tree.command(
        name="setname",
        description="Change the bot\'s username",
    )
    @app_commands.describe(name="New bot username")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def slash_setname(interaction: discord.Interaction, name: str) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            response = await bot.cmd_setname(leftover_args=[], name=name)
            await _send_response(interaction, bot, response, "setname")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /setavatar ────────────────────────────────────────────────────────

    @bot.tree.command(
        name="setavatar",
        description="Change the bot\'s avatar",
    )
    @app_commands.describe(url="URL of the new avatar image")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def slash_setavatar(interaction: discord.Interaction, url: str) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            url = _validate_url(url)
            response = await bot.cmd_setavatar(url=url)
            await _send_response(interaction, bot, response, "setavatar")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /joinserver ───────────────────────────────────────────────────────

    @bot.tree.command(
        name="joinserver",
        description="Generate an invite link to add the bot to another server",
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def slash_joinserver(interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer(ephemeral=True)
        try:
            response = await bot.cmd_joinserver()
            await _send_response(interaction, bot, response, "joinserver")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /leaveserver ──────────────────────────────────────────────────────

    @bot.tree.command(
        name="leaveserver",
        description="Make the bot leave a server",
    )
    @app_commands.describe(server="Server name or ID to leave")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def slash_leaveserver(interaction: discord.Interaction, server: str) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            response = await bot.cmd_leaveserver(val=server)
            await _send_response(interaction, bot, response, "leaveserver")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ═══════════════════════════════════════════════════════════════════════
    # Phase 6: Info Commands
    # ═══════════════════════════════════════════════════════════════════════

    # ─── /uptime ───────────────────────────────────────────────────────────

    @bot.tree.command(
        name="uptime",
        description="Show how long the bot has been running",
    )
    @app_commands.guild_only()
    async def slash_uptime(interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            response = await bot.cmd_uptime()
            await _send_response(interaction, bot, response, "uptime")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /latency ──────────────────────────────────────────────────────────

    @bot.tree.command(
        name="latency",
        description="Show API and voice latency",
    )
    @app_commands.guild_only()
    async def slash_latency(interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            response = await bot.cmd_latency(guild=interaction.guild)
            await _send_response(interaction, bot, response, "latency")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /botlatency ──────────────────────────────────────────────────────

    @bot.tree.command(
        name="botlatency",
        description="Show detailed latency for all voice connections",
    )
    @app_commands.guild_only()
    async def slash_botlatency(interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            response = await bot.cmd_botlatency()
            await _send_response(interaction, bot, response, "botlatency")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ─── /botversion ──────────────────────────────────────────────────────

    @bot.tree.command(
        name="botversion",
        description="Show the current bot version",
    )
    @app_commands.guild_only()
    async def slash_botversion(interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.defer()
        try:
            response = await bot.cmd_botversion()
            await _send_response(interaction, bot, response, "botversion")
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)

    # ═══════════════════════════════════════════════════════════════════════
    # Phase 7: Radio / DJ Commands
    # ═══════════════════════════════════════════════════════════════════════

    # ─── /radio ────────────────────────────────────────────────────────────

    @bot.tree.command(
        name="radio",
        description="Start a Spotify radio station based on a song or artist",
    )
    @app_commands.describe(
        seed="Song name, artist, or Spotify URL to seed the radio",
        action="Start or stop the radio",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Start", value="start"),
            app_commands.Choice(name="Stop", value="stop"),
        ]
    )
    @app_commands.guild_only()
    async def slash_radio(
        interaction: discord.Interaction,
        seed: Optional[str] = None,
        action: Optional[app_commands.Choice[str]] = None,
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        guild = interaction.guild
        act = action.value if action else "start"

        # ── Handle stop ──
        if act == "stop":
            if guild and guild.id in bot._radio_sessions:
                del bot._radio_sessions[guild.id]
                # Also clear the queue
                player = bot.get_player_in(guild)
                if player:
                    player.playlist.clear()
                await interaction.response.send_message(
                    "\U0001f4fb Radio stopped and queue cleared.", ephemeral=False
                )
            else:
                await interaction.response.send_message(
                    "No radio is currently playing.", ephemeral=True
                )
            return

        # ── Handle start ──
        if not seed:
            await interaction.response.send_message(
                "Please provide a seed song or artist. Example: `/radio seed:Daft Punk - Get Lucky`",
                ephemeral=True,
            )
            return

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "You need to be in a voice channel.", ephemeral=True
            )
            return

        if not bot.config.spotify_enabled or not bot.spotify:
            await interaction.response.send_message(
                "\u274c Spotify is not configured. Radio requires Spotify credentials.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        try:
            from musicbot.spotify import Spotify

            seed_track_ids = []
            seed_artist_ids = []
            seed_track_name = seed

            # Check if seed is a Spotify URL
            if Spotify.is_url_supported(seed):
                parts = Spotify.url_to_parts(seed)
                if parts[1] == "track":
                    track_obj = await bot.spotify.get_track_object(parts[-1])
                    seed_track_ids = [track_obj.spotify_id]
                    seed_track_name = f"{track_obj.artist_name} - {track_obj.name}"
                    # Also grab artist ID
                    artists = track_obj.data.get("artists", [])
                    if artists:
                        aid = artists[0].get("id")
                        if aid:
                            seed_artist_ids = [aid]
                else:
                    await interaction.followup.send(
                        "\u274c Radio only supports track URLs as seeds, not playlists or albums.",
                        ephemeral=True,
                    )
                    return
            else:
                # Search Spotify for the seed
                results = await bot.spotify.search_tracks(seed, limit=1)
                if not results:
                    await interaction.followup.send(
                        f"\u274c Could not find any tracks matching: **{seed}**",
                        ephemeral=True,
                    )
                    return
                top_track = results[0]
                seed_track_ids = [top_track.spotify_id]
                seed_track_name = f"{top_track.artist_name} - {top_track.name}"
                artists = top_track.data.get("artists", [])
                if artists:
                    aid = artists[0].get("id")
                    if aid:
                        seed_artist_ids = [aid]

            # Get artist genres for better discovery
            artist_genres = []
            if seed_artist_ids:
                try:
                    artist_info = await bot.spotify.get_artist_info(seed_artist_ids[0])
                    artist_genres = artist_info.get("genres", [])
                except Exception:
                    pass

            # First, queue the seed song itself
            author = interaction.user
            channel = interaction.channel
            permissions = bot.permissions.for_user(author)
            fake_msg = _FakeMessage(interaction)
            _player = bot.get_player_in(guild) if guild else None

            # Play the seed song first
            try:
                await bot._cmd_play(
                    message=fake_msg,
                    _player=_player,
                    channel=channel,
                    guild=guild,
                    author=author,
                    permissions=permissions,
                    leftover_args=[],
                    song_url=seed,
                    head=False,
                )
                if not _player:
                    _player = bot.get_player_in(guild)
            except Exception as e:
                log.warning("Radio: failed to queue seed song: %s", e)

            # Discover similar tracks using hybrid approach
            recs = await bot.spotify.discover_tracks_for_radio(
                artist_ids=seed_artist_ids,
                artist_name=seed_track_name.split(" - ")[0] if " - " in seed_track_name else seed_track_name,
                genres=artist_genres,
                exclude_track_ids=set(seed_track_ids),
                limit=20,
            )

            if not recs:
                await interaction.followup.send(
                    f"\u274c Could not find similar tracks for: **{seed_track_name}**",
                    ephemeral=True,
                )
                return

            # Store radio session
            played_ids = set(seed_track_ids)
            bot._radio_sessions[guild.id] = {
                "guild_id": guild.id,
                "seed_track_ids": seed_track_ids,
                "seed_artist_ids": seed_artist_ids,
                "artist_name": seed_track_name.split(" - ")[0] if " - " in seed_track_name else seed_track_name,
                "genres": artist_genres,
                "channel": interaction.channel,
                "author": interaction.user,
                "active": True,
                "played_track_ids": played_ids,
            }

            # Send the radio started embed
            embed = bot._gen_embed()
            embed.title = "\U0001f4fb Radio Started"
            embed.description = (
                f"**Seed:** {seed_track_name}\n"
                f"**Queuing:** {len(recs)} similar tracks from various artists\n\n"
                f"Use `/radio action:Stop` to stop the radio."
            )
            await interaction.followup.send(embed=embed)

            # Queue all discovered tracks
            for track in recs:
                search_query = track.get_track_search_string("ytsearch:{0} {1}")
                try:
                    await bot._cmd_play(
                        message=fake_msg,
                        _player=_player,
                        channel=channel,
                        guild=guild,
                        author=author,
                        permissions=permissions,
                        leftover_args=[],
                        song_url=search_query,
                        head=False,
                    )
                    played_ids.add(track.spotify_id)
                    if not _player:
                        _player = bot.get_player_in(guild)
                except Exception as e:
                    log.warning("Radio: failed to queue %s: %s", track.name, e)
                    continue

        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            await interaction.followup.send(f"\u274c {msg}", ephemeral=True)


    log.info(
        "Registered %d slash commands.",
        len(bot.tree.get_commands()),
    )
