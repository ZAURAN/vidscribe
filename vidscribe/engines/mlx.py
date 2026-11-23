"""Local Qwen3-ASR via mlx-audio (Apple Silicon Macs), run exactly as the original bash script did."""
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from vidscribe import media

DEFAULT_MODEL = "mlx-community/Qwen3-ASR-1.7B-8bit"
GENERATE = "mlx_audio.stt.generate"
PATCH = Path(__file__).with_name("mlx_patch.py")


def available() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64" and bool(shutil.which(GENERATE))


def command(interp: str, wav: Path, out_base: Path, fmt: str, dur: float, opts, ram_bytes: int) -> list[str]:
    # mlx-audio spends one --max-tokens budget (default 8192) on the whole file: dense speech ran out
    # after ~13-55 min, and a repetition loop could burn it all. So give the file a budget that never
    # binds; mlx_patch.py caps each ~30 s piece at 25 tok/s instead (real speech peaks ~16).
    # Pieces decoded 32 at a time: 2.6x faster on a 64-min talk, 6.1 GB peak GPU memory; 8 fits Macs under 16 GB.
    cmd = [interp, "-",
           "--model", opts.model or os.environ.get("VIDSCRIBE_MODEL") or DEFAULT_MODEL,
           "--audio", str(wav), "--output-path", str(out_base), "--format", fmt,
           "--max-tokens", str(int(8192 + 32 * dur)),
           "--max-parallel-segments", "32" if ram_bytes >= 16 * 1024 ** 3 else "8"]
    if opts.lang:
        cmd += ["--language", opts.lang]
    if opts.context:
        cmd += ["--context", opts.context]
    return cmd


def transcribe(src: Path, tmp: Path, out_base: Path, fmt: str, opts) -> None:
    exe = shutil.which(GENERATE)
    if not available() or not exe:
        print("vidscribe: the mlx engine needs an Apple Silicon Mac with mlx-audio "
              "(uv tool install --force mlx-audio --prerelease=allow)", file=sys.stderr)
        sys.exit(1)
    with open(exe, "rb") as f:
        interp = f.readline()[2:].strip().decode()  # the shebang's interpreter has mlx-audio
    wav = media.extract_audio(src, tmp / "in16k.wav")
    ram = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout)
    cmd = command(interp, wav, out_base, fmt, media.duration(wav), opts, ram)
    sys.stderr.flush()
    r = subprocess.run(cmd, input=PATCH.read_bytes(), stdout=sys.stderr.fileno())
    if r.returncode:
        print(f"vidscribe: mlx-audio failed (exit {r.returncode})", file=sys.stderr)
        sys.exit(1)
