"""vidscribe command line: argument parsing, the run flow and its output lines."""
import argparse
import os
import platform
import re
import sys
import tempfile
from pathlib import Path

from vidscribe import engines, media, subs

DESCRIPTION = """\
Speech-to-text for a video or audio file, or a URL (X, YouTube, etc., fetched with yt-dlp).
Prints the transcript path; text to stdout for txt.
Video (-f txt|srt) writes srt + txt and prints the video's path, so an agent can look at the picture with ffmpeg.
Downloaded videos stay in the vidscribe temp folder for 3 days; local files are used where they are.
-a/--audio-only: transcript only (URLs ask yt-dlp for audio only)."""


def removed(flag: str):
    class Removed(argparse.Action):
        def __init__(self, option_strings, dest, **kw):
            super().__init__(option_strings, dest, nargs=0, help=argparse.SUPPRESS)

        def __call__(self, *_):
            print(f"vidscribe: {flag} was removed (docs/decisions/0009-drop-picture-commands.md); "
                  "run ffmpeg on the video path a normal run prints", file=sys.stderr)
            sys.exit(1)
    return Removed


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"vidscribe: {message}", file=sys.stderr)
        sys.exit(1)


def parser() -> argparse.ArgumentParser:
    p = Parser(prog="vidscribe", description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("src", help="video or audio file, or URL")
    p.add_argument("-o", metavar="DIR", help="output folder (default: $VIDSCRIBE_OUTDIR or the temp folder)")
    p.add_argument("-l", metavar="LANG", help="language, e.g. en, ru (default: detect)")
    p.add_argument("-f", choices=("txt", "srt", "vtt", "json"), default="txt", help="output format (default: txt)")
    p.add_argument("-c", metavar="TEXT", help='hotwords / context, e.g. "Anthropic, Claude"')
    p.add_argument("-m", metavar="MODEL", help="engine model (mlx default: $VIDSCRIBE_MODEL)")
    p.add_argument("-e", choices=engines.NAMES, help="engine (default: $VIDSCRIBE_ENGINE or the best available)")
    p.add_argument("-n", type=int, metavar="N", help="maximum number of speakers (scribe)")
    p.add_argument("-a", "--audio-only", action="store_true", help="transcript only, no video")
    for flag in ("-v", "--at", "--scan"):
        p.add_argument(flag, action=removed(flag))
    return p


def err(line: str) -> None:
    print(line, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    if platform.system() == "Darwin":  # uv tools and Homebrew, as the original script did
        os.environ["PATH"] = os.pathsep.join(
            [str(Path.home() / ".local/bin"), "/opt/homebrew/bin", os.environ.get("PATH", "")])
    media.require_tools()
    media.prune()
    name = engines.select(args.e)
    err(f"engine: {name}" + (" (audio is uploaded to ElevenLabs)" if name == "scribe" else ""))
    engine = engines.get(name)
    opts = engines.Options(lang=args.l, context=args.c, model=args.m, speakers=args.n)
    fmt = args.f
    # keep the video for txt and srt runs, unless -a (vtt/json give a transcript only)
    want_video = not args.audio_only and fmt in ("txt", "srt")
    outdir = Path(args.o) if args.o else media.default_outdir()
    outdir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="vidscribe-", ignore_cleanup_errors=True) as t:
        tmp = Path(t)
        if re.match(r"https?://", args.src):
            src = media.download(args.src, tmp, want_video)
        else:
            src = Path(args.src)
            if not src.is_file():
                err(f"no such file: {args.src}")
                return 1
        out = outdir / src.stem
        srt = Path(f"{out}.srt")
        audio = media.has_audio(src)
        video = (want_video or not audio) and media.has_video(src)
        keep_video = want_video and video
        if not audio:
            if not video:
                err("vidscribe: no usable audio or video stream")
                return 1
            if not keep_video:
                err("vidscribe: no audio track to transcribe")
                return 1
            err("vidscribe: no audio track; writing an empty transcript")
            srt.write_text("")
        else:
            engine.transcribe(src, tmp, out, "srt" if keep_video else fmt, opts)

        if keep_video:
            subs.srt_to_txt(srt, Path(f"{out}.txt"))
            err(f"video: {media.keep_video(src, tmp)}")

        # truncation check: models have silently stopped early on long media before
        if audio and srt.is_file():
            cues = subs.read_srt(srt)
            last, dur = (cues[-1].end if cues else 0.0), media.duration(src)
            if dur - last > 30:
                err(f"WARNING: last cue {last:.0f}s < duration {dur:.0f}s; transcript ends early")

    err(f"transcript: {out}.{fmt}")
    if fmt == "txt":
        sys.stdout.write(Path(f"{out}.txt").read_text(encoding="utf-8"))
    return 0
