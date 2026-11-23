"""Local faster-whisper: NVIDIA GPU (CUDA float16) or CPU (int8), on any OS."""
import json
import os
import platform
import sys
import wave
from pathlib import Path

from vidscribe import media, subs

DEFAULT_MODEL = "large-v3-turbo"
_dll_dirs = []  # keep the add_dll_directory handles alive


def _add_cuda_dlls() -> None:
    """Windows: CUDA DLLs come from the nvidia-* pip packages (site-packages/nvidia/*/bin)."""
    if platform.system() != "Windows" or _dll_dirs:
        return
    for base in sys.path:
        for d in sorted(Path(base or ".").glob("nvidia/*/bin")):
            _dll_dirs.append(os.add_dll_directory(str(d)))
            # ctranslate2 loads cuDNN/cuBLAS lazily with a plain LoadLibrary, which searches PATH
            os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")


def available() -> bool:
    _add_cuda_dlls()
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def _whisper_model():
    """faster_whisper.WhisperModel; exits 1 with an install hint when faster-whisper is missing."""
    _add_cuda_dlls()
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        if platform.system() == "Windows":
            how = "install.ps1 -Local"
        else:
            how = 'uv tool install --force --python 3.12 "<vidscribe repo>[local]"'
        print(f"vidscribe: the whisper engine needs faster-whisper ({e}); install it: {how}", file=sys.stderr)
        sys.exit(1)
    return WhisperModel


def load(model: str, device: str = "cuda"):
    """CUDA float16 or CPU int8; a CUDA failure raises (transcribe falls back to CPU)."""
    WhisperModel = _whisper_model()
    if device == "cpu":
        return WhisperModel(model, device="cpu", compute_type="int8")
    m = WhisperModel(model, device="cuda", compute_type="float16")
    print(f"whisper: {model} on CUDA (float16)", file=sys.stderr)
    return m


def _samples(wav: Path):
    """16 kHz mono PCM as float32. Decoding it here keeps PyAV out of the way: faster-whisper 1.2.1
    passes av.open() an argument PyAV 19 removed."""
    import numpy as np  # a faster-whisper dependency
    with wave.open(str(wav), "rb") as f:
        pcm = f.readframes(f.getnframes())
    return np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0


def transcribe(src: Path, tmp: Path, out_base: Path, fmt: str, opts) -> None:
    _whisper_model()  # an install hint before any ffmpeg work
    name = opts.model or DEFAULT_MODEL
    samples = _samples(media.extract_audio(src, tmp / "in16k.wav"))

    def recognize(model):
        # vad_filter skips silence, where whisper tends to invent text
        segments, info = model.transcribe(samples, language=opts.lang, hotwords=opts.context, vad_filter=True)
        return [subs.Cue(s.start, s.end, s.text.strip()) for s in segments if s.text.strip()], info

    try:
        cues, info = recognize(load(name))
    # no GPU, no driver, missing DLLs, no CUDA build (macOS); CUDA can also load and then fail
    # at the first decode, when ctranslate2 loads cuBLAS/cuDNN lazily
    except Exception as e:
        print(f"warning: CUDA unavailable ({e}), using CPU", file=sys.stderr)
        cues, info = recognize(load(name, "cpu"))
    if fmt == "json":
        data = {"language": info.language, "segments": [c._asdict() for c in cues]}
        Path(f"{out_base}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                                            encoding="utf-8", newline="\n")
    else:
        subs.write(cues, out_base, fmt)
