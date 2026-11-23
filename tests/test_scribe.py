import contextlib
import email
import email.policy
import http.client
import http.server
import io
import json
import os
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from vidscribe import media
from vidscribe.engines import Options, scribe
from vidscribe.subs import Cue

KEY = "test-key-not-a-real-secret-123"


def w(text, start, end, speaker="speaker_0", kind="word"):
    return {"text": text, "start": start, "end": end, "type": kind, "speaker_id": speaker}


def sp(at, speaker="speaker_0"):
    return w(" ", at, at, speaker, "spacing")


def response(payload):
    """A urlopen() stand-in returning payload as the JSON body."""
    r = mock.MagicMock()
    r.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    return r


def form_fields(req):
    """Parse the multipart body the way a server would: [(name, value or bytes)]."""
    raw = b"Content-Type: " + req.get_header("Content-type").encode() + b"\r\n\r\n" + req.data
    msg = email.message_from_bytes(raw, policy=email.policy.HTTP)
    out = []
    for part in msg.iter_parts():
        name = part.get_param("name", header="content-disposition")
        body = part.get_payload(decode=True)
        out.append((name, body if part.get_filename() else body.decode()))
    return out


class RequestTest(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.audio = Path(d.name) / "audio.mp3"
        self.audio.write_bytes(b"ID3fake-mp3")

    def send(self, opts, payload=None):
        with mock.patch("urllib.request.OpenerDirector.open", return_value=response(payload or {"words": []})) as op:
            result = scribe.request(self.audio, KEY, opts)
        req = op.call_args.args[0]
        return req, result

    def test_fields_and_header(self):
        req, result = self.send(Options(lang="en", context="Anthropic, Claude Code", speakers=2),
                                {"language_code": "en", "words": []})
        self.assertEqual(req.full_url, "https://api.elevenlabs.io/v1/speech-to-text")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.get_header("Xi-api-key"), KEY)
        fields = form_fields(req)
        self.assertEqual(sorted(f for f in fields if f[0] != "file"), sorted([
            ("model_id", "scribe_v3"), ("diarize", "true"), ("tag_audio_events", "true"),
            ("timestamps_granularity", "word"), ("language_code", "en"), ("num_speakers", "2"),
            ("keyterms", "Anthropic"), ("keyterms", "Claude Code"),
        ]))
        self.assertEqual(dict(fields)["file"], b"ID3fake-mp3")
        self.assertEqual(result, {"language_code": "en", "words": []})

    def test_model_flag_and_no_optional_fields(self):
        req, _ = self.send(Options(model="scribe_v2"))
        names = dict(form_fields(req))
        self.assertEqual(names["model_id"], "scribe_v2")
        for absent in ("language_code", "num_speakers", "keyterms"):
            self.assertNotIn(absent, names)

    def fail(self, exc):
        err = io.StringIO()
        with mock.patch("urllib.request.OpenerDirector.open", side_effect=exc) as op, \
                contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            scribe.request(self.audio, KEY, Options())
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(op.call_count, 1)  # a paid request is never retried
        self.assertNotIn(KEY, err.getvalue())
        return err.getvalue()

    def test_http_error(self):
        body = json.dumps({"detail": {"status": "invalid_api_key", "message": "Invalid API key"}}).encode()
        exc = urllib.error.HTTPError(scribe.API, 401, "Unauthorized", {}, io.BytesIO(body))
        self.assertIn("ElevenLabs API error 401: Invalid API key", self.fail(exc))

    def test_http_error_echoing_the_key_is_redacted(self):
        body = json.dumps({"detail": f"bad key {KEY}"}).encode()
        exc = urllib.error.HTTPError(scribe.API, 403, "Forbidden", {}, io.BytesIO(body))
        self.assertIn("ElevenLabs API error 403: bad key", self.fail(exc))

    def test_network_error(self):
        self.assertIn("cannot reach ElevenLabs: ", self.fail(urllib.error.URLError("getaddrinfo failed")))

    def test_response_cut_off(self):
        r = mock.MagicMock()
        r.__enter__.return_value.read.side_effect = http.client.IncompleteRead(b"{\"wor", 900)
        self.assertIn("vidscribe: cannot reach ElevenLabs: ", self.fail([r]))

    def test_200_that_is_not_json(self):
        r = mock.MagicMock()
        r.__enter__.return_value.read.return_value = b"<html>gateway</html>"
        self.assertIn("vidscribe: ElevenLabs API error 200: invalid response", self.fail([r]))

    def test_bad_key_rejected_before_sending_and_not_printed(self):
        for bad in ("sk_abc\r\nX-Evil: 1secretpart", "sk_abc secretpart", "sk_abc’secretpart"):
            err = io.StringIO()
            with mock.patch("urllib.request.OpenerDirector.open") as op, \
                    contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
                scribe.request(self.audio, bad, Options())
            self.assertEqual(cm.exception.code, 1)
            op.assert_not_called()
            self.assertIn("ELEVENLABS_API_KEY", err.getvalue())
            self.assertNotIn("secretpart", err.getvalue())


class Recorder(http.server.BaseHTTPRequestHandler):
    """Local server: /redirect answers 302 to self.server.target; anything else is recorded."""
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", self.server.target)
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self.server.hits.append(dict(self.headers))
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

    do_GET = do_POST

    def log_message(self, *_):
        pass


