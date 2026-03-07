---
name: nas-media-download
description: Search, download and manage media on NAS via Prowlarr/qBittorrent/Radarr/Sonarr/Jellyfin. Use when user asks to find, download, or manage movies/TV shows on their NAS media server. Handles searching indexers, presenting results, downloading via qBittorrent, and triggering Jellyfin library scans.
---

# NAS Media Download

## Overview
Search and download media to NAS, auto-import to Jellyfin.
Default behavior is confirmation-first: search, rank, recommend, wait for selection, then download.

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

## Default Interaction Rule
- When the user says `download`, `下这个`, `帮我下`, or otherwise asks to download media, do **not** immediately start the download.
- Always search first, rank the candidates, and present a shortlist to the user.
- The user must explicitly choose a result by number or exact title before any download begins.
- Only skip this confirmation step if the user clearly identifies a previously listed result (for example: `下第6个`, `下载刚才那个 4K Remux`).
- Once a shortlist is shown, treat it as a frozen result snapshot for that interaction. Do not remap the user's number against a fresh live search.
- If the original chosen result is no longer available, say so clearly and ask the user to pick again from a refreshed list.

### Step 1: Determine Media Type
- Movie keywords: 电影, movie, 片子, BluRay, Remux, 1080p, 2160p, 年份明确的单片
- TV keywords: 剧, TV, series, season, S01, EP, 全集, 连载
- Movie → use Prowlarr search, then add the chosen release to Radarr
- TV Show → use Prowlarr search, then add the chosen release or series to Sonarr
- If ambiguous, ask one short follow-up question only after presenting the best inferred guess

### Step 2: Search via Prowlarr API
```bash
GET http://192.168.10.45:9696/api/v1/search?query={title}&type=search
Header: X-Api-Key: {prowlarr_api_key}
```

Parse results and present to user as a ranked shortlist with:
- Number
- Stable result ID (internal snapshot ID, not shown unless needed)
- Title
- Size (human readable)
- Seeders
- Source indexer
- Quality (parse from title: resolution, codec, HDR, audio)
- Subtitle info (if in title)

Sort by seeders descending, show the top 10-20 results depending on noise level.
Deduplicate obviously identical releases from different indexers when possible.
Persist the exact shortlist used for display as the authoritative snapshot for follow-up commands like `下第6个`.
Always include a brief recommendation section such as:
- Best value
- Best quality
- Best subtitle-friendly release
- Best compact 4K release

Preferred reply format:
1. `#1 Title ...`
2. `#2 Title ...`
3. `#3 Title ...`

Each item should include short inline notes for size, seeders, source, and standout traits.

### Step 3: User Selection
Wait for the user to pick a result by number or exact title.
Resolve the choice against the stored shortlist snapshot from the previous reply, not a fresh search.
Do not begin downloading until the user explicitly confirms the choice.
If the user references a number but no snapshot is available, re-run the search and present a new numbered list instead of guessing.

### Step 4: Download via qBittorrent
Option A (preferred): Add the chosen movie to Radarr or the chosen show to Sonarr for automated management.
Option B (manual fallback): Add magnet/torrent directly to qBit via API.

Rules:
- Never start a download from the shortlist unless the user has selected a result.
- If the user says `下载这个` while replying to a previously listed result, treat that as valid confirmation.
- For movies, prefer Radarr so the final file is renamed and imported cleanly.
- For shows, prefer Sonarr so season/episode structure stays correct.
- Before sending a download command, verify that the chosen release title still matches the stored snapshot entry.
- If the cached result expired or the client cannot fetch that exact release, stop and tell the user the exact chosen item is no longer available; do not silently substitute a different one.

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

Progress policy:
- Do not spam routine progress updates.
- Report when one of these happens:
  - download is accepted into queue
  - metadata is resolved and real download starts
  - download completes
  - import fails or stalls
  - user explicitly asks for status

### Step 6: Post-Download
1. Verify file in the target media directory
2. Trigger Jellyfin library scan:
   ```bash
   POST http://192.168.10.45:8096/Library/Refresh
   Header: X-Emby-Token: {jellyfin_api_key}
   ```
3. Let Bazarr fetch subtitles automatically
4. Send a completion message including:
   - media title
   - final imported path
   - file size
   - whether Jellyfin scan was triggered
   - whether subtitles are pending or found

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
→ Present top ranked results with numbered recommendations
→ User picks one
→ Add to Radarr
→ Monitor queue and confirm import
→ Trigger Jellyfin scan and report completion

User: "下载《爱乐之城》"
→ Do not download immediately
→ Search first and present numbered choices
→ Wait for confirmation such as `下第3个`
→ Start the chosen release only after confirmation

User: "帮我找一下绝命毒师第一季"
→ Detect TV workflow
→ Search and route the chosen result to Sonarr
→ Confirm season import and Jellyfin update
