# vidscribe

Lets AI agents watch videos, on macOS and Windows. Give it a file or any URL yt-dlp handles. It returns a transcript and, for video, the path of the video file, so the agent can look at the picture with `ffmpeg`. Videos without an audio track get an empty transcript and the path. Three engines: on-device [MLX](https://github.com/ml-explore/mlx) on Apple Silicon (the Mac default: no API keys, no cloud), on-device faster-whisper on Windows, and ElevenLabs Scribe in the cloud.

## Does it help?

The transcript does. On 12 long talks, an agent with only `ffmpeg` scored 54% on the 12 questions about what was said. With vidscribe's transcript it scored 100%.

vidscribe used to have its own picture commands: overview sheets, `--at` and `--scan`. They did not beat an agent that runs `ffmpeg` on the video file. On the public [Video-Index v1.1](https://github.com/Espere-1119-Song/Video-Index) benchmark, they scored 38.2% and plain `ffmpeg` scored 37.7%, and they cost 23% more per question. So they were removed in November 2026 ([ADR-0009](docs/decisions/0009-drop-picture-commands.md)). The `v1` tag keeps them.

Tables, method, and limits: [docs/benchmark.md](docs/benchmark.md). Every run used Codex with `gpt-6.2-sol`. The transcripts in that benchmark came from the MLX engine; Scribe and whisper were not measured.

## Install

**macOS (Apple Silicon)** needs [Homebrew](https://brew.sh). The default model (~2.5 GB) downloads on first run.

```sh
git clone https://github.com/SamuelZ12/vidscribe.git
cd vidscribe && ./install.sh
```

**Windows** (PowerShell 5.1 or 7) installs ffmpeg and uv with winget if they are missing:

```powershell
git clone https://github.com/SamuelZ12/vidscribe.git
cd vidscribe
.\install.ps1          # cloud engine (ElevenLabs Scribe)
.\install.ps1 -Local   # also the local whisper engine (NVIDIA GPU or CPU)
```

Both also install the agent skill into `~/.claude/skills/vidscribe`. Open a new terminal, then check with `vidscribe -h`. Update with `git pull` and run the installer again. Manual install and uninstall: [docs/usage.md](docs/usage.md#install).

## Engines

| Engine | Runs on | Default when | Cost | Audio leaves the device |
|---|---|---|---|---|
| `mlx` | Apple Silicon Mac | on an Apple Silicon Mac | free | no |
| `scribe` | any OS | `ELEVENLABS_API_KEY` is set and mlx is not available | paid (ElevenLabs) | yes |
| `whisper` | any OS, NVIDIA GPU or CPU | faster-whisper is installed (`-Local`) and no key is set | free | no |

Choose with `-e` or `VIDSCRIBE_ENGINE`. Scribe also labels speakers (`[speaker_N]`) and sounds (`(laughter)`). You set `ELEVENLABS_API_KEY` yourself (Windows: `setx ELEVENLABS_API_KEY "<your key>"`, macOS: an `export` line in `~/.zshrc`); the installers never ask for it.

## Usage

```sh
vidscribe talk.mp4                                     # transcript; the video path goes to stderr
vidscribe "https://www.youtube.com/watch?v=<id>"       # downloads the video too
vidscribe "https://www.youtube.com/watch?v=<id>" -a    # transcript only
vidscribe memo.m4a -f srt -o ~/transcripts             # srt, kept outside the temp folder
vidscribe talk.mp4 -e scribe -n 2                      # cloud engine, at most 2 speakers
```

On YouTube's first video:

```console
$ vidscribe "https://www.youtube.com/watch?v=jNQXAC9IVRw"
video: /tmp/vidscribe/videos/jNQXAC9IVRw.mp4
transcript: /tmp/vidscribe/transcripts/jNQXAC9IVRw.txt
All right, so here we are, one of the elephants. Cool thing about these guys is that they have really, really, really long trunks, and that's that's cool. And that's pretty much all there is to say.
```

txt transcripts print to stdout; the transcript and video paths go to stderr. On an M5 Pro Mac mini with the MLX engine, a 64-minute lecture took 50 s, download included; that figure is MLX only. Outputs stay in `/tmp/vidscribe/` (Windows: `%TEMP%\vidscribe`) for 3 days. The default MLX model is Qwen3-ASR (~30 languages); for others, use `-m mlx-community/whisper-large-v3-turbo-asr-fp16`. Full reference: [docs/usage.md](docs/usage.md).

## Agent skill

```sh
npx skills add SamuelZ12/vidscribe
```

The installers already put it in `~/.claude/skills/vidscribe`. Otherwise, with Node.js 22.20+, run the command above; without Node, copy `skill/` into your agent's skills folder.

## Limits

- Speech only (Scribe also tags sounds such as laughter): music isn't described.
- Scribe uploads the audio to ElevenLabs and costs money; mlx and whisper stay on the device.
- No OCR or word timestamps; agents read on-screen text from frames they take with `ffmpeg`.

Design decisions: [docs/decisions/](docs/decisions/).

## License

MIT. The models, ffmpeg and yt-dlp come under their own licenses: [docs/usage.md](docs/usage.md#licenses).
