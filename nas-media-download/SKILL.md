---
name: nas-media-download
description: Search, download and manage media on NAS via Prowlarr/qBittorrent/Radarr/Sonarr/Jellyfin. Use when user asks to find, download, or manage movies/TV shows on their NAS media server. Handles searching indexers, presenting results, downloading via qBittorrent, and triggering Jellyfin library scans.
---

# NAS Media Download

## Overview
Search and download media to NAS, auto-import to Jellyfin.

## Environment
- NAS IP: 192.168.10.45 (SSH as admin)
- Prowlarr: http://192.168.10.45:9696 (API Key: read from /share/CACHEDEV1_DATA/Docker/prowlarr/config/config.xml)
- Radarr: http://192.168.10.45:7878 (API Key: read from config)
- Sonarr: http://192.168.10.45:8989 (API Key: read from config)
- qBittorrent: http://192.168.10.45:8090
- Jellyfin: http://192.168.10.45:8096
- Media directory: /share/Media/Movies/ and /share/Media/TV/
- Bazarr handles subtitles (Chinese/Japanese/English)

## Workflow

### Step 1: Determine Media Type
- Movie → use Prowlarr search or Radarr
- TV Show → use Prowlarr search or Sonarr

### Step 2: Search via Prowlarr API
```bash
GET http://192.168.10.45:9696/api/v1/search?query={title}&type=search
Header: X-Api-Key: {prowlarr_api_key}
```

Parse results and present to user as table:
- Title
- Size (human readable)
- Seeders
- Source indexer
- Quality (parse from title: resolution, codec, HDR, audio)
- Subtitle info (if in title)

Sort by seeders descending, show top 20.

### Step 3: User Selection
Wait for user to pick a result by number.

### Step 4: Download via qBittorrent
Option A (preferred): Add to Radarr/Sonarr for automated management
Option B (manual): Add magnet/torrent directly to qBit via API

qBit API:
- Login: POST /api/v2/auth/login
- Add torrent: POST /api/v2/torrents/add (with magnet URL or .torrent)
- Set category: movies or tv
- Set save path: /share/Media/Movies/ or /share/Media/TV/

### Step 5: Monitor Download
Poll qBit API for progress:
```bash
GET /api/v2/torrents/info?hashes={hash}
```
Report progress to user when asked or when complete.

### Step 6: Post-Download
1. Verify file in media directory
2. Trigger Jellyfin library scan:
   ```bash
   POST http://192.168.10.45:8096/Library/Refresh
   Header: X-Emby-Token: {jellyfin_api_key}
   ```
3. Bazarr will auto-fetch subtitles

### Step 7: Seeding Rules (Pre-configured)
- Max ratio: 1.0 (upload = download amount)
- Max seed time: 24 hours
- Action when limit reached: Pause torrent

## API Key Discovery
API keys are stored in each app's config.xml on NAS:
```bash
ssh admin@192.168.10.45 "grep -o '<ApiKey>[^<]*</ApiKey>' /share/CACHEDEV1_DATA/Docker/{app}/config/config.xml"
```

Replace {app} with: prowlarr, radarr, sonarr

For Jellyfin API key, check:
```bash
ssh admin@192.168.10.45 "cat /share/CACHEDEV1_DATA/Docker/jellyfin/config/data/jellyfin.db" # or use Jellyfin API
```

## Limitations
- Only use user's pre-configured public indexers in Prowlarr
- Do not add new indexer sources or PT sites
- Do not search for or download illegal/prohibited content
- Present results objectively; user makes final download decision

## Example Usage
User: "帮我搜一下《星际穿越》"
→ Search Prowlarr for "Interstellar 2014"
→ Present top 20 results sorted by seeders
→ User picks one
→ Download via qBit or add to Radarr
→ Confirm Jellyfin library updated
