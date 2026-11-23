"""Engine choice. Each engine module exposes available() and transcribe(src, tmp, out_base, fmt, opts)."""
import importlib
import os
import platform
import sys
from dataclasses import dataclass
from types import ModuleType

NAMES = ("mlx", "scribe", "whisper")


@dataclass
class Options:
    lang: str | None = None
    context: str | None = None
    model: str | None = None
    speakers: int | None = None


def get(name: str) -> ModuleType:
    return importlib.import_module(f"{__name__}.{name}")


def _usable(name: str) -> bool:
    try:
        return bool(get(name).available())
    except ImportError:  # engine module or its dependency not installed
        return False


def _none_usable() -> str:
    system = platform.system()
    lines = ["vidscribe: no speech-to-text engine is set up. Pick one:"]
    if system == "Darwin" and platform.machine() == "arm64":
        lines.append("  mlx (local): uv tool install --force mlx-audio --prerelease=allow")
    if system == "Windows":
        key = '  then: setx ELEVENLABS_API_KEY "<your key>" and open a new terminal'
        local = "  whisper (local, NVIDIA GPU or CPU): install.ps1 -Local"
    else:
        key = "  then: echo 'export ELEVENLABS_API_KEY=<your key>' >> ~/.zshrc and open a new terminal"
        local = '  whisper (local): uv tool install --force --python 3.12 "<vidscribe repo>[local]"'
    lines += ["  scribe (cloud, audio is uploaded): get an API key at https://elevenlabs.io/app/settings/api-keys",
              key, local]
    return "\n".join(lines)


def select(name: str | None) -> str:
    """-e or $VIDSCRIBE_ENGINE, else mlx on Apple Silicon, scribe with a key, whisper if installed."""
    name = name or os.environ.get("VIDSCRIBE_ENGINE")
    if name:
        if name not in NAMES:
            print(f"vidscribe: unknown engine {name!r}; choose one of {', '.join(NAMES)}", file=sys.stderr)
            sys.exit(1)
        return name
    if _usable("mlx"):
        return "mlx"
    if os.environ.get("ELEVENLABS_API_KEY") and _usable("scribe"):
        return "scribe"
    if _usable("whisper"):
        return "whisper"
    print(_none_usable(), file=sys.stderr)
    sys.exit(1)
