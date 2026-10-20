# YouTube strategy extraction (runs fully on your PC)

There are three steps. No cloud API is used, so there's no per-token cost.

```
pip install -r scripts/youtube/requirements.txt        # Python 3.10+

# 1. Fetch: list videos, keep strategy-like titles, save metadata and captions
python scripts/youtube/yt_fetch.py --limit 20          # trial: 20 videos per channel
python scripts/youtube/yt_fetch.py                     # full run (re-runs skip videos already done)
#    --whisper  transcribe caption-less videos (pip install faster-whisper; needs ffmpeg)

# 2. Screen + extract with a local Gemma model
ollama pull gemma3:27b                                 # or whichever Gemma you already have
python scripts/youtube/yt_extract.py --dry-run         # videos and chunk counts
python scripts/youtube/yt_extract.py --limit 5         # check quality first
python scripts/youtube/yt_extract.py                   # everything

# 3. Merge into one catalog
python scripts/youtube/yt_catalog.py                   # data/youtube/catalog.csv + research/youtube-strategy-catalog.md

git add data/youtube research && git commit -m "YouTube strategies" && git push
```

## Model server options

| Server | Command |
|---|---|
| Ollama (default) | `--model gemma3:27b` (use `ollama list` to see your exact tag) |
| LM Studio | `--backend openai --url http://localhost:1234 --model <model id shown in LM Studio>` |
| llama.cpp `llama-server` | `--backend openai --url http://localhost:8080 --model gemma` |

Both backends force the output into the strategy JSON schema, so the model can't return free text.

## Settings that matter

- **Model size.** Use 27B if your GPU can hold it (about 16–24 GB of memory when quantised). 12B works but misses more details. 4B or smaller isn't reliable enough for extraction.
- **`--num-ctx 16384`** (Ollama). Ollama's default context is small, and anything over the limit is dropped silently. The script requests this size and **fails loudly if the prompt filled the context**. Raise it if you have spare GPU memory.
- **`--chunk-chars 20000`**. Long webinars are split into chunks of about 5–7k tokens, with a little overlap between chunks. Smaller chunks give a small model more focus, but a strategy explained across a boundary can come out in pieces.
  The catalog step groups those pieces back together, and each strategy records which chunk it came from (`_chunk`).
- **Two stages.** `screen` reads the title, description and opening of the transcript, and decides whether it's a strategy video. Only videos that pass go to `extract`.
  - `--screen-only` runs stage 1 across the whole library first.
  - `--no-screen` extracts everything.

## Output for each video (`data/youtube/<channel>/<video_id>/`)

- `meta.json`: title, date, description, chapters, links
- `transcript.json`: caption segments with timestamps
- `screen.json`: strategy video or not, confidence, reason
- `strategy.json`: extracted strategies with timestamps for the evidence

## Terms of use

Only captions and metadata are saved. `--whisper` downloads audio to a temp folder and deletes it afterwards.
Don't republish the transcripts. Keep `--sleep` at 3 seconds or more.
