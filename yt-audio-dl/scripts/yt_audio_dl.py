#!/usr/bin/env python3
"""
YouTube Audio Downloader — batch download + downsample for AI processing.

Usage:
  python3 yt_audio_dl.py download <video_id> [--output-dir DIR]
  python3 yt_audio_dl.py channel <channel_id> [--max N] [--output-dir DIR]
  python3 yt_audio_dl.py search <query>
  python3 yt_audio_dl.py batch <json_file> [--output-dir DIR]
  python3 yt_audio_dl.py status <dir>
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime


# ── Config ──────────────────────────────────────────────────────────────

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
COOKIES_FILE = os.environ.get("YT_COOKIES_FILE", "")

DOWNSAMPLE_ARGS = [
    "-ac", "1",        # mono
    "-ar", "16000",    # 16kHz
    "-c:a", "aac",     # AAC codec
    "-b:a", "64k",     # 64kbps
]


# ── Core Functions ──────────────────────────────────────────────────────

def download_one(video_id: str, output_dir: Path) -> str:
    """Download a single video's audio. Returns 'ok', 'skip', or 'fail'."""
    final = output_dir / f"{video_id}.m4a"
    if final.exists() and final.stat().st_size > 10_000:
        return "skip"

    raw = output_dir / f"{video_id}_raw.m4a"
    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        import yt_dlp
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": str(raw),
            "quiet": True,
            "no_warnings": True,
            "force_ipv4": True,
        }
        if COOKIES_FILE and Path(COOKIES_FILE).exists():
            ydl_opts["cookiefile"] = COOKIES_FILE

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Find actual downloaded file
        actual = None
        for ext in [".m4a", ".webm", ".opus", ".mp4"]:
            c = raw.with_suffix(ext)
            if c.exists():
                actual = c
                break
        if not actual and raw.exists():
            actual = raw
        if not actual:
            return "fail"

        # Downsample
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(actual)] + DOWNSAMPLE_ARGS + [str(final)],
            capture_output=True, check=True, timeout=120,
        )
        actual.unlink(missing_ok=True)
        return "ok"

    except Exception as e:
        print(f"  ERROR {video_id}: {e}", file=sys.stderr)
        for ext in [".m4a", ".webm", ".opus", ".mp4", ".part"]:
            raw.with_suffix(ext).unlink(missing_ok=True)
        return "fail"


def search_channel(query: str) -> list:
    """Search for YouTube channels by name."""
    if not YOUTUBE_API_KEY:
        print("ERROR: YOUTUBE_API_KEY not set", file=sys.stderr)
        return []

    url = (
        f"https://www.googleapis.com/youtube/v3/search"
        f"?key={YOUTUBE_API_KEY}"
        f"&q={urllib.parse.quote(query)}"
        f"&type=channel&part=snippet&maxResults=5"
    )
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=15).read())
        results = []
        for item in data.get("items", []):
            results.append({
                "channel_id": item["id"]["channelId"],
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"][:100],
            })
        return results
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return []


def get_channel_videos(channel_id: str, max_results: int = 60) -> list:
    """Fetch video list from a YouTube channel via Data API v3."""
    if not YOUTUBE_API_KEY:
        print("ERROR: YOUTUBE_API_KEY not set", file=sys.stderr)
        return []

    videos = []

    for duration in ["medium", "long"]:  # medium=4-20min, long=20min+
        next_page = ""
        while len(videos) < max_results:
            url = (
                f"https://www.googleapis.com/youtube/v3/search"
                f"?key={YOUTUBE_API_KEY}"
                f"&channelId={channel_id}"
                f"&part=snippet"
                f"&type=video"
                f"&videoDuration={duration}"
                f"&order=date"
                f"&maxResults=50"
            )
            if next_page:
                url += f"&pageToken={next_page}"

            try:
                data = json.loads(urllib.request.urlopen(url, timeout=15).read())
            except Exception as e:
                print(f"  API error: {e}", file=sys.stderr)
                break

            seen = {v["video_id"] for v in videos}
            for item in data.get("items", []):
                vid_id = item["id"].get("videoId")
                if vid_id and vid_id not in seen:
                    videos.append({
                        "video_id": vid_id,
                        "title": item["snippet"]["title"],
                        "published_at": item["snippet"]["publishedAt"],
                    })
                    seen.add(vid_id)

            next_page = data.get("nextPageToken", "")
            if not next_page:
                break

    return videos[:max_results]


