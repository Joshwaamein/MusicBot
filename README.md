# Jeeves — Discord Music Bot 🎵

> **Maintained by [Joshwaamein](https://github.com/Joshwaamein)**
> Forked from [Just-Some-Bots/MusicBot](https://github.com/Just-Some-Bots/MusicBot)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A Discord music bot that plays music from **YouTube**, **Spotify**, **SoundCloud**, and more directly into voice channels. Built with [Python](https://www.python.org) 3.8+ and [discord.py](https://github.com/Rapptz/discord.py).

## Features

- 🎶 Play music from YouTube, Spotify, SoundCloud, Bandcamp, and other services
- 📋 Queue system with shuffle, repeat, and playlist support
- 🔊 Volume control and playback speed adjustment
- 🎤 Karaoke mode
- 🔒 Permission system to restrict commands per user/role
- 📝 Auto-playlist for background music when the queue is empty
- 🌍 Multi-server support
- 🔄 Persistent queue (survives restarts)

## Quick Start

1. **Clone the repo:**
   ```bash
   git clone https://github.com/Joshwaamein/MusicBot.git
   cd MusicBot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the bot:**
   ```bash
   cp config/example_options.ini config/options.ini
   ```
   Edit `config/options.ini` and add your Discord bot token and (optionally) Spotify credentials.

4. **Run:**
   ```bash
   python3 run.py
   ```

## Commands

The default command prefix is `/`. Here are some common commands:

| Command | Description |
|---------|-------------|
| `/play <url or search>` | Play a song or add it to the queue |
| `/skip` | Skip the current song |
| `/queue` | Show the current queue |
| `/np` | Show what's currently playing |
| `/volume <1-100>` | Set the playback volume |
| `/pause` / `/resume` | Pause or resume playback |
| `/shuffle` | Shuffle the queue |
| `/repeat` | Toggle repeat mode |
| `/disconnect` | Leave the voice channel |
| `/help` | Show all available commands |

Full command list: [MusicBot Commands](https://just-some-bots.github.io/MusicBot/using/commands/)

## Changes in this fork

- Fixed yt-dlp compatibility with latest versions
- Secrets removed from repository (uses `config/options.ini.example` template)
- Synced with upstream MusicBot
- Updated README and documentation

## Configuration

The main configuration file is `config/options.ini` (not tracked by git). Copy the example to get started:

```bash
cp config/example_options.ini config/options.ini
```

You'll need:
- **Discord Bot Token** — from the [Discord Developer Portal](https://discord.com/developers/applications)
- **Spotify Client ID & Secret** (optional) — from the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)

## Further Reading

- [Setup Guide](https://just-some-bots.github.io/MusicBot/)
- [Original MusicBot](https://github.com/Just-Some-Bots/MusicBot)
- [Project License](LICENSE)
