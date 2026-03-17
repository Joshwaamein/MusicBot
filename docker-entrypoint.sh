#!/bin/sh
# ============================================================================
# docker-entrypoint.sh — MusicBot Docker Container Entrypoint
# Joshwaamein/MusicBot
#
# This script runs when the Docker container starts:
#   1. Copies example config files if no config exists yet
#   2. Launches MusicBot via run.py
# ============================================================================

# Copy example config if no config exists (first run)
if [ ! -f "/musicbot/config/example_options.ini" ]; then
    cp -r /musicbot/sample_config/* /musicbot/config
fi

# Start MusicBot (exec replaces shell process for clean signal handling)
exec python3 run.py "$@"