def batch_download(videos: list, output_dir: Path) -> tuple:
    """Download a list of videos. Returns (success, skip, fail, failed_ids)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    success = skip = fail = 0
    failed_ids = []

    for i, v in enumerate(videos):
        vid = v["video_id"] if isinstance(v, dict) else v
        status = download_one(vid, output_dir)

        if status == "skip":
            skip += 1
        elif status == "ok":
            success += 1
            sz = (output_dir / f"{vid}.m4a").stat().st_size // 1024
            print(f"[{i+1}/{len(videos)}] ✅ {vid} ({sz}KB)")
        else:
            fail += 1
            failed_ids.append(vid)
            title = v.get("title", "")[:50] if isinstance(v, dict) else ""
            print(f"[{i+1}/{len(videos)}] ❌ {vid} {title}")

        if (success + skip + fail) % 10 == 0:
            done = success + skip + fail
            print(f"📥 进度: {done}/{len(videos)}（新 {success} / 缓存 {skip} / 失败 {fail}）")

    return success, skip, fail, failed_ids


def show_status(directory: Path):
    """Show download status for a directory."""
    if not directory.exists():
        print(f"Directory not found: {directory}")
        return

    m4a_files = list(directory.glob("*.m4a"))
    total_size = sum(f.stat().st_size for f in m4a_files)
    print(f"📁 {directory}")
    print(f"   Files: {len(m4a_files)}")
    print(f"   Size:  {total_size / 1024 / 1024:.0f} MB")

    # Check for residual files
    parts = list(directory.glob("*.part"))
    raws = list(directory.glob("*_raw.*"))
    if parts or raws:
        print(f"   ⚠️  Residual files: {len(parts)} .part, {len(raws)} raw")


# ── CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="YouTube Audio Downloader")
    sub = parser.add_subparsers(dest="command")

    # download
    p_dl = sub.add_parser("download", help="Download a single video")
    p_dl.add_argument("video_id")
    p_dl.add_argument("--output-dir", "-o", default=".", type=Path)

    # channel
    p_ch = sub.add_parser("channel", help="Download from a channel")
    p_ch.add_argument("channel_id", help="YouTube channel ID")
    p_ch.add_argument("--max", "-n", type=int, default=60)
    p_ch.add_argument("--output-dir", "-o", default=None, type=Path)
    p_ch.add_argument("--save-list", action="store_true", help="Save video list JSON")

    # search
    p_se = sub.add_parser("search", help="Search channel by name")
    p_se.add_argument("query")

    # batch
    p_ba = sub.add_parser("batch", help="Download from a JSON video list")
    p_ba.add_argument("json_file", type=Path)
    p_ba.add_argument("--output-dir", "-o", default=".", type=Path)

    # status
    p_st = sub.add_parser("status", help="Check download status")
    p_st.add_argument("directory", type=Path)

    args = parser.parse_args()

    if args.command == "download":
        args.output_dir.mkdir(parents=True, exist_ok=True)
        status = download_one(args.video_id, args.output_dir)
        if status == "ok":
            sz = (args.output_dir / f"{args.video_id}.m4a").stat().st_size // 1024
            print(f"✅ {args.video_id} ({sz}KB)")
        elif status == "skip":
            print(f"⏭️  {args.video_id} already exists")
        else:
            print(f"❌ {args.video_id} failed")
            sys.exit(1)

    elif args.command == "search":
        results = search_channel(args.query)
        if not results:
            print("No channels found.")
            return
        for r in results:
            print(f"  {r['channel_id']}  {r['title']}")
            if r["description"]:
                print(f"    {r['description']}")

    elif args.command == "channel":
        print(f"📺 Fetching videos for {args.channel_id}...")
        videos = get_channel_videos(args.channel_id, args.max)
        if not videos:
            print("No videos found. Check channel ID.")
            sys.exit(1)
        print(f"   Found {len(videos)} videos")

        output_dir = args.output_dir or Path(f"./{args.channel_id}_audio")
        output_dir.mkdir(parents=True, exist_ok=True)

        if args.save_list:
            list_file = output_dir / "video_list.json"
            with open(list_file, "w") as f:
                json.dump({"channel_id": args.channel_id, "videos": videos}, f, indent=2)
            print(f"   Saved list to {list_file}")

        success, skip, fail, failed_ids = batch_download(videos, output_dir)
        total_size = sum(f.stat().st_size for f in output_dir.glob("*.m4a")) // (1024 * 1024)
        print(f"\n📊 新 {success} / 缓存 {skip} / 失败 {fail} / 总大小 ~{total_size}MB")

        if failed_ids:
            fail_file = output_dir / "failed.json"
            with open(fail_file, "w") as f:
                json.dump(failed_ids, f, indent=2)
            print(f"❌ Failed IDs saved to {fail_file}")

    elif args.command == "batch":
        with open(args.json_file) as f:
            data = json.load(f)
        videos = data.get("videos", data) if isinstance(data, dict) else data
        print(f"📋 {len(videos)} videos from {args.json_file}")

        args.output_dir.mkdir(parents=True, exist_ok=True)
        success, skip, fail, failed_ids = batch_download(videos, args.output_dir)
        total_size = sum(f.stat().st_size for f in args.output_dir.glob("*.m4a")) // (1024 * 1024)
        print(f"\n📊 新 {success} / 缓存 {skip} / 失败 {fail} / 总大小 ~{total_size}MB")

    elif args.command == "status":
        show_status(args.directory)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
