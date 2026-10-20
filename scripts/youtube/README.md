# YouTube strategy extraction

There are three steps. Step 1 has to run on your own computer, because YouTube blocks cloud servers.

```
pip install -r scripts/youtube/requirements.txt        # Python 3.10+

# 1. On your machine: list videos, keep strategy-like titles, save metadata and captions
python scripts/youtube/yt_fetch.py --limit 20          # trial run: 20 videos per channel
python scripts/youtube/yt_fetch.py                     # full run (re-runs skip videos already done)
#    optional: --whisper to transcribe caption-less videos (pip install faster-whisper, needs ffmpeg)
#    optional: --all to skip the title filter, --tabs videos,streams to include livestreams
git add data/youtube && git commit -m "YouTube transcripts" && git push

# 2. Claude reads each transcript and writes strategy.json (needs ANTHROPIC_API_KEY or `ant auth login`)
python scripts/youtube/yt_extract.py --dry-run         # what will be processed, and prompt sizes
python scripts/youtube/yt_extract.py --limit 5         # check quality on a few videos first

# 3. Merge into one catalog
python scripts/youtube/yt_catalog.py                   # data/youtube/catalog.csv + research/youtube-strategy-catalog.md
```

**Channels** are listed in `channels.txt`. If a channel lists 0 videos, check its handle in a browser.

**Output** for each video goes in `data/youtube/<channel>/<video_id>/`:
- `meta.json`: title, date, description, chapters, links
- `transcript.json`: caption segments with timestamps
- `strategy.json`: Claude's extraction

**Model and settings.** Extraction uses `claude-opus-5-5` at effort `high`. If the model declines a video, the request is retried automatically on a fallback model (`fallbacks: "default"`).
Change the effort with `--effort`. Use `--dry-run` to see token counts before spending anything.

**Terms of use.** Only captions and metadata are saved. The `--whisper` option downloads audio to a temp folder and deletes it afterwards.
Don't republish the transcripts. Keep `--sleep` at 3 seconds or more.
