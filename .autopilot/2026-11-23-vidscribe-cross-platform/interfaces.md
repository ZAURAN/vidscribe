# Interfaces

## Project rules
- The core package uses the Python standard library only (Python >= 3.10). Optional engines import their dependencies lazily, inside the engine module.
- User-facing strings keep the original's exact wording where the original had them (see `notes.md`): `video: <path>`, `transcript: <path>`, `vidscribe: no audio track; writing an empty transcript`, `vidscribe: no audio track to transcribe`, `vidscribe: no usable audio or video stream`, `no such file: <src>`, `WARNING: last cue %.0fs < duration %.0fs; transcript ends early`, `vidscribe: <flag> was removed (docs/decisions/0009-drop-picture-commands.md); run ffmpeg on the video path a normal run prints`.
- Never print, log or write the value of `ELEVENLABS_API_KEY`.
- All subprocess calls pass argument lists (no shell) and read/write text as UTF-8.
- Tests: `python -m unittest discover tests`; tests that need ffmpeg are skipped (not failed) when it is absent; no network in tests.
- Code comments and docs in English, matching the upstream repo.

## Границы, решённые в спецификации

### `vidscribe/cli.py` — owns argument parsing, the run flow, and every stdout/stderr line except engine warnings
- `main(argv: list[str] | None = None) -> int`; `vidscribe/__main__.py` does `sys.exit(main())`.
- Flags: `src`, `-o DIR`, `-l LANG`, `-f txt|srt|vtt|json`, `-c TEXT`, `-m MODEL`, `-e mlx|scribe|whisper`, `-n N`, `-a/--audio-only`, `-h/--help`; `-v`, `--at`, `--scan` → the removed message, exit 1.
- Flow: UTF-8 stdio → `media.require_tools()` → `media.prune()` → `engines.select()` and print `engine: <name>` → download or locate → probe → `engine.transcribe(...)` (or the empty-srt path) → srt→txt when keeping video → `media.keep_video` → ends-early check → `transcript: …` → txt to stdout.

### `vidscribe/media.py` — owns ffmpeg/ffprobe/yt-dlp and the output folders
- `ROOT: Path` — `/tmp/vidscribe` on POSIX; `Path(tempfile.gettempdir()) / "vidscribe"` on Windows.
- `default_outdir() -> Path` — `$VIDSCRIBE_OUTDIR` or `ROOT / "transcripts"`.
- `require_tools() -> None` — exits 1 with an OS-specific install hint when ffmpeg or ffprobe is missing.
- `prune(days: int = 3) -> None` — removes `ROOT/{transcripts,videos,frames}/*` older than `days`.
- `download(url: str, dest: Path, want_video: bool) -> Path` — yt-dlp via `[sys.executable, "-m", "yt_dlp", ...]`, the original's flags, first file only.
- `has_audio(p: Path) -> bool`, `has_video(p: Path) -> bool` — ffprobe `a:u` / `V:u`.
- `duration(p: Path) -> float` — seconds, `0.0` if unknown.
- `extract_audio(src: Path, dst: Path) -> Path` — by `dst` suffix: `.wav` → 16 kHz mono PCM; `.mp3` → mono 64 kbit/s.
- `keep_video(src: Path, tmp: Path) -> Path` — a file inside `tmp` (downloaded) is moved to `ROOT / "videos"`; a local file is returned as an absolute path.

### `vidscribe/subs.py` — owns transcript file formats
- `class Cue(NamedTuple): start: float; end: float; text: str`
- `write(cues: list[Cue], out_base: Path, fmt: str) -> Path` — txt (one cue per line), srt, vtt; returns the written path.
- `read_srt(path: Path) -> list[Cue]`; `srt_to_txt(srt: Path, txt: Path) -> None` (one cue per line, as the original).
- `fmt_ts(seconds: float, sep: str = ",") -> str` — `HH:MM:SS,mmm` (`.` for vtt).

### `vidscribe/engines/__init__.py` — owns engine choice
- `NAMES = ("mlx", "scribe", "whisper")`
- `@dataclass Options: lang: str | None; context: str | None; model: str | None; speakers: int | None`
- `select(name: str | None) -> str` — an explicit name (or `$VIDSCRIBE_ENGINE`), else the default order from the spec; exits 1 with an OS-specific hint when none is usable.
- `get(name: str) -> ModuleType` — each engine module exposes
  - `available() -> bool`
  - `transcribe(src: Path, tmp: Path, out_base: Path, fmt: str, opts: Options) -> None` — extracts its own audio from `src` into `tmp`, writes `out_base.<fmt>` (fmt in txt|srt|vtt|json), prints its own warnings to stderr, exits 1 with a message on a fatal error.

