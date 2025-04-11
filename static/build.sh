#!/usr/bin/env bash

# Instala FFmpeg
apt-get update && apt-get install -y ffmpeg

# Instala yt-dlp manualmente (última versión)
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
chmod a+rx /usr/local/bin/yt-dlp
