"""Fetch video metadata and transcripts from YouTube channels.

Run this on your own machine: YouTube blocks most cloud/datacenter IPs.

    pip install -r scripts/youtube/requirements.txt
    python scripts/youtube/yt_fetch.py                    # all channels in channels.txt
    python scripts/youtube/yt_fetch.py --limit 20         # quick trial run
    python scripts/youtube/yt_fetch.py --whisper          # transcribe videos that have no captions

Output, one folder per video (re-runs skip videos already fetched):
    data/youtube/<channel>/index.jsonl          every video on the channel + whether it passed the filter
    data/youtube/<channel>/<video_id>/meta.json
    data/youtube/<channel>/<video_id>/transcript.json
"""
import argparse
import json
import re
import sys
import tempfile
import time
from pathlib import Path

from yt_dlp import YoutubeDL
from youtube_transcript_api import (
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
)

ROOT = Path(__file__).resolve().parents[2]

# Title keywords that suggest a strategy / rules video. English, Hindi (Devanagari) and Hinglish.
STRATEGY_PATTERN = re.compile(
    r"strateg|setup|system|backtest|algo|rule|straddle|strangle|iron\s*(fly|condor)|condor|butterfly|"
    r"spread|hedg|option\s*(sell|buy|writ)|theta|delta|gamma|vega|\bIV\b|implied vol|volatility|VIX|"
    r"expiry|breakout|\bORB\b|opening range|VWAP|supertrend|moving average|\bEMA\b|\bSMA\b|\bRSI\b|MACD|"
    r"bollinger|renko|point\s*(and|&)\s*figure|momentum|mean revers|swing|positional|intraday|scalp|"
    r"stop\s*loss|\bSL\b|target|entry|exit|win rate|DTE|trade management|adjust|roll|"
    r"रणनीति|स्ट्रेटेजी|सेटअप|ऑप्शन|ट्रेडिंग|बैकटेस्ट",
    re.IGNORECASE,
)

URL_PATTERN = re.compile(r"https?://\S+")


def channel_slug(url: str) -> str:
    m = re.search(r"youtube\.com/(@[^/?#]+|channel/[^/?#]+|c/[^/?#]+|user/[^/?#]+)", url)
    return (m.group(1) if m else url).replace("channel/", "").replace("/", "_").lstrip("@")


def list_channel_videos(channel_url: str, tabs: list[str]) -> list[dict]:
    """Flat listing of a channel's uploads: fast, one request per page, no per-video calls."""
    videos, seen = [], set()
    opts = {"extract_flat": "in_playlist", "quiet": True, "skip_download": True, "ignoreerrors": True}
    with YoutubeDL(opts) as ydl:
        for tab in tabs:
            info = ydl.extract_info(f"{channel_url.rstrip('/')}/{tab}", download=False)
            for e in (info or {}).get("entries") or []:
                if not e or not e.get("id") or e["id"] in seen:
                    continue
                seen.add(e["id"])
                videos.append({
                    "id": e["id"],
                    "title": e.get("title") or "",
                    "duration": e.get("duration"),
                    "view_count": e.get("view_count"),
                    "tab": tab,
                })
    return videos


def fetch_metadata(video_id: str) -> dict:
    opts = {"quiet": True, "skip_download": True, "ignoreerrors": False}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    description = info.get("description") or ""
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": info.get("title"),
        "channel": info.get("channel"),
        "upload_date": info.get("upload_date"),
        "duration": info.get("duration"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "language": info.get("language"),
        "tags": info.get("tags") or [],
        "chapters": [
            {"start": c.get("start_time"), "title": c.get("title")} for c in info.get("chapters") or []
        ],
        "description": description,
        "links": sorted(set(URL_PATTERN.findall(description))),
    }


def fetch_captions(api: YouTubeTranscriptApi, video_id: str, languages: list[str]) -> dict | None:
    """Prefer human-made captions, then auto-generated, in the order of `languages`."""
    transcripts = api.list(video_id)
    for finder in (transcripts.find_manually_created_transcript, transcripts.find_generated_transcript):
        try:
            t = finder(languages)
        except NoTranscriptFound:
            continue
        fetched = t.fetch()
        return {
            "source": "youtube_captions",
            "language": t.language_code,
            "is_generated": t.is_generated,
            "segments": [
                {"start": round(s["start"], 1), "text": s["text"]} for s in fetched.to_raw_data()
            ],
        }
    return None


