FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libopus0 \
    libsodium23 \
    libffi-dev \
    git \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Add project source
WORKDIR /musicbot
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . ./
COPY ./config sample_config

# Create volumes for persistent data
VOLUME ["/musicbot/audio_cache", "/musicbot/config", "/musicbot/data", "/musicbot/logs"]

ENV APP_ENV=docker

ENTRYPOINT ["/bin/sh", "docker-entrypoint.sh"]
