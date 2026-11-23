# Usage

```
vidscribe <file-or-URL> [-o DIR] [-l LANG] [-f txt|srt|vtt|json] [-c "terms"] [-m MODEL] [-e mlx|scribe|whisper] [-n N] [-a]
vidscribe -h | --help
```

- Transcripts go to `<temp>/vidscribe/transcripts/<name>.<fmt>`, where `<temp>` is `/tmp` on macOS and `%TEMP%` on Windows; txt is also printed to stdout. Use `-o DIR` to keep them elsewhere. Every run prints `engine: <name>` to stderr first.
- A video input (a video stream, checked with ffprobe; URLs are downloaded as video, up to 720p) writes srt + txt and prints `video: <path>` to stderr, so an agent can look at the picture with `ffmpeg`. Downloaded videos are saved as `<temp>/vidscribe/videos/<id>.<ext>`; a local file is used where it is. Audio files, including mp3/m4a with cover art, give a transcript only.
- A video with no audio track gets empty srt and txt files and its video path. Transcript-only runs require audio.
- `-a`/`--audio-only`: transcript only; URLs ask yt-dlp for audio only. `-f vtt|json` also gives a transcript only.
- `-v`, `--at` and `--scan` were removed in November 2026 ([ADR-0009](decisions/0009-drop-picture-commands.md)). To keep using them, check out the `v1` tag.
- `-e` picks the engine (see [Engines](#engines)). `-n N` caps the number of speakers (scribe only). `-l en|ru|...` forces a language. `-c "Letta, Qwen"` biases rare names (hotwords for mlx and whisper, keyterms for scribe). `-m` picks another model for the engine.
- mlx detects the language separately in every ~30 s piece, so mixed-language media and music breaks need no flag; use `-l en` for Hindi or other speech mixed with English terms to keep those terms in Latin script.
- Long media is transcribed to the end. Applause or music can show up as a short run of one repeated word ("oh, oh, oh"). `warning: transcript cut off in 00:12:03-00:12:09` means the model got stuck there (almost always such a loop): that stretch keeps only its first words, and the rest of the file is unaffected. A `WARNING: last cue ... < duration` line means the transcript ends before the media does: either the model stopped early or there is no speech near the end. `warning: CUDA unavailable (...), using CPU` means the whisper engine fell back to the processor and will be slower.
- Old outputs in the vidscribe temp folder (transcripts, videos, and v1's frames folders) are pruned after 3 days, checked at the start of each run.

## Engines

| Engine | Runs on | Default when | Cost | Audio leaves the device |
|---|---|---|---|---|
| `mlx` | Apple Silicon Mac (M1 or later) | on an Apple Silicon Mac with mlx-audio installed | free | no |
| `scribe` | any OS | `ELEVENLABS_API_KEY` is set and mlx is not used | paid (ElevenLabs) | yes: mono mp3 audio, about 30 MB per hour |
| `whisper` | any OS, NVIDIA GPU or CPU | faster-whisper is installed and no key is set | free | no |

Order when `-e` and `VIDSCRIBE_ENGINE` are not set: mlx, then scribe, then whisper; if none is usable, vidscribe lists the options. Default models: mlx `mlx-community/Qwen3-ASR-1.7B-8bit`, scribe `scribe_v3`, whisper `large-v3-turbo`.

- **scribe** labels speakers `[speaker_N]` (when there is more than one) and sounds such as `(laughter)`. Errors are shown, never retried, because each request is paid. Run output says `engine: scribe (audio is uploaded to ElevenLabs)`.
- **whisper** uses an NVIDIA GPU (float16) when CUDA works, else the CPU (int8) with a warning. It filters silence with VAD.
- The benchmark figures in the README and `docs/benchmark.md` were measured on the MLX engine; Scribe and whisper have no measurements.

### The ElevenLabs key

Create an API key in your ElevenLabs account and set it yourself; the installers and vidscribe never ask for it and never print it.

- Windows: `setx ELEVENLABS_API_KEY "<your key>"`, then open a new terminal.
- macOS: add `export ELEVENLABS_API_KEY=<your key>` to `~/.zshrc`, then open a new terminal.

## Install

Run the installers from the folder of this repository, not from a clone of the upstream project: `cd <this repository>`, then `./install.sh` or `.\install.ps1`. This version is based on [SamuelZ12/vidscribe](https://github.com/SamuelZ12/vidscribe) (upstream, MIT).

**macOS (Apple Silicon).** Needs [Homebrew](https://brew.sh). `./install.sh` runs `brew install uv ffmpeg`, `uv tool install --force mlx-audio --prerelease=allow`, then `uv tool install --force --python 3.12 <repo>`, and copies `skill/` into `~/.claude/skills/vidscribe`. It removes an old `~/.local/bin/vidscribe` symlink that would shadow the new command.

**Windows (PowerShell 5.1 or 7).** `.\install.ps1` installs ffmpeg (`winget install Gyan.FFmpeg`) and uv (`winget install astral-sh.uv`) only if they are missing, runs `uv tool install --force --python 3.12 <repo>`, runs `uv tool update-shell`, and copies `skill/` into `~/.claude/skills/vidscribe`. `.\install.ps1 -Local` installs `<repo>[local,cuda]`: faster-whisper plus the CUDA 12 libraries (pip packages `nvidia-cublas-cu12` and `nvidia-cudnn-cu12`); an NVIDIA driver is still required for the GPU. If winget is missing, install ffmpeg and uv by hand.

Both installers are safe to run again, and they replace the contents of the skill folder with the files in `skill/`. Open a new terminal if `vidscribe` is not found right after installing.

**By hand.** Install ffmpeg (with `ffprobe`) and uv, then `uv tool install --force --python 3.12 .` (add `[local,cuda]` for whisper). From a checkout without installing: `python -m vidscribe <args>` in the repo root.

**Uninstall.** `uv tool uninstall vidscribe` (and `uv tool uninstall mlx-audio` on a Mac), then delete `~/.claude/skills/vidscribe`. Models stay in their caches (`~/.cache/huggingface`) until you delete them.

## Environment

- `ELEVENLABS_API_KEY`: key for the scribe engine (set by you; see above).
- `VIDSCRIBE_ENGINE`: default engine (same as `-e`).
- `VIDSCRIBE_MODEL`: default model for the mlx engine (same as `-m`).
- `VIDSCRIBE_OUTDIR`: transcript folder (same as `-o`).

## Licenses

`mlx-community/Qwen3-ASR-1.7B-8bit` (default) is converted from [`Qwen/Qwen3-ASR-1.7B`](https://huggingface.co/Qwen/Qwen3-ASR-1.7B), Apache 2.0. `mlx-community/whisper-large-v3-turbo-asr-fp16` is converted from OpenAI's [`whisper-large-v3-turbo`](https://huggingface.co/openai/whisper-large-v3-turbo), MIT (the original's; the MLX copy states none). `ffmpeg`, `yt-dlp` and `faster-whisper` come under their own licenses; ElevenLabs Scribe is a paid service under ElevenLabs' terms.
