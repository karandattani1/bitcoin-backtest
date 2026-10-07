# Pulling strategy data from YouTube: how it works

*Plan for turning trading YouTube channels into backtestable strategy rules. Written 7 Oct 2026.*

## The short version

A strategy video carries information in four places. Each one needs a different tool:

| Where the information is | What it typically holds | Tool |
|---|---|---|
| **Title, description, tags, chapters** | Strategy name, links (often an **AlgoTest/Tradetron shared-strategy link with every parameter**), timestamps | YouTube Data API v3 (official) or `yt-dlp --dump-json` |
| **Captions / speech** | The rules as spoken: entry time, strikes, SL, target, re-entry, claimed results | `youtube-transcript-api` for existing captions; **Whisper** speech-to-text when there are none |
| **On-screen visuals** | Backtest screenshots, indicator settings, the AlgoTest/Tradetron config screen, P&L tables | Download the video at low resolution, extract keyframes with `ffmpeg`, then OCR or a vision model |
| **Comments** | Viewers' live results, corrections, "this stopped working after X" | YouTube Data API `commentThreads` |

Then an LLM pass (e.g. Claude) turns the text into a **fixed strategy schema**. Duplicates get merged,
and each strategy becomes a rule card in the format of [strategy-rulebook.md](strategy-rulebook.md),
ready to backtest.

## Pipeline

```
channel list
   │
   ▼
1. Discover   – list every video on each channel (ID, title, date, duration, views, description)
   │
   ▼
2. Filter     – keep videos about strategies (keyword and title rules, plus a cheap LLM yes/no)
   │
   ▼
3. Transcript – captions in Hindi/English (manual > auto-generated) → Whisper if none
   │
   ▼
4. Visuals    – only for videos that pass step 5's "missing parameters" check: keyframes → OCR/vision
   │
   ▼
5. Extract    – LLM fills a strategy JSON, citing the timestamp of each rule
   │
   ▼
6. Dedupe     – cluster near-identical strategies (e.g. 40 versions of the 9:20 straddle)
   │
   ▼
7. Rule cards – write to rulebook / YAML → backtester
```

Everything is stored per video in a folder (`data/youtube/<channel>/<video_id>/`) containing
`meta.json`, `transcript.json`, `frames/` and `strategy.json`. That way a re-run only processes new videos.

## Step by step

### 1. Discover videos
- **Option A: official YouTube Data API v3** (recommended for metadata).
  - Create a free API key in Google Cloud Console.
  - Look up the channel's "uploads" playlist ID with `channels.list?part=contentDetails`.
  - Page through `playlistItems.list`, 50 per call, then `videos.list` for duration, views and the full description.
  - The default quota is 10,000 units/day. A list call costs 1 unit, so even a 2,000-video channel takes about 80 units.
- **Option B: `yt-dlp`** (no key needed):
  `yt-dlp --flat-playlist --dump-json "https://www.youtube.com/@CHANNEL/videos"` lists every video.
  Add `--skip-download --dump-json <url>` on a single video to get its full metadata, including chapters.

### 2. Filter for strategy videos
- Keep titles and descriptions that match: straddle, strangle, iron fly, condor, ORB, breakout, backtest,
  algo, AlgoTest, Tradetron, setup, strategy, "9:20", expiry, SL, rules, Supertrend, VWAP, momentum, RSI, plus Hindi equivalents.
- Drop shorts under 60 seconds, livestreams over 2 hours (process those last), and market-update or news videos.
- **Extract links from descriptions straight away.** AlgoTest and Tradetron share links often contain the complete
  strategy configuration, which is far more reliable than the spoken version.

### 3. Get transcripts
- `youtube-transcript-api` (Python) fetches captions without downloading the video.
  - Ask for `["en", "hi"]` and prefer manually created captions over auto-generated ones.
  - Auto-generated Hindi captions are noisy with numbers ("नौ बीस" for 9:20, "तीस परसेंट" for 30%), so the LLM step has to normalise them.
- When a video has no captions, download only the audio (`yt-dlp -x --audio-format m4a`) and transcribe it with Whisper.
  - Use `large-v3` (or `faster-whisper` on a GPU). It handles Hindi and Hinglish well.
  - Use `--task transcribe`, not translate, so numbers come out as spoken. Translate in the LLM step instead.
- Keep the **timestamps**. Each extracted rule should point back to a moment in the video so you can check it.