def whisper_transcribe(video_id: str, model_size: str) -> dict:
    """Download audio only, transcribe locally, delete the audio."""
    from faster_whisper import WhisperModel  # optional dependency

    with tempfile.TemporaryDirectory() as tmp:
        opts = {
            "quiet": True,
            "format": "bestaudio/best",
            "outtmpl": f"{tmp}/%(id)s.%(ext)s",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}],
        }
        with YoutubeDL(opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
        audio = next(Path(tmp).glob(f"{video_id}.*"))
        model = WhisperModel(model_size, compute_type="auto")
        # task="transcribe" keeps numbers as spoken; translation happens in the extraction step.
        segments, info = model.transcribe(str(audio), task="transcribe", vad_filter=True)
        return {
            "source": f"whisper_{model_size}",
            "language": info.language,
            "is_generated": True,
            "segments": [{"start": round(s.start, 1), "text": s.text.strip()} for s in segments],
        }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--channels", default=str(Path(__file__).with_name("channels.txt")))
    p.add_argument("--out", default=str(ROOT / "data" / "youtube"))
    p.add_argument("--limit", type=int, default=0, help="max videos per channel after filtering (0 = all)")
    p.add_argument("--all", action="store_true", help="skip the title keyword filter")
    p.add_argument("--tabs", default="videos", help="comma list of channel tabs: videos,streams,shorts")
    p.add_argument("--min-duration", type=int, default=120, help="skip videos shorter than this (seconds)")
    p.add_argument("--languages", default="en,hi,en-IN", help="caption language preference order")
    p.add_argument("--sleep", type=float, default=3.0, help="pause between videos (seconds)")
    p.add_argument("--whisper", action="store_true", help="transcribe videos without captions locally")
    p.add_argument("--whisper-model", default="large-v3")
    args = p.parse_args()

    channels = [
        line.strip() for line in Path(args.channels).read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    languages = [x.strip() for x in args.languages.split(",") if x.strip()]
    tabs = [x.strip() for x in args.tabs.split(",") if x.strip()]
    api = YouTubeTranscriptApi()

    for channel_url in channels:
        slug = channel_slug(channel_url)
        cdir = Path(args.out) / slug
        cdir.mkdir(parents=True, exist_ok=True)
        print(f"\n== {slug}: listing videos", flush=True)
        videos = list_channel_videos(channel_url, tabs)
        for v in videos:
            long_enough = v["duration"] is None or v["duration"] >= args.min_duration
            v["selected"] = long_enough and (args.all or bool(STRATEGY_PATTERN.search(v["title"])))
        with open(cdir / "index.jsonl", "w") as f:
            for v in videos:
                f.write(json.dumps(v, ensure_ascii=False) + "\n")
        selected = [v for v in videos if v["selected"]]
        if args.limit:
            selected = selected[: args.limit]
        print(f"   {len(videos)} videos, {len(selected)} selected", flush=True)

        stats = {"captions": 0, "whisper": 0, "none": 0, "skipped": 0, "errors": 0}
        for i, v in enumerate(selected, 1):
            vdir = cdir / v["id"]
            if (vdir / "transcript.json").exists():
                stats["skipped"] += 1
                continue
            vdir.mkdir(exist_ok=True)
            try:
                if not (vdir / "meta.json").exists():
                    meta = fetch_metadata(v["id"])
                    (vdir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
                try:
                    transcript = fetch_captions(api, v["id"], languages)
                except (TranscriptsDisabled, NoTranscriptFound):
                    transcript = None
                if transcript:
                    stats["captions"] += 1
                elif args.whisper:
                    transcript = whisper_transcribe(v["id"], args.whisper_model)
                    stats["whisper"] += 1
                else:
                    stats["none"] += 1
                    (vdir / "NO_CAPTIONS").touch()
                if transcript:
                    (vdir / "transcript.json").write_text(json.dumps(transcript, ensure_ascii=False))
                    (vdir / "NO_CAPTIONS").unlink(missing_ok=True)
                print(f"   [{i}/{len(selected)}] {v['id']} {v['title'][:70]!r} "
                      f"{'ok' if transcript else 'no captions'}", flush=True)
            except (IpBlocked, RequestBlocked) as e:
                print(f"\nYouTube is blocking this IP ({type(e).__name__}). Wait a while, raise --sleep, "
                      "or run from a different network. Progress so far is saved.", file=sys.stderr)
                return 2
            except VideoUnavailable:
                stats["errors"] += 1
            except Exception as e:  # keep going; one bad video shouldn't stop a channel
                stats["errors"] += 1
                print(f"   [{i}/{len(selected)}] {v['id']} error: {type(e).__name__}: {e}", flush=True)
            time.sleep(args.sleep)
        print(f"   done: {stats}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
