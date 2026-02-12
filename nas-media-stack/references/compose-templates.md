# Docker Compose Templates

Reference compose files. Adjust `DOCKER_ROOT` paths per NAS platform.

## media-stack.yml

```yaml
services:
  qbittorrent:
    image: linuxserver/qbittorrent:latest
    container_name: qbittorrent
    restart: unless-stopped
    environment:
      - PUID=${PUID}
      - PGID=${PGID}
      - TZ=${TZ}
      - WEBUI_PORT=8090
    ports:
      - "8090:8090"
      - "6881:6881"
      - "6881:6881/udp"
    volumes:
      - ${DOCKER_ROOT}/qbittorrent/config:/config
      - ${MEDIA_ROOT}:/media

  prowlarr:
    image: linuxserver/prowlarr:latest
    container_name: prowlarr
    restart: unless-stopped
    environment:
      - PUID=${PUID}
      - PGID=${PGID}
      - TZ=${TZ}
    ports:
      - "9696:9696"
    volumes:
      - ${DOCKER_ROOT}/prowlarr/config:/config

  radarr:
    image: linuxserver/radarr:latest
    container_name: radarr
    restart: unless-stopped
    environment:
      - PUID=${PUID}
      - PGID=${PGID}
      - TZ=${TZ}
    ports:
      - "7878:7878"
    volumes:
      - ${DOCKER_ROOT}/radarr/config:/config
      - ${MEDIA_ROOT}:/media

  sonarr:
    image: linuxserver/sonarr:latest
    container_name: sonarr
    restart: unless-stopped
    environment:
      - PUID=${PUID}
      - PGID=${PGID}
      - TZ=${TZ}
    ports:
      - "8989:8989"
    volumes:
      - ${DOCKER_ROOT}/sonarr/config:/config
      - ${MEDIA_ROOT}:/media

  bazarr:
    image: linuxserver/bazarr:latest
    container_name: bazarr
    restart: unless-stopped
    environment:
      - PUID=${PUID}
      - PGID=${PGID}
      - TZ=${TZ}
    ports:
      - "6767:6767"
    volumes:
      - ${DOCKER_ROOT}/bazarr/config:/config
      - ${MEDIA_ROOT}:/media

  jellyfin:
    image: jellyfin/jellyfin:latest
    container_name: jellyfin
    restart: unless-stopped
    environment:
      - TZ=${TZ}
    ports:
      - "8096:8096"
    volumes:
      - ${DOCKER_ROOT}/jellyfin/config:/config
      - ${MEDIA_ROOT}:/media
    devices:
      - /dev/dri:/dev/dri
    group_add:
      - "105"  # render group GID, verify on NAS

  jellyseerr:
    image: fallenbagel/jellyseerr:latest
    container_name: jellyseerr
    restart: unless-stopped
    environment:
      - TZ=${TZ}
    ports:
      - "5055:5055"
    volumes:
      - ${DOCKER_ROOT}/jellyseerr/config:/app/config

  jellystat:
    image: cyfershepard/jellystat:latest
    container_name: jellystat
    restart: unless-stopped
    environment:
      - TZ=${TZ}
      - POSTGRES_USER=${JELLYSTAT_POSTGRES_USER}
      - POSTGRES_PASSWORD=${JELLYSTAT_POSTGRES_PASSWORD}
      - POSTGRES_DB=${JELLYSTAT_POSTGRES_DB}
      - POSTGRES_IP=jellystat-db
      - POSTGRES_PORT=5432
      - JWT_SECRET=${JELLYSTAT_JWT_SECRET}
    ports:
      - "3100:3000"
    depends_on:
      - jellystat-db

  jellystat-db:
    image: postgres:15-alpine
    container_name: jellystat-db
    restart: unless-stopped
    environment:
      - POSTGRES_USER=${JELLYSTAT_POSTGRES_USER}
      - POSTGRES_PASSWORD=${JELLYSTAT_POSTGRES_PASSWORD}
      - POSTGRES_DB=${JELLYSTAT_POSTGRES_DB}
    volumes:
      - ${DOCKER_ROOT}/jellystat/db:/var/lib/postgresql/data
```

## photo-security.yml

```yaml
services:
  immich-server:
    image: ghcr.io/immich-app/immich-server:release
    container_name: immich-server
    restart: unless-stopped
    environment:
      - TZ=${TZ}
      - DB_HOSTNAME=immich-postgres
      - DB_USERNAME=${IMMICH_DB_USER}
      - DB_PASSWORD=${IMMICH_DB_PASSWORD}
      - DB_DATABASE_NAME=${IMMICH_DB_NAME}
      - REDIS_HOSTNAME=immich-redis
    ports:
      - "2283:2283"
    volumes:
      - ${PHOTO_ROOT}:/usr/src/app/upload
    depends_on:
      - immich-redis
      - immich-postgres

  immich-machine-learning:
    image: ghcr.io/immich-app/immich-machine-learning:release
    container_name: immich-ml
    restart: unless-stopped
    volumes:
      - ${DOCKER_ROOT}/immich/ml-cache:/cache

  immich-redis:
    image: redis:7-alpine
    container_name: immich-redis
    restart: unless-stopped

  immich-postgres:
    image: tensorchord/pgvecto-rs:pg16-v0.2.0
    container_name: immich-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_USER=${IMMICH_DB_USER}
      - POSTGRES_PASSWORD=${IMMICH_DB_PASSWORD}
      - POSTGRES_DB=${IMMICH_DB_NAME}
      - POSTGRES_INITDB_ARGS=--data-checksums
    volumes:
      - ${DOCKER_ROOT}/immich/postgres:/var/lib/postgresql/data

  vaultwarden:
    image: vaultwarden/server:latest
    container_name: vaultwarden
    restart: unless-stopped
    environment:
      - TZ=${TZ}
    ports:
      - "8888:80"
    volumes:
      - ${DOCKER_ROOT}/vaultwarden/data:/data
```

## tools.yml

```yaml
services:
  alist:
    image: xhofe/alist:latest
    container_name: alist
    restart: unless-stopped
    environment:
      - TZ=${TZ}
    ports:
      - "5244:5244"
    volumes:
      - ${DOCKER_ROOT}/alist/config:/opt/alist/data
      - ${MEDIA_ROOT}:/media

  stirling-pdf:
    image: frooodle/s-pdf:latest
    container_name: stirling-pdf
    restart: unless-stopped
    environment:
      - TZ=${TZ}
    ports:
      - "8085:8080"
    volumes:
      - ${DOCKER_ROOT}/stirling-pdf:/usr/share/tessdata
```

## monitoring.yml

```yaml
services:
  nginx-proxy-manager:
    image: jc21/nginx-proxy-manager:latest
    container_name: npm
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "81:81"
    volumes:
      - ${DOCKER_ROOT}/nginx-proxy-manager/data:/data
      - ${DOCKER_ROOT}/nginx-proxy-manager/letsencrypt:/etc/letsencrypt

  uptime-kuma:
    image: louislam/uptime-kuma:latest
    container_name: uptime-kuma
    restart: unless-stopped
    ports:
      - "3001:3001"
    volumes:
      - ${DOCKER_ROOT}/uptime-kuma:/app/data
```