class RedirectTest(unittest.TestCase):
    def serve(self):
        s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Recorder)
        s.hits, s.target = [], ""
        threading.Thread(target=s.serve_forever, daemon=True).start()
        self.addCleanup(s.server_close)
        self.addCleanup(s.shutdown)
        return s, f"http://127.0.0.1:{s.server_address[1]}"

    def test_redirect_is_not_followed_and_the_key_stays_put(self):
        api, api_url = self.serve()
        other, other_url = self.serve()
        api.target = other_url + "/stolen"
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        audio = Path(d.name) / "audio.mp3"
        audio.write_bytes(b"mp3")
        err = io.StringIO()
        with mock.patch.object(scribe, "API", api_url + "/redirect"), \
                mock.patch.dict(os.environ, {"NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1"}), \
                contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            scribe.request(audio, KEY, Options())
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(other.hits, [])  # the redirect target never saw a request, let alone the key
        self.assertIn("ElevenLabs API error 302", err.getvalue())
        self.assertNotIn(KEY, err.getvalue())


class CuesTest(unittest.TestCase):
    def test_breaks_on_sentence_pause_and_speaker(self):
        words = [w("Hello", 0.0, 0.4), sp(0.4), w("there.", 0.5, 0.9), sp(0.9),
                 w("How", 1.0, 1.2), sp(1.2), w("are", 1.3, 1.5),
                 w("(laughter)", 1.6, 2.0, kind="audio_event"), sp(2.0),
                 w("you", 3.5, 3.8), sp(3.8), w("Fine", 3.9, 4.2, "speaker_1")]
        self.assertEqual(scribe.to_cues(words), [
            Cue(0.0, 0.9, "[speaker_0] Hello there."),
            Cue(1.0, 2.0, "[speaker_0] How are (laughter)"),
            Cue(3.5, 3.8, "[speaker_0] you"),
            Cue(3.9, 4.2, "[speaker_1] Fine"),
        ])

    def test_one_speaker_no_label_and_7s_limit(self):
        words = []
        for i in range(10):
            words += [w(f"w{i}", float(i), i + 0.9), sp(i + 0.9)]
        self.assertEqual(scribe.to_cues(words), [
            Cue(0.0, 6.9, "w0 w1 w2 w3 w4 w5 w6"),
            Cue(7.0, 9.9, "w7 w8 w9"),
        ])

    def test_empty(self):
        self.assertEqual(scribe.to_cues([]), [])


class TranscribeTest(unittest.TestCase):
    PAYLOAD = {"language_code": "en", "words": [w("Hi.", 0.0, 0.5), sp(0.5), w("Bye.", 2.0, 2.4)]}

    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.dir = Path(d.name)
        self.extract = mock.patch.object(media, "extract_audio", side_effect=self.fake_extract)
        self.extract.start()
        self.addCleanup(self.extract.stop)

    def fake_extract(self, src, dst):
        self.extracted = dst
        dst.write_bytes(b"mp3")
        return dst

    def run_engine(self, fmt):
        os.environ["ELEVENLABS_API_KEY"] = KEY
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("urllib.request.OpenerDirector.open", return_value=response(self.PAYLOAD)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            scribe.transcribe(self.dir / "in.mp4", self.dir, self.dir / "clip", fmt, Options())
        self.assertNotIn(KEY, out.getvalue() + err.getvalue())
        text = Path(f"{self.dir / 'clip'}.{fmt}").read_text(encoding="utf-8")
        self.assertNotIn(KEY, text)
        return text

    def test_srt_and_mp3(self):
        self.assertEqual(self.run_engine("srt"),
                         "1\n00:00:00,000 --> 00:00:00,500\nHi.\n\n2\n00:00:02,000 --> 00:00:02,400\nBye.\n")
        self.assertEqual(self.extracted.suffix, ".mp3")  # mono 64 kbit/s by media.extract_audio

    def test_txt(self):
        self.assertEqual(self.run_engine("txt"), "Hi.\nBye.\n")

    def test_json_is_the_raw_response(self):
        self.assertEqual(json.loads(self.run_engine("json")), self.PAYLOAD)

    def no_key(self, system):
        os.environ.pop("ELEVENLABS_API_KEY", None)
        err = io.StringIO()
        with mock.patch("platform.system", return_value=system), mock.patch("urllib.request.OpenerDirector.open") as op, \
                contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            scribe.transcribe(self.dir / "in.mp4", self.dir, self.dir / "clip", "txt", Options())
        self.assertEqual(cm.exception.code, 1)
        op.assert_not_called()
        self.assertIn("ELEVENLABS_API_KEY", err.getvalue())
        self.assertIn("elevenlabs.io", err.getvalue())
        return err.getvalue()

    def test_no_key_windows(self):
        self.assertIn('setx ELEVENLABS_API_KEY "<your key>"', self.no_key("Windows"))

    def test_no_key_mac(self):
        self.assertIn("export ELEVENLABS_API_KEY=<your key>' >> ~/.zshrc", self.no_key("Darwin"))


if __name__ == "__main__":
    unittest.main()
