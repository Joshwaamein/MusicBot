"""
Slash command cog for core music commands.
These wrap the existing MusicBot cmd_* methods to provide Discord slash command support.
"""

import logging
import math
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands

if TYPE_CHECKING:
    from musicbot.bot import MusicBot

log = logging.getLogger(__name__)


async def setup(bot: "MusicBot") -> None:
    """Register slash commands on the bot's command tree."""

    @bot.tree.command(name="play", description="Play a song from YouTube, Spotify, or search by name")
    @app_commands.describe(song="A URL or search query for the song to play")
    async def slash_play(interaction: discord.Interaction, song: str) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("You need to be in a voice channel.", ephemeral=True)
            return
        await interaction.response.defer()
        try:
            guild = interaction.guild
            author = interaction.user
            channel = interaction.channel
            permissions = bot.permissions.for_user(author)
            _player = bot.get_player_in(guild)
            if not _player:
                _player = await bot.get_player(author.voice.channel, create=True)
            response = await bot._cmd_play(
                message=None, _player=_player, channel=channel, guild=guild,
                author=author, permissions=permissions, leftover_args=[], song_url=song, head=False,
            )
            if response and response.content:
                c = response.content
                if isinstance(c, discord.Embed):
                    await interaction.followup.send(embed=c)
                else:
                    await interaction.followup.send(str(c))
            else:
                await interaction.followup.send("🎶 Added to queue!")
        except Exception as e:
            await interaction.followup.send(f"❌ {getattr(e, 'message', str(e))}", ephemeral=True)

    @bot.tree.command(name="playnext", description="Add a song to play next in the queue")
    @app_commands.describe(song="A URL or search query")
    async def slash_playnext(interaction: discord.Interaction, song: str) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("You need to be in a voice channel.", ephemeral=True)
            return
        await interaction.response.defer()
        try:
            guild = interaction.guild
            author = interaction.user
            permissions = bot.permissions.for_user(author)
            _player = bot.get_player_in(guild)
            if not _player:
                _player = await bot.get_player(author.voice.channel, create=True)
            response = await bot._cmd_play(
                message=None, _player=_player, channel=interaction.channel, guild=guild,
                author=author, permissions=permissions, leftover_args=[], song_url=song, head=True,
            )
            if response and response.content:
                c = response.content
                await interaction.followup.send(str(c) if not isinstance(c, discord.Embed) else "", embed=c if isinstance(c, discord.Embed) else discord.utils.MISSING)
            else:
                await interaction.followup.send("🎶 Added to play next!")
        except Exception as e:
            await interaction.followup.send(f"❌ {getattr(e, 'message', str(e))}", ephemeral=True)

    @bot.tree.command(name="skip", description="Skip the current song")
    @app_commands.describe(force="Force skip (owner/instaskip only)")
    async def slash_skip(interaction: discord.Interaction, force: bool = False) -> None:
        if not interaction.guild:
            return
        player = bot.get_player_in(interaction.guild)
        if not player or not player.current_entry:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        entry = player.current_entry
        if player.repeatsong:
            player.repeatsong = False
        player.skip()
        await interaction.response.send_message(f"⏭️ Skipped **{entry.title}**")

    @bot.tree.command(name="pause", description="Pause the current song")
    async def slash_pause(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = bot.get_player_in(interaction.guild)
        if not player or not player.is_playing:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        player.pause()
        await interaction.response.send_message(f"⏸️ Paused")

    @bot.tree.command(name="resume", description="Resume playback")
    async def slash_resume(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = bot.get_player_in(interaction.guild)
        if not player or not player.is_paused:
            await interaction.response.send_message("Nothing is paused.", ephemeral=True)
            return
        player.resume()
        await interaction.response.send_message(f"▶️ Resumed")

    @bot.tree.command(name="queue", description="Show the current song queue")
    @app_commands.describe(page="Page number")
    async def slash_queue(interaction: discord.Interaction, page: int = 1) -> None:
        if not interaction.guild:
            return
        player = bot.get_player_in(interaction.guild)
        if not player or not player.playlist.entries:
            await interaction.response.send_message("The queue is empty.", ephemeral=True)
            return
        from musicbot.utils import format_song_duration
        entries = list(player.playlist.entries)
        total = len(entries)
        per_page = 10
        pages = math.ceil(total / per_page)
        page = max(1, min(page, pages))
        start = (page - 1) * per_page
        desc = ""
        if player.current_entry:
            prog = format_song_duration(player.progress)
            dur = format_song_duration(player.current_entry.duration_td) if player.current_entry.duration else "?"
            desc += f"🎵 **Now Playing:** {player.current_entry.title}\n`[{prog}/{dur}]`\n\n"
        desc += f"**Queue ({total} songs):**\n"
        for idx, item in enumerate(entries[start:start+per_page], start + 1):
            t = item.title[:50] + "..." if len(item.title) > 50 else item.title
            desc += f"`{idx}.` {t}\n"
        if pages > 1:
            desc += f"\n*Page {page}/{pages}*"
        embed = discord.Embed(title="🎶 Song Queue", description=desc, color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="np", description="Show the currently playing song")
    async def slash_np(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = bot.get_player_in(interaction.guild)
        if not player or not player.current_entry:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        from musicbot.utils import format_song_duration
        entry = player.current_entry
        prog = format_song_duration(player.progress)
        dur = format_song_duration(entry.duration_td) if entry.duration else "Live"
        pct = player.progress / entry.duration_td.total_seconds() if entry.duration and entry.duration_td.total_seconds() > 0 else 0
        filled = int(20 * pct)
        bar = "▓" * filled + "░" * (20 - filled)
        embed = discord.Embed(title="🎵 Now Playing", description=f"**{entry.title}**", color=discord.Color.green())
        if entry.author:
            embed.add_field(name="Added by", value=entry.author.name, inline=True)
        embed.add_field(name="Progress", value=f"`{bar}` {prog}/{dur}", inline=False)
        if entry.thumbnail_url:
            embed.set_thumbnail(url=entry.thumbnail_url)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="volume", description="Set or show the playback volume")
    @app_commands.describe(level="Volume level (1-100)")
    async def slash_volume(interaction: discord.Interaction, level: Optional[int] = None) -> None:
        if not interaction.guild:
            return
        player = bot.get_player_in(interaction.guild)
        if not player:
            await interaction.response.send_message("Not connected.", ephemeral=True)
            return
        if level is None:
            await interaction.response.send_message(f"🔊 Volume: **{int(player.volume*100)}%**")
            return
        if not 1 <= level <= 100:
            await interaction.response.send_message("Volume must be 1-100.", ephemeral=True)
            return
        old = int(player.volume * 100)
        player.volume = level / 100.0
        await interaction.response.send_message(f"🔊 Volume: **{old}%** → **{level}%**")

    @bot.tree.command(name="summon", description="Summon the bot to your voice channel")
    async def slash_summon(interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Join a voice channel first.", ephemeral=True)
            return
        await interaction.response.defer()
        try:
            player = bot.get_player_in(interaction.guild)
            if player and player.voice_client:
                await interaction.guild.change_voice_state(channel=interaction.user.voice.channel, self_deaf=bot.config.self_deafen)
            else:
                await bot.get_player(interaction.user.voice.channel, create=True)
            await interaction.followup.send(f"✅ Connected to **{interaction.user.voice.channel.name}**")
        except Exception as e:
            await interaction.followup.send(f"❌ {getattr(e, 'message', str(e))}", ephemeral=True)

    @bot.tree.command(name="disconnect", description="Disconnect from voice")
    async def slash_disconnect(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = bot.get_player_in(interaction.guild)
        if not player:
            await interaction.response.send_message("Not connected.", ephemeral=True)
            return
        await bot.disconnect_voice_client(interaction.guild)
        await interaction.response.send_message("👋 Disconnected.")

    @bot.tree.command(name="shuffle", description="Shuffle the queue")
    async def slash_shuffle(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = bot.get_player_in(interaction.guild)
        if not player or not player.playlist.entries:
            await interaction.response.send_message("Nothing to shuffle.", ephemeral=True)
            return
        player.playlist.shuffle()
        await interaction.response.send_message("🔀 Queue shuffled!")

    @bot.tree.command(name="clear", description="Clear the queue")
    async def slash_clear(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = bot.get_player_in(interaction.guild)
        if not player:
            await interaction.response.send_message("Not connected.", ephemeral=True)
            return
        player.playlist.clear()
        await interaction.response.send_message("🗑️ Queue cleared!")

    @bot.tree.command(name="repeat", description="Toggle repeat mode")
    @app_commands.describe(mode="Repeat mode")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Song", value="song"),
        app_commands.Choice(name="Playlist", value="playlist"),
        app_commands.Choice(name="Off", value="off"),
    ])
    async def slash_repeat(interaction: discord.Interaction, mode: str = "song") -> None:
        if not interaction.guild:
            return
        player = bot.get_player_in(interaction.guild)
        if not player:
            await interaction.response.send_message("Not connected.", ephemeral=True)
            return
        if mode == "song":
            player.repeatsong = not player.repeatsong
            player.loopqueue = False
            await interaction.response.send_message(f"🔂 Song repeat **{'enabled' if player.repeatsong else 'disabled'}**")
        elif mode == "playlist":
            player.loopqueue = not player.loopqueue
            player.repeatsong = False
            await interaction.response.send_message(f"🔁 Playlist repeat **{'enabled' if player.loopqueue else 'disabled'}**")
        else:
            player.repeatsong = False
            player.loopqueue = False
            await interaction.response.send_message("⏹️ Repeat disabled")

    @bot.tree.command(name="help", description="Show available commands")
    async def slash_help(interaction: discord.Interaction) -> None:
        embed = discord.Embed(title="🎵 Jeeves — Commands", color=discord.Color.blurple())
        embed.add_field(name="🎶 Music", value="`/play` `/playnext` `/skip` `/pause` `/resume` `/volume`", inline=True)
        embed.add_field(name="📋 Queue", value="`/queue` `/np` `/shuffle` `/clear` `/repeat`", inline=True)
        embed.add_field(name="🔧 Control", value="`/summon` `/disconnect`", inline=True)
        embed.set_footer(text="github.com/Joshwaamein/MusicBot")
        await interaction.response.send_message(embed=embed)

    log.info("Registered 16 slash commands on bot.tree")
