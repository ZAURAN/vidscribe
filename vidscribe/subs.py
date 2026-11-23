"""Transcript file formats: txt, srt, vtt."""
import re
from pathlib import Path
from typing import NamedTuple

_TS = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)")


class Cue(NamedTuple):
    start: float
    end: float
    text: str


def fmt_ts(seconds: float, sep: str = ",") -> str:
    """HH:MM:SS,mmm (sep "." for vtt)."""
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def write(cues: list[Cue], out_base: Path, fmt: str) -> Path:
    """Write out_base.<fmt> (txt: one cue per line) and return its path."""
    if fmt == "txt":
        body = "".join(c.text + "\n" for c in cues)
    elif fmt == "srt":
        body = "\n".join(f"{i}\n{fmt_ts(c.start)} --> {fmt_ts(c.end)}\n{c.text}\n"
                         for i, c in enumerate(cues, 1))
    elif fmt == "vtt":
        body = "WEBVTT\n" + "".join(f"\n{fmt_ts(c.start, '.')} --> {fmt_ts(c.end, '.')}\n{c.text}\n"
                                    for c in cues)
    else:
        raise ValueError(f"unsupported format: {fmt}")
    path = Path(f"{out_base}.{fmt}")
    path.write_text(body, encoding="utf-8", newline="\n")
    return path


def _seconds(ts: str) -> float:
    m = _TS.search(ts)
    if not m:
        return 0.0
    h, mi, s, ms = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(s) + int(ms) / 1000


def read_srt(path: Path) -> list[Cue]:
    cues = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip()):
        rows = block.strip().splitlines()
        for i, row in enumerate(rows):
            if "-->" in row:
                start, end = row.split("-->", 1)
                cues.append(Cue(_seconds(start), _seconds(end), " ".join(rows[i + 1:]).strip()))
                break
    return cues


def srt_to_txt(srt: Path, txt: Path) -> None:
    """txt from the srt, one cue per line."""
    txt.write_text("".join(c.text + "\n" for c in read_srt(srt)), encoding="utf-8", newline="\n")
