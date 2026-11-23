"""ffmpeg, ffprobe, yt-dlp and the output folders."""
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# temp is cleared on reboot at best, so outputs are pruned at startup after 3 days
ROOT = Path(tempfile.gettempdir()) / "vidscribe" if platform.system() == "Windows" else Path("/tmp/vidscribe")

VIDEO_FORMATS = "bv*[height<=720]+ba/b[height<=720]/b/bv[height<=720]/bv/ba"
AUDIO_FORMATS = "ba/b"


def default_outdir() -> Path:
    return Path(os.environ.get("VIDSCRIBE_OUTDIR") or ROOT / "transcripts")


def require_tools() -> None:
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return
    system = platform.system()
    if system == "Windows":
        hint = "winget install --id Gyan.FFmpeg -e   (then open a new terminal)"
    elif system == "Darwin":
        hint = "brew install ffmpeg"
    else:
        hint = "install ffmpeg with your package manager, e.g. sudo apt install ffmpeg"
    print(f"vidscribe: ffmpeg and ffprobe must be on PATH; install them with:\n  {hint}", file=sys.stderr)
    sys.exit(1)


def prune(days: int = 3) -> None:
    """Remove ROOT/{transcripts,videos,frames}/* older than `days` (frames/ is left over from v1)."""
    cutoff = time.time() - days * 86400
    for d in ("transcripts", "videos", "frames"):
        try:
            entries = list((ROOT / d).iterdir())
        except OSError:
            continue
        for p in entries:
            try:
                if p.lstat().st_mtime >= cutoff:
                    continue
                if p.is_dir() and not p.is_symlink():
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    p.unlink()
            except OSError:
                pass


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, encoding="utf-8", errors="replace", **kw)


def download(url: str, dest: Path, want_video: bool) -> Path:
    """Fetch one file with yt-dlp into dest; returns its path."""
    # --no-playlist: a watch?v=…&list=… link fetches that one video, not the whole playlist.
    r = _run([sys.executable, "-m", "yt_dlp", "-q", "--no-warnings", "--no-playlist", "--no-simulate",
              "--no-mtime", "--print", "after_move:filepath",
              "-f", VIDEO_FORMATS if want_video else AUDIO_FORMATS, "--merge-output-format", "mp4",
              "-o", str(dest / "%(id)s.%(ext)s"), url],
             env={**os.environ, "PYTHONUTF8": "1"})
    lines = r.stdout.splitlines()
    if r.returncode or not lines or not lines[0]:
        print(f"vidscribe: yt-dlp could not download {url}", file=sys.stderr)
        sys.exit(1)
    return Path(lines[0])  # first file only (an X post with several videos is still a playlist)


def _streams(p: Path, select: str) -> bool:
    r = _run(["ffprobe", "-v", "quiet", "-select_streams", select, "-show_entries", "stream=index",
              "-of", "csv=p=0", str(p)])
    return bool(r.stdout.strip())


def has_audio(p: Path) -> bool:
    return _streams(p, "a:u")


def has_video(p: Path) -> bool:
    # Uppercase V excludes attached cover art; u requires usable codec parameters.
    return _streams(p, "V:u")


def duration(p: Path) -> float:
    r = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def extract_audio(src: Path, dst: Path) -> Path:
    """.wav: 16 kHz mono PCM; .mp3: mono 64 kbit/s."""
    codec = ["-ar", "16000"] if dst.suffix == ".wav" else ["-b:a", "64k"]
    r = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(src), "-ac", "1",
                        *codec, str(dst)])
    if r.returncode:
        print(f"vidscribe: ffmpeg could not extract audio from {src}", file=sys.stderr)
        sys.exit(1)
    return dst


def keep_video(src: Path, tmp: Path) -> Path:
    """Downloads are bulky: move them to ROOT/videos (pruned after 3 days); local files stay put."""
    if src.resolve().is_relative_to(tmp.resolve()):
        vid = ROOT / "videos" / src.name
        vid.parent.mkdir(parents=True, exist_ok=True)
        vid.unlink(missing_ok=True)  # mv -f
        shutil.move(src, vid)
        return vid
    return src.absolute()
