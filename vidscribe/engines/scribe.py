"""ElevenLabs Scribe: cloud speech-to-text with speaker labels and audio events (stdlib only)."""
import http.client
import json
import os
import platform
import re
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from vidscribe import media, subs

API = "https://api.elevenlabs.io/v1/speech-to-text"
DEFAULT_MODEL = "scribe_v3"
TIMEOUT = 3600  # a long file can take a while; the paid request is never retried
SENTENCE_END = ".?!…。？！"


def available() -> bool:
    return True  # stdlib only; the key is checked when it runs


def _fail(line: str, key: str) -> None:
    print(line.replace(key, "<ELEVENLABS_API_KEY>") if key else line, file=sys.stderr)
    sys.exit(1)


def _no_key() -> str:
    if platform.system() == "Windows":
        how = 'setx ELEVENLABS_API_KEY "<your key>"   (then open a new terminal)'
    else:
        how = "echo 'export ELEVENLABS_API_KEY=<your key>' >> ~/.zshrc   (then open a new terminal)"
    return ("vidscribe: the scribe engine needs ELEVENLABS_API_KEY.\n"
            "  get a key at https://elevenlabs.io/app/settings/api-keys\n"
            f"  set it yourself: {how}")


def _multipart(fields: list[tuple[str, str]], audio: Path) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
             for name, value in fields]
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{audio.name}"\r\n'
                 "Content-Type: audio/mpeg\r\n\r\n".encode() + audio.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _error_message(e: urllib.error.HTTPError) -> str:
    raw = e.read().decode("utf-8", "replace")
    try:
        detail = json.loads(raw).get("detail")
    except (ValueError, AttributeError):
        return raw.strip()[:500] or str(e.reason)
    if isinstance(detail, dict):
        return str(detail.get("message") or detail)
    if isinstance(detail, list):  # validation errors
        return "; ".join(str(d.get("msg", d)) if isinstance(d, dict) else str(d) for d in detail)
    return str(detail or e.reason)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A 3xx would resend xi-api-key to wherever Location points; surface it as an API error instead."""
    def redirect_request(self, *_):
        return None


def _check_key(key: str) -> None:
    # http.client would raise with the whole key in the traceback; never echo it
    if not re.fullmatch(r"[\x21-\x7e]+", key):
        _fail("vidscribe: ELEVENLABS_API_KEY has spaces, line breaks or non-ASCII characters; "
              "copy the key again and set it anew", "")


def request(audio: Path, key: str, opts) -> dict:
    """POST the audio to Scribe; exits 1 on an API or network error. Redirects are not followed."""
    _check_key(key)
    fields = [("model_id", opts.model or DEFAULT_MODEL), ("diarize", "true"),
              ("tag_audio_events", "true"), ("timestamps_granularity", "word")]
    if opts.lang:
        fields.append(("language_code", opts.lang))
    if opts.speakers:
        fields.append(("num_speakers", str(opts.speakers)))
    if opts.context:
        fields += [("keyterms", t.strip()) for t in opts.context.split(",") if t.strip()]
    body, ctype = _multipart(fields, audio)
    req = urllib.request.Request(API, data=body, method="POST",
                                 headers={"xi-api-key": key, "Content-Type": ctype})
    try:
        with urllib.request.build_opener(_NoRedirect).open(req, timeout=TIMEOUT) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        _fail(f"vidscribe: ElevenLabs API error {e.code}: {_error_message(e)}", key)
    except (urllib.error.URLError, OSError, http.client.HTTPException) as e:  # incl. a body cut off mid-read
        _fail(f"vidscribe: cannot reach ElevenLabs: {getattr(e, 'reason', e)}", key)
    try:
        data = json.loads(raw)
    except ValueError:
        data = None
    if not isinstance(data, dict):  # e.g. a proxy's HTML page
        _fail("vidscribe: ElevenLabs API error 200: invalid response", key)
    return data


def to_cues(words: list[dict]) -> list[subs.Cue]:
    """Group words into cues: new cue on a speaker change, a pause > 1 s, a sentence end, or > 7 s."""
    groups = []  # [speaker, start, end, text, ends_sentence]
    for w in words:
        kind = w.get("type", "word")
        if kind == "spacing":
            if groups:
                groups[-1][3] += w.get("text", " ")
            continue
        text = w.get("text", "")
        if kind == "audio_event":
            text = f" ({text.strip(' ()[]')}) "
        speaker, start, end = w.get("speaker_id"), float(w["start"]), float(w["end"])
        g = groups[-1] if groups else None
        if g is None or speaker != g[0] or start - g[2] > 1 or g[4] or end - g[1] > 7:
            groups.append([speaker, start, end, text, False])
        else:
            g[2], g[3] = end, g[3] + text
        groups[-1][4] = text.rstrip()[-1:] in SENTENCE_END if kind == "word" else False
    many = len({g[0] for g in groups}) > 1
    return [subs.Cue(start, end, (f"[{speaker}] " if many else "") + " ".join(text.split()))
            for speaker, start, end, text, _ in groups]


def transcribe(src: Path, tmp: Path, out_base: Path, fmt: str, opts) -> None:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        _fail(_no_key(), "")
    _check_key(key)  # before spending time on the audio
    # mono 64 kbit/s mp3: ~30 MB an hour of upload
    audio = media.extract_audio(src, tmp / "audio.mp3")
    resp = request(audio, key, opts)
    if fmt == "json":
        Path(f"{out_base}.json").write_text(json.dumps(resp, ensure_ascii=False, indent=2) + "\n",
                                            encoding="utf-8", newline="\n")
    else:
        subs.write(to_cues(resp.get("words") or []), out_base, fmt)
