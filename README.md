# Jeeves — Discord Music Bot 🎵

> **Maintained by [Joshwaamein](https://github.com/Joshwaamein)**
> Forked from [Just-Some-Bots/MusicBot](https://github.com/Just-Some-Bots/MusicBot)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![discord.py](https://img.shields.io/badge/discord.py-latest-7289da.svg)](https://github.com/Rapptz/discord.py)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A feature-rich Discord music bot with **48 slash commands**, **Spotify radio**, and support for YouTube, SoundCloud, Bandcamp, and more. Built with [Python](https://www.python.org) and [discord.py](https://github.com/Rapptz/discord.py).

---

## ✨ Features

### 🎶 Music Playback
- Play from **YouTube**, **Spotify**, **SoundCloud**, **Bandcamp**, and [many more](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- Search for songs by name or paste a URL
- Stream live audio without pre-downloading
- Adjustable playback **speed** (0.5x – 100x) and **volume** (1–100%)
- **Seek** to any position in a track

### 📻 Spotify Radio
- `/radio` — Start an endless radio station seeded from any song or artist
- Discovers similar music using Spotify playlists, genre search, and artist catalogs
- **Auto-refill** — automatically queues more songs when the queue runs low
- Stop anytime with `/radio action:Stop` or `/clear`

### 📋 Queue Management
- Add songs to the front (`/playnext`) or play immediately (`/playnow`)
- **Shuffle**, **repeat** (single track or entire queue), and **clear** the queue
- Persistent queue that survives bot restarts
- Round-robin mode for fair multi-user queuing

### 🎤 Extra Features
- **Karaoke mode** — vocal removal for sing-along
- **Auto-playlist** — background music when the queue is empty
- **Follow mode** — bot follows a user between voice channels

### 🔒 Administration
- Per-user and per-role **permission system**
- **User blocklist** and **song blocklist**
- Per-server command prefix customization
- Remote **restart** and **reboot** commands
- Bot name, avatar, and nickname management

### 🌍 Deployment
- **Multi-server** support out of the box
- **Docker** ready with included Dockerfile
- **systemd** service for production Linux deployments
- Cross-platform: Linux, macOS, Windows

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/Joshwaamein/MusicBot.git
cd MusicBot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Requires:** Python 3.8+ and [FFmpeg](https://ffmpeg.org/download.html)

### 3. Configure the bot

```bash
cp config/example_options.ini config/options.ini
```

Edit `config/options.ini` and add:
- **Discord Bot Token** — from the [Discord Developer Portal](https://discord.com/developers/applications)
- **Spotify Client ID & Secret** (optional, enables `/radio`) — from the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)

### 4. Run

```bash
python3 run.py
```

---

## 📖 Commands

All commands use Discord's native **slash command** system. Type `/` in any channel to see them.

### 🎵 Music Playback

| Command | Description |
|---------|-------------|
| `/play <song>` | Play a song from YouTube, Spotify, or search by name |
| `/playnext <song>` | Add a song to play next in the queue |
| `/playnow <song>` | Play a song immediately, skipping the current one |
| `/shuffleplay <song>` | Play a song and shuffle it into a random queue position |
| `/stream <url>` | Stream from a URL (no pre-download) |
| `/search <query>` | Search for a song and choose from results |
| `/pause` | Pause the current song |
| `/resume` | Resume playback |
| `/skip [force:True]` | Skip the current song; `force:True` bypasses vote-skip (owner/instaskip only) |
| `/seek <time>` | Seek to a position (e.g. `1:30`, `+30`, `-15`) |
| `/speed <rate>` | Set playback speed (e.g. `0.5`, `1.0`, `2.0`) |
| `/volume [level]` | Set or show the playback volume (1–100) |
| `/np` | Show the currently playing song |
| `/summon` | Summon the bot to your voice channel |
| `/disconnect` | Disconnect from voice |

### 📻 Radio / DJ

| Command | Description |
|---------|-------------|
| `/radio seed:<song or artist>` | Start a Spotify radio station based on a song or artist |
| `/radio action:Stop` | Stop the radio and clear the queue |

### 📋 Queue & Playlist

| Command | Description |
|---------|-------------|
| `/queue [page]` | Show the current song queue |
| `/shuffle` | Shuffle the queue |
| `/clear` | Clear the queue (also stops radio if active) |
| `/repeat [mode]` | Toggle repeat: `song`, `all`, `on`, `off` |
| `/autoplaylist <action>` | Manage the auto-playlist (add/remove/show) |
| `/resetplaylist` | Reset the auto-playlist to default |
| `/karaoke` | Toggle karaoke mode |

### ⚙️ Configuration

| Command | Description |
|---------|-------------|
| `/config <option> [value]` | View or change bot configuration |
| `/option <option> <value>` | Toggle a bot option on/off |
| `/setprefix <prefix>` | Set a custom command prefix for this server |
| `/setnick [nick]` | Set the bot's nickname on this server |
| `/setname <name>` | Change the bot's username |
| `/setavatar <url>` | Change the bot's avatar |
| `/setperms [action]` | View or change bot permissions groups |
| `/follow [user]` | Tell the bot to follow a user between voice channels |

### 🛡️ Moderation

| Command | Description |
|---------|-------------|
| `/blockuser <action> <user>` | Block or unblock a user from using the bot |
| `/blocksong <action> <subject>` | Block or unblock a song/URL from being played |
| `/clean [count]` | Clean up bot messages from the channel |
| `/pldump <url>` | Dump all URLs from a playlist link |

### ℹ️ Info & Admin

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/uptime` | Show how long the bot has been running |
| `/latency` | Show API and voice latency |
| `/botlatency` | Show detailed latency for all voice connections |
| `/botversion` | Show the current bot version |
| `/perms [user]` | Show permissions for a user |
| `/id [user]` | Show the ID of a user or yourself |
| `/listids [category]` | List server/channel/role/user IDs |
| `/restart [mode]` | Restart the bot — modes: `soft` (reload config), `full` (restart process), `upgrade` (all), `uppip` (pip packages only), `upgit` (git pull only) |
| `/reboot confirm:yes` | Reboot the server (requires confirmation) |
| `/joinserver` | Generate an invite link to add the bot to another server |
| `/leaveserver <server>` | Make the bot leave a server |
| `/cache [action]` | Manage the audio cache — actions: `info` (show stats), `update` (rebuild), `clear` (delete cached files). Requires server admin. |

---

## 📻 Spotify Radio

The `/radio` command creates an endless radio station powered by Spotify's music catalog.

**How it works:**
1. You provide a seed — a song name, artist name, or Spotify track URL
2. The bot plays your requested song first
3. It discovers similar music using:
   - Curated Spotify playlists (e.g. "Artist Radio" playlists)
   - Genre-based track search
   - Artist top tracks and album deep cuts
4. When the queue runs low (≤3 songs), it automatically fetches more

**Examples:**
```
/radio seed:Daft Punk - Get Lucky
/radio seed:The Weeknd
/radio seed:https://open.spotify.com/track/2dpaYNEQHiRxtZbfNsse99
/radio action:Stop
```

> **Note:** Requires Spotify Client ID and Secret in `config/options.ini`.

---

## 🐳 Deployment

### Option 1: Bare Metal (systemd)

```bash
# Install dependencies
pip install -r requirements.txt

# Configure
cp config/example_options.ini config/options.ini
# Edit config/options.ini with your tokens

# Create a systemd service
sudo cp musicbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable musicbot
sudo systemctl start musicbot
```

### Option 2: Docker

```bash
# Build the image
docker build -t jeeves-musicbot .

# Run with docker-compose (copy the example first)
cp docker-compose.example.yml docker-compose.yml
# Edit docker-compose.yml as needed
docker-compose up -d
```

---

## ⚙️ Configuration

The main configuration file is `config/options.ini` (not tracked by git). Key settings:

| Setting | Description |
|---------|-------------|
| `Token` | Your Discord bot token (**required**) |
| `Spotify_ClientID` | Spotify app client ID (enables `/radio`) |
| `Spotify_ClientSecret` | Spotify app client secret |
| `CommandPrefix` | Default command prefix (default: `/`) |
| `DefaultVolume` | Default volume 0.01–1.0 (default: `0.25`) |
| `AutoSummon` | Auto-join owner's voice channel on startup |
| `UseAutoPlaylist` | Play background music when queue is empty |
| `SaveVideos` | Cache downloaded audio to disk |
| `DeleteMessages` | Auto-cleanup bot messages |
| `LeaveInactiveVC` | Leave voice when channel is empty |

See `config/example_options.ini` for the full list of options with descriptions.

---

## 📁 Project Structure

```
MusicBot/
├── musicbot/
│   ├── bot.py              # Core bot logic, event handlers, command methods
│   ├── cogs/
│   │   └── music.py        # All 48 slash command definitions
│   ├── spotify.py           # Spotify API client (search, radio discovery)
│   ├── player.py            # Audio player and playback management
│   ├── playlist.py          # Queue/playlist management
│   ├── downloader.py        # yt-dlp wrapper for audio extraction
│   ├── config.py            # Configuration parser
│   ├── permissions.py       # Permission system
│   ├── entry.py             # Track entry types
│   └── ...
├── config/
│   ├── example_options.ini  # Configuration template
│   └── example_permissions.ini
├── tests/                   # Test suite (pytest)
├── Dockerfile               # Docker build
├── run.py                   # Entry point
├── requirements.txt         # Python dependencies
└── README.md
```

---

## 🔀 What's Different from Upstream

This fork ([Joshwaamein/MusicBot](https://github.com/Joshwaamein/MusicBot)) adds significant enhancements over the original [Just-Some-Bots/MusicBot](https://github.com/Just-Some-Bots/MusicBot):

- **Full slash command migration** — All 48 commands use Discord's native slash command system (no more text prefix commands)
- **Spotify Radio** (`/radio`) — Endless radio stations powered by Spotify's music catalog
- **Docker support** — Production-ready Dockerfile with Python 3.10-slim
- **systemd service** — Hardened service file for Linux deployments
- **Test suite** — pytest-based tests for command registration and response handling
- **Input validation** — All slash commands validate and sanitize user input
- **Bug fixes** — yt-dlp compatibility, voice reconnection, embed formatting
- **Codebase cleanup** — Removed dead code, unused files, and fixed references
- **Security** — All secrets removed from repository, proper `.gitignore` coverage

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run the tests (`pytest`)
5. Commit (`git commit -m "Add my feature"`)
6. Push (`git push origin feature/my-feature`)
7. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 🙏 Credits

- Original bot: [Just-Some-Bots/MusicBot](https://github.com/Just-Some-Bots/MusicBot)
- Discord library: [discord.py](https://github.com/Rapptz/discord.py)
- Audio extraction: [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- Music discovery: [Spotify Web API](https://developer.spotify.com/documentation/web-api)
