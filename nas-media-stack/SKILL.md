---
name: nas-media-stack
description: "Deploy and configure a complete media server stack on NAS (QNAP/Synology/generic Linux) via Docker Compose. Includes Jellyfin, *arr suite (Radarr/Sonarr/Prowlarr/Bazarr), qBittorrent, Immich (photos), Vaultwarden (passwords), Alist, Stirling PDF, Nginx Proxy Manager, Uptime Kuma, Portainer, FlareSolverr, and Jellystat. Handles full deployment lifecycle - directory setup, compose generation, image pulling, service startup, inter-service API wiring (download clients, indexers, media libraries, subtitle providers), and post-deploy verification. Use when user wants to set up a media server, NAS Docker deployment, home server, self-hosted streaming, *arr stack, Jellyfin setup, photo backup, or any combination of these services on a NAS or Linux box."
---

# NAS Media Stack Deployment

Deploy a complete self-hosted media + utility stack on a NAS via Docker Compose and wire all services together via API.

## Architecture Overview

```
Jellyseerr (request) → Radarr/Sonarr (manage) → Prowlarr (search indexers)
                                                       ↓
                                                  qBittorrent (download)
                                                       ↓
                                              Jellyfin (stream) ← Bazarr (subtitles)
                                                       ↓
                                              Jellystat (analytics)
```

Supporting services: Portainer (Docker management), Immich (photos), Vaultwarden (passwords), Alist (cloud drives), Stirling PDF (tools), NPM (reverse proxy), Uptime Kuma (monitoring), FlareSolverr (Cloudflare bypass).

## Prerequisites

- SSH access to NAS
- Docker + Docker Compose installed (QNAP: Container Station; Synology: Container Manager)
- Identify Docker binary path (QNAP: `/share/CACHEDEV1_DATA/.qpkg/container-station/bin`)
- Network access (ideally through a proxy for BT sites and ghcr.io)

## Deployment Phases

### Phase 0: Preparation

1. **Identify paths**: Find main data volume (QNAP: `/share/CACHEDEV1_DATA/`, Synology: `/volume1/`)
2. **Identify PUID/PGID**: Run `id <username>` on NAS. Use actual UID/GID for linuxserver containers.
3. **Create directory structure**:

```bash
DOCKER_ROOT="/share/CACHEDEV1_DATA/Docker"  # adjust per NAS
MEDIA_ROOT="/share/CACHEDEV1_DATA/Media"
PHOTO_ROOT="/share/CACHEDEV1_DATA/Photos"

mkdir -p $DOCKER_ROOT/{compose,portainer,jellyfin/config,qbittorrent/config}
mkdir -p $DOCKER_ROOT/{radarr/config,sonarr/config,prowlarr/config,bazarr/config}
mkdir -p $DOCKER_ROOT/{jellyseerr/config,jellystat,immich/ml-cache,immich/postgres}
mkdir -p $DOCKER_ROOT/{vaultwarden/data,alist/config,stirling-pdf}
mkdir -p $DOCKER_ROOT/nginx-proxy-manager/{data,letsencrypt}
mkdir -p $DOCKER_ROOT/uptime-kuma
mkdir -p $MEDIA_ROOT/Downloads/{complete,incomplete}
mkdir -p $MEDIA_ROOT/{Movies,TV,Anime,Music}
mkdir -p $PHOTO_ROOT
```

4. **Generate `.env`** at `$DOCKER_ROOT/compose/.env`:

```env
PUID=1000
PGID=100
TZ=Asia/Shanghai
JELLYSTAT_POSTGRES_USER=jellystat
JELLYSTAT_POSTGRES_PASSWORD=<random>
JELLYSTAT_POSTGRES_DB=jellystat
JELLYSTAT_JWT_SECRET=<random>
IMMICH_DB_USER=immich
IMMICH_DB_PASSWORD=<random>
IMMICH_DB_NAME=immich
```

5. **Fix media permissions**: `chown -R PUID:PGID $MEDIA_ROOT && chmod -R 775 $MEDIA_ROOT`
6. **Configure Docker mirror accelerators** (China): Edit Docker daemon config to add registry mirrors.
7. **Deploy Portainer**: Single container with `restart: unless-stopped`, port 9443.