### `vidscribe/engines/mlx.py` + `vidscribe/engines/mlx_patch.py`
- `mlx_patch.py` is the original heredoc body, byte for byte. `mlx.py` builds the original command and runs it with the mlx-audio interpreter (shebang of `mlx_audio.stt.generate`), its stdout sent to stderr. `DEFAULT_MODEL = "mlx-community/Qwen3-ASR-1.7B-8bit"`.
- `command(interp: str, wav: Path, out_base: Path, fmt: str, dur: float, opts: Options, ram_bytes: int) -> list[str]` — the test seam.

### `vidscribe/engines/scribe.py`
- `API = "https://api.elevenlabs.io/v1/speech-to-text"`, `DEFAULT_MODEL = "scribe_v3"`.
- `request(audio: Path, key: str, opts: Options) -> dict` — the test seam patches `urllib.request.urlopen`.
- `to_cues(words: list[dict]) -> list[Cue]`; fmt `json` writes the raw response.

### `vidscribe/engines/whisper.py`
- `DEFAULT_MODEL = "large-v3-turbo"`; `load(model: str)` tries CUDA (float16), then CPU (int8) with `warning: CUDA unavailable (...), using CPU`; on Windows it adds the `site-packages/nvidia/*/bin` DLL folders first.

### Install and skill
- `pyproject.toml` — package `vidscribe`, dependency `yt-dlp`; extras `local = ["faster-whisper>=1.1"]`, `cuda = ["nvidia-cublas-cu12", "nvidia-cudnn-cu12>=9,<10"]` (marker `sys_platform != 'darwin'`).
- `install.sh` (macOS) / `install.ps1` (Windows): system tools → `uv tool install --force --python 3.12 <repo>[extras]` → copy `skill/` into `~/.claude/skills/vidscribe`, replacing its contents.
- `bin/vidscribe` — a dev shim that runs the package from the repo checkout.

### Test seams
`cli.main(argv)`; `mlx.command(...)`; `urllib.request.urlopen` (scribe); `engines.select` with patched `platform.system`/`platform.machine`, `shutil.which`, the environment.

## Stack and commands
- Python >= 3.10 (this machine: Python 3.13 as `python`; installs pin 3.12 through uv). On Windows `python3` may be the Store stub — use `python`.
- Check command: `python -m unittest discover -s tests -v` from the repo root. One file: `python -m unittest tests.test_cli -v`.
- Run from a checkout without installing: `python -m vidscribe <args>` from the repo root.
- Installed: `uv tool install --force --python 3.12 .` (add `[local,cuda]` for the whisper engine) → `vidscribe` on PATH.
- Do not touch: `docs/benchmark.md`, `docs/measurements.md`, `docs/decisions/0001…0009` (history), `LICENSE`, `.autopilot/`.
- ffmpeg 9 and uv are installed on this machine; yt-dlp is on PATH too, but the package uses its own dependency.
- The original script is at commit `0eb1386` (`git show 0eb1386:bin/vidscribe`).
- Bash tool gotcha on this machine: long multi-line heredocs in one Bash call can fail to parse — write files with the file-writing tool instead.

- `core.autocrlf=true` on this machine: working-tree files may have CRLF while git stores LF. Byte-for-byte checks compare with line endings normalised to LF.

## Built by tickets

### T01 (core)
- `cli.main(argv=None) -> int`; prints `engine: <name>` itself (T02 adds the scribe upload note).
- `engines.select(name)`: explicit `-e`/`VIDSCRIBE_ENGINE` is not checked for availability; auto-choice uses `get(name).available()` and treats an ImportError as unavailable.
- `mlx.DEFAULT_MODEL`, `mlx.available()`, `mlx.command(interp, wav, out_base, fmt, dur, opts, ram_bytes)`, `mlx.transcribe(...)`.
- Tests: `tests/test_cli.py`, `test_engines.py`, `test_media.py`, `test_mlx.py`, `test_subs.py` (38 tests).
- T01: for scribe, `cli` prints `engine: scribe (audio is uploaded to ElevenLabs)` itself — T02 does not touch cli.py.
- T03: `install.ps1 [-Local]`, `install.sh` (no args); both end with `uv tool install --force --python 3.12 <repo>[extras]` and replace `~/.claude/skills/vidscribe` with `skill/`.
- T02: `scribe.request` sends via `build_opener(_NoRedirect)` (test seam: `urllib.request.OpenerDirector.open`); `_check_key` rejects keys outside [!-~]; `whisper.DEFAULT_MODEL="large-v3-turbo"`, reads wav via `wave` + numpy (faster-whisper 1.2.1 vs PyAV 19).
- F1: `whisper.load(model, device="cuda")` creates on one device only; the CUDA→CPU fallback lives in `whisper.transcribe` and covers model creation and decoding. cli checks `no such file` before `engines.select`.
