---
name: yt-audio-dl
description: Batch download YouTube channel audio for AI processing. Discover channels, fetch video lists, download with yt-dlp, downsample to 16kHz mono M4A. Supports resume, progress tracking, and archiving. Use when downloading YouTube audio, building audio datasets, or preparing files for Whisper transcription.
metadata: {"clawdis":{"emoji":"🎵","requires":{"bins":["ffmpeg","python3"],"pip":["yt-dlp"]}}}
---

# YouTube Audio Downloader

Batch download YouTube channel audio, optimized for AI/Whisper processing.

## Quick Start

### Download a single video
```bash
python3 {baseDir}/scripts/yt_audio_dl.py download <video_id> --output-dir /path/to/output
```

### Download from a channel (auto-discover videos)
```bash
python3 {baseDir}/scripts/yt_audio_dl.py channel <channel_id_or_name> --max 60 --output-dir /path/to/output
```

### Search channel ID by name
```bash
python3 {baseDir}/scripts/yt_audio_dl.py search "Meet Kevin"
```

### Batch download from a JSON video list
```bash
python3 {baseDir}/scripts/yt_audio_dl.py batch /path/to/videos.json --output-dir /path/to/output
```

### Check progress
```bash
python3 {baseDir}/scripts/yt_audio_dl.py status /path/to/output
```

## Output Format

- **Format**: M4A (AAC)
- **Sample rate**: 16kHz (Whisper optimal)
- **Channels**: Mono
- **Bitrate**: 64kbps
- **Naming**: `{video_id}.m4a`

Typical size: 5-15MB per 10-minute video.

## Video List JSON Format

```json
{
  "channel_id": "UC...",
  "channel_name": "Channel Name",
  "videos": [
    {"video_id": "abc123", "title": "Video Title", "published_at": "2026-01-01T00:00:00Z"}
  ]
}
```

Also accepts a flat array of `{"video_id": "..."}` objects.

## Features

- **Resume**: Skips already-downloaded files (>10KB)
- **Auto-discover**: Fetches video lists via YouTube Data API v3
- **Downsample**: ffmpeg 16kHz mono AAC 64kbps (Whisper-optimal)
- **Cookies**: Supports `cookies.txt` for age-restricted content
- **Progress**: Prints progress every 10 videos to stdout

## Environment Variables

- `YOUTUBE_API_KEY` — Required for channel discovery and video list fetching
- `YT_COOKIES_FILE` — Optional path to cookies.txt (for restricted videos)

## Notes

- yt-dlp must be kept up to date (YouTube changes nsig encryption frequently). Run `pip install -U yt-dlp` regularly.
- YouTube Data API free tier: 10,000 units/day. Each search request costs ~100 units.
- For large batches, use cron with `--delete-after-run` for auto-cleanup.