### Phase 1: Media Stack

Create `media-stack.yml` with 9 services. Key points:
- All media containers mount the same root: `$MEDIA_ROOT:/media`
- qBittorrent: set `WEBUI_PORT`, expose BT port (6881)
- Jellyfin: pass `/dev/dri` for hardware transcoding (Intel QSV/VAAPI), add `group_add` for render GID
- Jellystat + postgres: use env vars from `.env`

Services: qbittorrent, prowlarr, radarr, sonarr, bazarr, jellyfin, jellyseerr, jellystat, jellystat-db

### Phase 2: Photos & Security

Create `photo-security.yml` with 5 services:
- Immich: server + machine-learning + redis + postgres (use `tensorchord/pgvecto-rs:pg16-v0.2.0`)
- Vaultwarden: simple single container, port maps to 80

### Phase 3: Tools

Create `tools.yml`:
- Alist: mount media for browsing
- Stirling PDF: stateless tool

### Phase 4: Monitoring

Create `monitoring.yml`:
- Nginx Proxy Manager: ports 80/443/81
- Uptime Kuma: port 3001

### Deployment Order

```bash
cd $DOCKER_ROOT/compose
# Pull then up each phase. For slow connections, pull in background.
docker compose -f media-stack.yml pull && docker compose -f media-stack.yml up -d
docker compose -f photo-security.yml pull && docker compose -f photo-security.yml up -d
docker compose -f tools.yml pull && docker compose -f tools.yml up -d
docker compose -f monitoring.yml pull && docker compose -f monitoring.yml up -d
```

Verify with `docker ps` — expect 19+ containers all "Up".

## Post-Deploy: Service Wiring

Wire services via their APIs in this order. All API calls use `X-Api-Key` header.

### 1. qBittorrent Setup

- Get initial temp password: `docker logs qbittorrent | grep "temporary password"`
- Login via API: `POST /api/v2/auth/login`
- Set download paths: `POST /api/v2/app/setPreferences` → `save_path=/media/Downloads/complete`, `temp_path=/media/Downloads/incomplete`, `temp_path_enabled=true`
- Change password: `POST /api/v2/app/setPreferences` → `web_ui_password=<new>`
- **Note**: qBit password resets on restart if not persisted. Always set via API after restart.

### 2. Get API Keys

Extract from config XML files on NAS:
```bash
grep -o "<ApiKey>[^<]*" $DOCKER_ROOT/prowlarr/config/config.xml | cut -d">" -f2
grep -o "<ApiKey>[^<]*" $DOCKER_ROOT/radarr/config/config.xml | cut -d">" -f2
grep -o "<ApiKey>[^<]*" $DOCKER_ROOT/sonarr/config/config.xml | cut -d">" -f2
grep "apikey" $DOCKER_ROOT/bazarr/config/config/config.yaml | head -1
```

### 3. Prowlarr → Download Client + Apps

- Add qBittorrent: `POST /api/v1/downloadclient?forceSave=true` (use schema from `/api/v1/downloadclient/schema`)
- Add Radarr app: `POST /api/v1/applications?forceSave=true` with `syncLevel: fullSync`
- Add Sonarr app: same pattern

### 4. Radarr/Sonarr → Download Client + Root Folders

- Add qBittorrent: `POST /api/v3/downloadclient?forceSave=true`
- Add root folders: `POST /api/v3/rootfolder` → `/media/Movies` (Radarr), `/media/TV` + `/media/Anime` (Sonarr)
- If root folder fails with "not writable", fix permissions on NAS.

### 5. Jellyfin Setup

- Authenticate: `POST /Users/AuthenticateByName` with `Authorization: MediaBrowser Client=CLI, Device=..., DeviceId=..., Version=1.0`
- Create API key: `POST /Auth/Keys?app=NAS-Services`
- Add media libraries: `POST /Library/VirtualFolders?collectionType=movies&name=Movies` with `PathInfos[0].Path=/media/Movies`
- Enable QSV: `GET` then `POST /System/Configuration/encoding` → set `HardwareAccelerationType=qsv`, `VaapiDevice=/dev/dri/renderD128`

