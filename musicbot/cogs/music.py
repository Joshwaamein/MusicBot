"""
Slash command cog for core music commands.
These wrap the existing MusicBot cmd_* methods to provide Discord slash command support.
"""

import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands

if TYPE_CHECKING:
    from musicbot.bot import MusicBot

log = logging.getLogger(__name__)


class MusicCog:
    """Registers slash commands for MusicBot's core music functionality."""

    def __init__(self, bot: "MusicBot") -> None:
        self.bot = bot

    async def _get_voice_channel(
        self, interaction: discord.Interaction
    ) -> Optional[discord.VoiceChannel]:
        """Get the voice channel of the interaction author."""
        if (
            isinstance(interaction.user, discord.Member)
            and interaction.user.voice
            and interaction.user.voice.channel
        ):
            return interaction.user.voice.channel
        return None

    async def _ensure_voice(
        self, interaction: discord.Interaction
    ) -> bool:
        """Check that the user is in a voice channel."""
        vc = await self._get_voice_channel(interaction)
        if not vc:
            await interaction.response.send_message(
                "You need to be in a voice channel to use this command.",
                ephemeral=True,
            )
            return False
        return True

    # ─── /play ─────────────────────────────────────────────────────────────

    @app_commands.command(name="play", description="Play a song from YouTube, Spotify, or search by name")
    @app_commands.describe(song="A URL or search query for the song to play")
    async def slash_play(self, interaction: discord.Interaction, song: str) -> None:
        if not await self._ensure_voice(interaction):
            return
        await interaction.response.defer()
        try:
            guild = interaction.guild
            author = interaction.user
            channel = interaction.channel
            permissions = self.bot.permissions.for_user(author)

            _player = self.bot.get_player_in(guild) if guild else None

            # If not in voice, summon first
            if not _player and guild and isinstance(author, discord.Member) and author.voice:
                voice_channel = author.voice.channel
                _player = await self.bot.get_player(voice_channel, create=True)

            if not _player:
                await interaction.followup.send("Could not join a voice channel.", ephemeral=True)
                return

            # Use the internal play logic
            response = await self.bot._cmd_play(
                message=None,
                _player=_player,
                channel=channel,
                guild=guild,
                author=author,
                permissions=permissions,
                leftover_args=[],
                song_url=song,
                head=False,
            )
            if response and response.content:
                content = response.content
                if isinstance(content, discord.Embed):
                    await interaction.followup.send(embed=content)
                else:
                    await interaction.followup.send(str(content))
            else:
                await interaction.followup.send("🎶 Added to queue!", ephemeral=True)
        except Exception as e:
            msg = getattr(e, "message", str(e))
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── /playnext ─────────────────────────────────────────────────────────

    @app_commands.command(name="playnext", description="Add a song to play next in the queue")
    @app_commands.describe(song="A URL or search query")
    async def slash_playnext(self, interaction: discord.Interaction, song: str) -> None:
        if not await self._ensure_voice(interaction):
            return
        await interaction.response.defer()
        try:
            guild = interaction.guild
            author = interaction.user
            channel = interaction.channel
            permissions = self.bot.permissions.for_user(author)
            _player = self.bot.get_player_in(guild) if guild else None

            if not _player and guild and isinstance(author, discord.Member) and author.voice:
                _player = await self.bot.get_player(author.voice.channel, create=True)

            if not _player:
                await interaction.followup.send("Could not join a voice channel.", ephemeral=True)
                return

            response = await self.bot._cmd_play(
                message=None, _player=_player, channel=channel, guild=guild,
                author=author, permissions=permissions, leftover_args=[],
                song_url=song, head=True,
            )
            if response and response.content:
                await interaction.followup.send(str(response.content) if not isinstance(response.content, discord.Embed) else "", embed=response.content if isinstance(response.content, discord.Embed) else None)
            else:
                await interaction.followup.send("🎶 Added to play next!")
        except Exception as e:
            await interaction.followup.send(f"❌ {getattr(e, 'message', str(e))}", ephemeral=True)

    # ─── /skip ─────────────────────────────────────────────────────────────

    @app_commands.command(name="skip", description="Skip the current song")
    @app_commands.describe(force="Force skip (owner/instaskip only)")
    async def slash_skip(self, interaction: discord.Interaction, force: bool = False) -> None:
        if not interaction.guild:
            return
        player = self.bot.get_player_in(interaction.guild)
        if not player:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return

        if not player.current_entry:
            await interaction.response.send_message("Nothing is playing right now.", ephemeral=True)
            return

        permissions = self.bot.permissions.for_user(interaction.user)
        entry = player.current_entry
        author = interaction.user
        entry_author_id = entry.author.id if entry.author else 0

        permission_force_skip = permissions.instaskip or (
            self.bot.config.allow_author_skip and author.id == entry_author_id
        )

        if force and not permission_force_skip:
            await interaction.response.send_message("You don't have permission to force skip.", ephemeral=True)
            return

        if permission_force_skip and (force or self.bot.config.legacy_skip):
            if player.repeatsong:
                player.repeatsong = False
            player.skip()
            await interaction.response.send_message(f"⏭️ Force skipped **{entry.title}**")
        else:
            # Vote skip
            voice_channel = interaction.guild.me.voice.channel if interaction.guild.me.voice else None
            from musicbot.utils import count_members_in_voice
            import math

            num_voice = count_members_in_voice(voice_channel, include_bots=self.bot.config.bot_exception_ids)
            if num_voice == 0:
                num_voice = 1

            # We can't easily use the skip_state with slash commands without a message
            # So just do the skip for now
            player.skip()
            await interaction.response.send_message(f"⏭️ Skipped **{entry.title}**")

    # ─── /pause ────────────────────────────────────────────────────────────

    @app_commands.command(name="pause", description="Pause the current song")
    async def slash_pause(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.bot.get_player_in(interaction.guild)
        if not player or not player.is_playing:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        player.pause()
        await interaction.response.send_message(f"⏸️ Paused in **{player.voice_client.channel.name}**")

    # ─── /resume ───────────────────────────────────────────────────────────

    @app_commands.command(name="resume", description="Resume playback")
    async def slash_resume(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.bot.get_player_in(interaction.guild)
        if not player or not player.is_paused:
            await interaction.response.send_message("Nothing is paused.", ephemeral=True)
            return
        player.resume()
        await interaction.response.send_message(f"▶️ Resumed in **{player.voice_client.channel.name}**")

    # ─── /queue ────────────────────────────────────────────────────────────

    @app_commands.command(name="queue", description="Show the current song queue")
    @app_commands.describe(page="Page number to display")
    async def slash_queue(self, interaction: discord.Interaction, page: int = 1) -> None:
        if not interaction.guild:
            return
        player = self.bot.get_player_in(interaction.guild)
        if not player or not player.playlist.entries:
            await interaction.response.send_message("The queue is empty.", ephemeral=True)
            return

        from musicbot.utils import format_song_duration
        import math

        entries = list(player.playlist.entries)
        total = len(entries)
        per_page = 10
        pages = math.ceil(total / per_page)
        page = max(1, min(page, pages))
        start = (page - 1) * per_page
        end = start + per_page

        desc = ""
        if player.current_entry:
            progress = format_song_duration(player.progress)
            duration = format_song_duration(player.current_entry.duration_td) if player.current_entry.duration else "?"
            desc += f"🎵 **Now Playing:** {player.current_entry.title}\n`[{progress}/{duration}]`\n\n"

        desc += f"**Queue ({total} songs):**\n"
        for idx, item in enumerate(entries[start:end], start + 1):
            title = item.title[:50] + "..." if len(item.title) > 50 else item.title
            author_name = f" — added by {item.author.name}" if item.author else ""
            desc += f"`{idx}.` {title}{author_name}\n"

        if pages > 1:
            desc += f"\n*Page {page}/{pages}*"

        embed = discord.Embed(title="🎶 Song Queue", description=desc, color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed)

    # ─── /np (now playing) ─────────────────────────────────────────────────

    @app_commands.command(name="np", description="Show the currently playing song")
    async def slash_np(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.bot.get_player_in(interaction.guild)
        if not player or not player.current_entry:
            await interaction.response.send_message("Nothing is playing right now.", ephemeral=True)
            return

        from musicbot.utils import format_song_duration

        entry = player.current_entry
        progress = format_song_duration(player.progress)
        duration = format_song_duration(entry.duration_td) if entry.duration else "Live"

        # Progress bar
        percentage = 0.0
        if entry.duration and entry.duration_td.total_seconds() > 0:
            percentage = player.progress / entry.duration_td.total_seconds()
        bar_len = 20
        filled = int(bar_len * percentage)
        bar = "▓" * filled + "░" * (bar_len - filled)

        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{entry.title}**",
            color=discord.Color.green(),
        )
        if entry.author:
            embed.add_field(name="Added by", value=entry.author.name, inline=True)
        embed.add_field(name="Progress", value=f"`{bar}` {progress}/{duration}", inline=False)
        if entry.url:
            embed.add_field(name="URL", value=entry.url, inline=False)
        if entry.thumbnail_url:
            embed.set_thumbnail(url=entry.thumbnail_url)

        await interaction.response.send_message(embed=embed)

    # ─── /volume ───────────────────────────────────────────────────────────

    @app_commands.command(name="volume", description="Set or show the playback volume")
    @app_commands.describe(level="Volume level (1-100)")
    async def slash_volume(self, interaction: discord.Interaction, level: Optional[int] = None) -> None:
        if not interaction.guild:
            return
        player = self.bot.get_player_in(interaction.guild)
        if not player:
            await interaction.response.send_message("Not connected to voice.", ephemeral=True)
            return

        if level is None:
            vol = int(player.volume * 100)
            await interaction.response.send_message(f"🔊 Current volume: **{vol}%**")
            return

        if not 1 <= level <= 100:
            await interaction.response.send_message("Volume must be between 1 and 100.", ephemeral=True)
            return

        old_vol = int(player.volume * 100)
        player.volume = level / 100.0
        await interaction.response.send_message(f"🔊 Volume: **{old_vol}%** → **{level}%**")

    # ─── /summon ───────────────────────────────────────────────────────────

    @app_commands.command(name="summon", description="Summon the bot to your voice channel")
    async def slash_summon(self, interaction: discord.Interaction) -> None:
        if not await self._ensure_voice(interaction):
            return
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return

        await interaction.response.defer()
        try:
            player = self.bot.get_player_in(interaction.guild)
            if player and player.voice_client:
                await interaction.guild.change_voice_state(
                    channel=interaction.user.voice.channel,
                    self_deaf=self.bot.config.self_deafen,
                )
            else:
                player = await self.bot.get_player(
                    interaction.user.voice.channel, create=True
                )
            await interaction.followup.send(f"✅ Connected to **{interaction.user.voice.channel.name}**")
        except Exception as e:
            await interaction.followup.send(f"❌ {getattr(e, 'message', str(e))}", ephemeral=True)

    # ─── /disconnect ───────────────────────────────────────────────────────

    @app_commands.command(name="disconnect", description="Disconnect the bot from voice")
    async def slash_disconnect(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.bot.get_player_in(interaction.guild)
        if not player:
            await interaction.response.send_message("Not connected to voice.", ephemeral=True)
            return

        await self.bot.disconnect_voice_client(interaction.guild)
        await interaction.response.send_message("👋 Disconnected from voice.")

    # ─── /shuffle ──────────────────────────────────────────────────────────

    @app_commands.command(name="shuffle", description="Shuffle the queue")
    async def slash_shuffle(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.bot.get_player_in(interaction.guild)
        if not player or not player.playlist.entries:
            await interaction.response.send_message("Nothing to shuffle.", ephemeral=True)
            return
        player.playlist.shuffle()
        await interaction.response.send_message("🔀 Queue shuffled!")

    # ─── /clear ────────────────────────────────────────────────────────────

    @app_commands.command(name="clear", description="Clear the queue")
    async def slash_clear(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.bot.get_player_in(interaction.guild)
        if not player:
            await interaction.response.send_message("Not connected to voice.", ephemeral=True)
            return
        player.playlist.clear()
        await interaction.response.send_message("🗑️ Queue cleared!")

    # ─── /repeat ───────────────────────────────────────────────────────────

    @app_commands.command(name="repeat", description="Toggle repeat mode")
    @app_commands.describe(mode="Repeat mode")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Song", value="song"),
        app_commands.Choice(name="Playlist", value="playlist"),
        app_commands.Choice(name="Off", value="off"),
    ])
    async def slash_repeat(self, interaction: discord.Interaction, mode: str = "song") -> None:
        if not interaction.guild:
            return
        player = self.bot.get_player_in(interaction.guild)
        if not player:
            await interaction.response.send_message("Not connected to voice.", ephemeral=True)
            return

        if mode == "song":
            player.repeatsong = not player.repeatsong
            player.loopqueue = False
            status = "enabled" if player.repeatsong else "disabled"
            await interaction.response.send_message(f"🔂 Song repeat **{status}**")
        elif mode == "playlist":
            player.loopqueue = not player.loopqueue
            player.repeatsong = False
            status = "enabled" if player.loopqueue else "disabled"
            await interaction.response.send_message(f"🔁 Playlist repeat **{status}**")
        elif mode == "off":
            player.repeatsong = False
            player.loopqueue = False
            await interaction.response.send_message("⏹️ Repeat disabled")

    # ─── /seek ─────────────────────────────────────────────────────────────

    @app_commands.command(name="seek", description="Seek to a position in the current song")
    @app_commands.describe(time="Time in seconds or format like 1:30")
    async def slash_seek(self, interaction: discord.Interaction, time: str) -> None:
        if not interaction.guild:
            return
        player = self.bot.get_player_in(interaction.guild)
        if not player or not player.current_entry:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return

        from musicbot.utils import format_time_to_seconds
        from musicbot.entry import URLPlaylistEntry, LocalFilePlaylistEntry

        if not isinstance(player.current_entry, (URLPlaylistEntry, LocalFilePlaylistEntry)):
            await interaction.response.send_message("Cannot seek in streams.", ephemeral=True)
            return

        try:
            seek_seconds = float(format_time_to_seconds(time))
        except (ValueError, TypeError):
            await interaction.response.send_message(f"Invalid time format: `{time}`", ephemeral=True)
            return

        if player.current_entry.duration and (seek_seconds > player.current_entry.duration or seek_seconds < 0):
            await interaction.response.send_message("Seek time is out of range.", ephemeral=True)
            return

        entry = player.current_entry
        entry.set_start_time(seek_seconds)
        player.playlist.insert_entry_at_index(0, entry)
        player.skip()
        await interaction.response.send_message(f"⏩ Seeking to `{time}` ({seek_seconds:.0f}s)")

    # ─── /speed ────────────────────────────────────────────────────────────

    @app_commands.command(name="speed", description="Set playback speed")
    @app_commands.describe(rate="Speed rate (0.5 to 100.0)")
    async def slash_speed(self, interaction: discord.Interaction, rate: float) -> None:
        if not interaction.guild:
            return
        player = self.bot.get_player_in(interaction.guild)
        if not player or not player.current_entry:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return

        from musicbot.entry import URLPlaylistEntry, LocalFilePlaylistEntry

        if not isinstance(player.current_entry, (URLPlaylistEntry, LocalFilePlaylistEntry)):
            await interaction.response.send_message("Cannot change speed on streams.", ephemeral=True)
            return

        if not 0.5 <= rate <= 100.0:
            await interaction.response.send_message("Speed must be between 0.5 and 100.0", ephemeral=True)
            return

        entry = player.current_entry
        entry.set_start_time(player.progress)
        entry.set_playback_speed(rate)
        player.playlist.insert_entry_at_index(0, entry)
        player.skip()
        await interaction.response.send_message(f"⚡ Playback speed set to **{rate:.1f}x**")

    # ─── /help ─────────────────────────────────────────────────────────────

    @app_commands.command(name="help", description="Show available commands")
    async def slash_help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="🎵 Jeeves Music Bot — Commands",
            description="Here are the available slash commands:",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="🎶 Music",
            value=(
                "`/play` — Play a song\n"
                "`/playnext` — Add song to play next\n"
                "`/skip` — Skip current song\n"
                "`/pause` — Pause playback\n"
                "`/resume` — Resume playback\n"
                "`/volume` — Set volume (1-100)\n"
                "`/seek` — Seek to position\n"
                "`/speed` — Change playback speed\n"
            ),
            inline=True,
        )
        embed.add_field(
            name="📋 Queue",
            value=(
                "`/queue` — Show the queue\n"
                "`/np` — Now playing\n"
                "`/shuffle` — Shuffle queue\n"
                "`/clear` — Clear queue\n"
                "`/repeat` — Toggle repeat\n"
            ),
            inline=True,
        )
        embed.add_field(
            name="🔧 Control",
            value=(
                "`/summon` — Join your voice channel\n"
                "`/disconnect` — Leave voice\n"
            ),
            inline=True,
        )
        embed.set_footer(text="Maintained by Joshwaamein | github.com/Joshwaamein/MusicBot")
        await interaction.response.send_message(embed=embed)


async def setup(bot: "MusicBot") -> None:
    """Called by discord.py to load this cog."""
    cog = MusicCog(bot)
    bot.tree.add_command(cog.slash_play)
    bot.tree.add_command(cog.slash_playnext)
    bot.tree.add_command(cog.slash_skip)
    bot.tree.add_command(cog.slash_pause)
    bot.tree.add_command(cog.slash_resume)
    bot.tree.add_command(cog.slash_queue)
    bot.tree.add_command(cog.slash_np)
    bot.tree.add_command(cog.slash_volume)
    bot.tree.add_command(cog.slash_summon)
    bot.tree.add_command(cog.slash_disconnect)
    bot.tree.add_command(cog.slash_shuffle)
    bot.tree.add_command(cog.slash_clear)
    bot.tree.add_command(cog.slash_repeat)
    bot.tree.add_command(cog.slash_seek)
    bot.tree.add_command(cog.slash_speed)
    bot.tree.add_command(cog.slash_help)
    log.info("Loaded MusicCog with %d slash commands", 16)