### 4. Capture what's on screen (only when it's needed)
- Many creators *show* the parameters (an AlgoTest legs screen, indicator settings, a P&L table) instead of saying them.
- Download a low resolution only: `yt-dlp -f "bv*[height<=480]"`.
- Extract frames when the scene changes: `ffmpeg -i v.mp4 -vf "select='gt(scene,0.3)'" -vsync vfr frames/%04d.jpg`.
- Keep frames around the timestamps where the transcript mentions "settings", "parameters", "backtest", "result" and similar words.
- Send those frames to a vision-capable model (or Tesseract OCR) to read the numbers.
- Doing this only for videos where step 5 found missing fields keeps it cheap.

### 5. Extract to a fixed schema
Ask the LLM to fill this structure and to write `null` rather than guess:

```json
{
  "video_id": "...", "channel": "...", "published": "2025-11-04",
  "strategy_name": "...",
  "category": "vol_selling | credit_spread | option_buying | futures | equity_swing | equity_positional",
  "instrument": "NIFTY weekly options", "timeframe": "5m",
  "entry": {"time": "09:20", "conditions": ["..."], "legs": [{"side": "sell", "type": "CE", "strike": "ATM", "qty_lots": 1}]},
  "stop_loss": {"type": "per_leg_pct", "value": 30},
  "target": {"type": "combined_pct", "value": 50},
  "re_entry": {"allowed": true, "max": 2, "rule": "..."},
  "exit": {"time": "15:15", "conditions": []},
  "filters": ["VIX < 20", "no event days"],
  "claimed_results": {"period": "2022-2024", "win_rate": 0.68, "cagr": null, "max_dd": null, "costs_included": false},
  "evidence": [{"field": "stop_loss", "timestamp": "07:42", "quote": "..."}],
  "external_links": ["https://algotest.in/..."],
  "completeness": 0.8,
  "pre_sep_2025_only": true
}
```

- `completeness` is the share of the fields a backtest needs that were found.
- `pre_sep_2025_only` flags videos built around expiries that no longer exist (BankNifty weekly, Thursday NIFTY).
- A cheaper model is enough for the step-2 yes/no filter. Use a stronger model for this extraction step.
- Run the extraction twice on a sample and compare the outputs to catch errors.

### 6. Merge duplicates
- Group strategies by `(category, instrument, entry time, leg structure)`.
- Within a group, keep the different SL/target/filter values as **parameter variants to test**, instead of treating them as separate strategies.
- This often turns hundreds of videos into a few dozen distinct strategies.

### 7. Turn into rule cards
- Map each merged strategy onto the rulebook format (entry, stops, exit, filters).
- Add a source list of video links with timestamps, so every rule can be traced back.
- Mark each card **[YouTube]** and note how many channels describe the same strategy.

## Practical constraints

- **Where to run it:** this cloud sandbox blocks youtube.com (the API at googleapis.com is reachable).
  YouTube also often blocks transcript and download requests from cloud and datacenter IPs.
  **Run steps 1–4 on your own laptop or a home connection.** Then commit the `meta.json` and `transcript.json` files
  (not the videos) and run steps 5–7 here.
- **Terms of service:** YouTube's ToS restricts downloading video content. Fetching metadata through the official API is fine.
  Fetching captions and extracting rules for your own private research is common practice but sits in a grey area.
  - Don't republish transcripts or video.
  - Delete downloaded audio and video after processing.
  - Keep request rates low (a few seconds between videos).
- **Quality:** a lot of YouTube strategy content is overfitted or shows hand-picked results.
  The `claimed_results` field is recorded **only** so it can be compared with your own backtest.
  It is never treated as evidence.
- **Language:** expect Hindi and Hinglish. Whisper `large-v3` handles it, and the extraction prompt should normalise spoken numbers and times.

## Tools to install (on your machine)

```
pip install yt-dlp youtube-transcript-api google-api-python-client faster-whisper anthropic
# plus: ffmpeg (brew/apt), optional tesseract-ocr
```

## What I need from you to build it

1. **The channel list** (URLs or @handles).
2. **A YouTube Data API key**, or confirmation that `yt-dlp` is fine for discovery.
3. **Whether you'll run the fetch steps locally.** I'll write `scripts/yt_fetch.py`, which you run at home, and
   `scripts/yt_extract.py`, which runs here on the committed transcripts.
