# Architecture

vidscribe turns a video, audio file or URL into a timestamped transcript and keeps the video file so an agent can pull frames with ffmpeg. Python >= 3.10; the core uses the standard library only. Engine dependencies are imported lazily inside each engine module.

## Data flow

`vidscribe/cli.py` owns argument parsing, the run flow and every stdout/stderr line except engine warnings. `main(argv) -> int`; `vidscribe/__main__.py` calls it.

1. UTF-8 stdio; on macOS the PATH is extended with `~/.local/bin` and `/opt/homebrew/bin`.
2. `media.require_tools()` (ffmpeg, ffprobe) and `media.prune()` (output folders older than 3 days).
3. A missing local file fails with `no such file: <src>` before an engine is chosen.
4. `engines.select()` picks the engine; `engine: <name>` is printed (for scribe, `engine: scribe (audio is uploaded to ElevenLabs)`).
5. URL: `media.download()` (yt-dlp run as `python -m yt_dlp`); local path: used in place. Probe with `has_audio` / `has_video` / `duration`.
6. `engine.transcribe(src, tmp, out_base, fmt, opts)`. The engine extracts its own audio. No audio track: an empty transcript for video, an error for audio-only input.
7. With a kept video the transcript is also written as txt (`subs.srt_to_txt`); `media.keep_video()` moves a downloaded file to `ROOT/videos`, a local file keeps its absolute path.
8. Ends-early check (`WARNING: last cue ...`), then `video: <path>`, `transcript: <path>`, and the txt body on stdout.

## Modules

- `media.py`: ffmpeg/ffprobe/yt-dlp and output folders. `ROOT` is `/tmp/vidscribe` on POSIX and `<tempdir>/vidscribe` on Windows; `default_outdir()` honours `VIDSCRIBE_OUTDIR`. `extract_audio` makes 16 kHz mono wav or 64 kbit/s mono mp3 by the destination suffix.
- `subs.py`: `Cue(start, end, text)`, `write()` for txt/srt/vtt, `read_srt`, `srt_to_txt`, `fmt_ts`.
- `engines/__init__.py`: `NAMES = ("mlx", "scribe", "whisper")`, `Options(lang, context, model, speakers)`, `select(name)`, `get(name)`. Every engine module exposes `available()` and `transcribe(...)`; a fatal error prints a message and exits 1.
- `engines/mlx.py` + `mlx_patch.py`: Apple Silicon. Builds the original mlx-audio command and runs it with the interpreter named in the shebang of `mlx_audio.stt.generate`; its stdout goes to stderr. `command(...)` is the test seam.
- `engines/scribe.py`: ElevenLabs Scribe over HTTPS (`scribe_v3`). `request(...)` is the test seam; format `json` writes the raw response.
- `engines/whisper.py`: faster-whisper (`large-v3-turbo`). CUDA float16 first, CPU int8 fallback inside `transcribe`; on Windows the `site-packages/nvidia/*/bin` DLL folders are put on PATH first.

## Engine choice

An explicit `-e` or `VIDSCRIBE_ENGINE` is taken as is, without an availability check. Otherwise: mlx if usable (Apple Silicon with mlx-audio), else scribe if `ELEVENLABS_API_KEY` is set, else whisper if installed, else exit 1 with an OS-specific hint. An ImportError counts as unavailable. The cloud engine is never chosen without the key.

## Conventions

- User-facing strings keep the original script's exact wording (`video:`, `transcript:`, the no-audio messages, the removed-flag message for `-v`, `--at`, `--scan`).
- Subprocess calls pass argument lists, never a shell; text is read and written as UTF-8.
- `ELEVENLABS_API_KEY` is never printed, logged or written. Scribe sends through an opener that follows no redirects, and rejects keys outside printable ASCII before sending anything.
- Tests never touch the network and skip, not fail, when ffmpeg is missing.
- Code comments and docs are in English.

## Install

`pyproject.toml` defines the package, the `vidscribe` script, the extras `local` (faster-whisper) and `cuda` (NVIDIA runtime wheels, not on macOS). `install.sh` (macOS) and `install.ps1` (Windows) install system tools, run `uv tool install --force --python 3.12 <repo>[extras]` and replace `~/.claude/skills/vidscribe` with `skill/`. `bin/vidscribe` is a dev shim that runs the checkout.

See `docs/decisions/` for why, and `CONTEXT.md` for the vocabulary.