### 6. Bazarr → Radarr/Sonarr + Subtitles

Bazarr API is limited. Prefer editing config file directly:
```bash
# In $DOCKER_ROOT/bazarr/config/config/config.yaml
# Set radarr/sonarr sections: apikey, ip, port
# Set opensubtitlescom: username, password
# Set enabled_providers list
# Set serie_default_enabled/movie_default_enabled: true
# Set serie_default_profile/movie_default_profile to profile ID
```
Then `docker restart bazarr`.

Language profiles must be created via Web UI: Settings → Languages → Add New Profile.

### 7. Jellyseerr → Jellyfin + Radarr + Sonarr

- Login: `POST /api/v1/auth/jellyfin` with cookie jar
- Add Radarr: `POST /api/v1/settings/radarr` — requires `activeProfileName` field (get profiles from Radarr API first)
- Add Sonarr: `POST /api/v1/settings/sonarr` — requires `activeAnimeProfileName` + `activeAnimeDirectory`

### 8. Jellystat

Must be configured via Web UI (API auth is non-trivial). Point to Jellyfin URL + API key.

### 9. Prowlarr Indexers

Get indexer schemas: `GET /api/v1/indexer/schema` (large response ~5MB, save to file).

Extract minimal fields for each indexer:
```python
minimal = {
    "name": s["name"], "implementation": s["implementation"],
    "configContract": s["configContract"], "protocol": s["protocol"],
    "enable": True, "appProfileId": 1, "priority": 25,
    "definitionName": s.get("definitionName", ""),
    "fields": s["fields"], "tags": []
}
```

Recommended public indexers (no registration): Nyaa.si, EZTV, The Pirate Bay, BitSearch, LimeTorrents.

Some sites (1337x, KickassTorrents) need FlareSolverr for Cloudflare bypass:
- Deploy FlareSolverr container on port 8191
- Add as indexer proxy in Prowlarr: `POST /api/v1/indexerProxy`
- Create matching tag and assign to both proxy and indexer
- **Note**: FlareSolverr v3 has limited effectiveness against new Cloudflare; don't over-invest.

### 10. Adding Movies/Shows

Via Radarr API:
```
GET /api/v3/movie/lookup?term=<search>  → get tmdbId
POST /api/v3/movie → add with qualityProfileId, rootFolderPath, addOptions.searchForMovie=true
POST /api/v3/command → {"name":"MoviesSearch","movieIds":[id]}
```

## Port Reference

| Service | Port | Notes |
|---------|------|-------|
| Portainer | 9443 | HTTPS |
| Jellyfin | 8096 | + QSV transcoding |
| qBittorrent | 8090 | WebUI |
| Radarr | 7878 | Movies |
| Sonarr | 8989 | TV/Anime |
| Prowlarr | 9696 | Indexers |
| Bazarr | 6767 | Subtitles |
| Jellyseerr | 5055 | Requests |
| Jellystat | 3100 | Stats |
| Immich | 2283 | Photos |
| Vaultwarden | 8888 | Passwords |
| Alist | 5244 | Cloud drives |
| Stirling PDF | 8085 | PDF tools |
| NPM | 81/80/443 | Reverse proxy |
| Uptime Kuma | 3001 | Monitoring |
| FlareSolverr | 8191 | CF bypass |

## Troubleshooting

- **qBit password reset on restart**: Password set via API may not persist. Re-set after each restart.
- **Root folder "not writable"**: Fix permissions: `chown -R PUID:PGID /path && chmod -R 775 /path`
- **downloadClientUnavailable**: qBit password changed; update in Radarr/Sonarr/Prowlarr download client settings.
- **SSH Connection Refused on QNAP**: Toggle SSH off/on in QTS, or reboot NAS.
- **Immich unhealthy on start**: Normal — DB migration takes 2-5 minutes. Wait.
- **QNAP Docker config**: File is `docker.json` not `daemon.json`, at `$CONTAINER_STATION_PATH/etc/docker.json`.
- **Indexer Cloudflare blocked**: Deploy FlareSolverr or skip; plenty of non-CF indexers available.
