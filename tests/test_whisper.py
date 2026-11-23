import contextlib
import importlib.util
import io
import json
import os
import struct
import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path
from unittest import mock

from vidscribe import media
from vidscribe.engines import Options, whisper

if importlib.util.find_spec("numpy"):
    import numpy  # noqa: F401  loaded before patch.dict(sys.modules) snapshots; numpy can't load twice

Segment = types.SimpleNamespace


class FakeModel:
    """Stands in for faster_whisper.WhisperModel; records what it was given."""
    events = []
    fail_cuda = False
    fail_cuda_decode = False  # the model loads on CUDA, but decoding needs a DLL that is missing

    def __init__(self, model, device, compute_type):
        FakeModel.events.append(("init", model, device, compute_type))
        self.device = device
        if device == "cuda" and FakeModel.fail_cuda:
            raise RuntimeError("CUDA driver version is insufficient")

    def transcribe(self, audio, **kw):
        FakeModel.events.append(("transcribe", audio, kw))
        segs = [Segment(start=0.0, end=1.5, text=" Hello world."), Segment(start=2.0, end=3.25, text=" Bye.")]

        def lazy():  # faster-whisper decodes while the segments are iterated
            if self.device == "cuda" and FakeModel.fail_cuda_decode:
                raise RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")
            yield from segs
        return lazy(), types.SimpleNamespace(language="en")


def fake_extract(src, dst):
    """What ffmpeg writes for .wav: 16 kHz mono 16-bit PCM (three samples here)."""
    with wave.open(str(dst), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(struct.pack("<3h", 0, 16384, -32768))
    return dst


@unittest.skipUnless(importlib.util.find_spec("numpy"), "numpy (a faster-whisper dependency) is not installed")
class WhisperTest(unittest.TestCase):
    def setUp(self):
        FakeModel.events, FakeModel.fail_cuda, FakeModel.fail_cuda_decode = [], False, False
        fake = types.ModuleType("faster_whisper")
        fake.WhisperModel = FakeModel
        for p in (mock.patch.dict(sys.modules, {"faster_whisper": fake}),
                  mock.patch("platform.system", return_value="Linux"),
                  mock.patch.object(media, "extract_audio", side_effect=fake_extract)):
            p.start()
            self.addCleanup(p.stop)
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.dir = Path(d.name)

    def run_engine(self, fmt, opts=None):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            whisper.transcribe(self.dir / "in.mp4", self.dir, self.dir / "clip", fmt, opts or Options())
        self.err = err.getvalue()
        return Path(f"{self.dir / 'clip'}.{fmt}").read_text(encoding="utf-8")

    def test_available_only_with_faster_whisper(self):
        self.assertTrue(whisper.available())
        with mock.patch.dict(sys.modules, {"faster_whisper": None}):  # None makes the import fail
            self.assertFalse(whisper.available())

    def test_defaults_cuda_and_srt(self):
        self.assertEqual(self.run_engine("srt"),
                         "1\n00:00:00,000 --> 00:00:01,500\nHello world.\n\n"
                         "2\n00:00:02,000 --> 00:00:03,250\nBye.\n")
        init, (_, audio, kw) = FakeModel.events
        self.assertEqual(init, ("init", "large-v3-turbo", "cuda", "float16"))
        self.assertEqual(list(audio), [0.0, 0.5, -1.0])  # the 16 kHz wav as float32 samples
        self.assertEqual(str(audio.dtype), "float32")
        self.assertTrue(kw["vad_filter"])
        self.assertIsNone(kw.get("language"))
        self.assertIsNone(kw.get("hotwords"))
        self.assertIn("cuda", self.err.lower())

    def test_flags_reach_the_model(self):
        self.run_engine("txt", Options(lang="ru", context="Anthropic, Claude", model="small"))
        init, (_, _, kw) = FakeModel.events
        self.assertEqual(init[1], "small")
        self.assertEqual(kw["language"], "ru")
        self.assertEqual(kw["hotwords"], "Anthropic, Claude")

    def test_txt_and_vtt(self):
        self.assertEqual(self.run_engine("txt"), "Hello world.\nBye.\n")
        self.assertTrue(self.run_engine("vtt").startswith("WEBVTT\n\n00:00:00.000 --> 00:00:01.500\nHello world.\n"))

    def test_json_has_language_and_segments(self):
        self.assertEqual(json.loads(self.run_engine("json")), {
            "language": "en",
            "segments": [{"start": 0.0, "end": 1.5, "text": "Hello world."},
                         {"start": 2.0, "end": 3.25, "text": "Bye."}],
        })

    def test_cpu_fallback_with_warning(self):
        FakeModel.fail_cuda = True
        self.run_engine("txt")
        inits = [e for e in FakeModel.events if e[0] == "init"]
        self.assertEqual(inits, [("init", "large-v3-turbo", "cuda", "float16"),
                                 ("init", "large-v3-turbo", "cpu", "int8")])
        self.assertIn("warning: CUDA unavailable (CUDA driver version is insufficient), using CPU", self.err)

    def test_cuda_failure_while_decoding_retries_on_cpu(self):
        FakeModel.fail_cuda_decode = True
        self.assertEqual(self.run_engine("txt"), "Hello world.\nBye.\n")
        inits = [e for e in FakeModel.events if e[0] == "init"]
        self.assertEqual(inits, [("init", "large-v3-turbo", "cuda", "float16"),
                                 ("init", "large-v3-turbo", "cpu", "int8")])
        self.assertIn("warning: CUDA unavailable (Library cublas64_12.dll is not found or cannot be loaded), "
                      "using CPU", self.err)

    def not_installed(self, system):
        err = io.StringIO()
        with mock.patch.dict(sys.modules, {"faster_whisper": None}), \
                mock.patch("platform.system", return_value=system), mock.patch.object(whisper, "_dll_dirs", [None]), \
                contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            whisper.transcribe(self.dir / "in.mp4", self.dir, self.dir / "clip", "txt", Options())
        self.assertEqual(cm.exception.code, 1)
        self.assertTrue(err.getvalue().startswith("vidscribe: "), err.getvalue())
        self.assertIn("faster-whisper", err.getvalue())
        media.extract_audio.assert_not_called()  # fails before any ffmpeg work
        return err.getvalue()

    def test_not_installed_windows_hint(self):
        self.assertIn("install.ps1 -Local", self.not_installed("Windows"))

    def test_not_installed_hint(self):
        self.assertIn('uv tool install --force --python 3.12 "<vidscribe repo>[local]"', self.not_installed("Linux"))

    def test_windows_adds_nvidia_dll_folders_before_import(self):
        site = self.dir / "site-packages"
        bins = [site / "nvidia" / pkg / "bin" for pkg in ("cublas", "cudnn")]
        for b in bins:
            b.mkdir(parents=True)
        (site / "nvidia" / "nobin").mkdir()
        added = []

        def add_dll_directory(path):
            added.append(Path(path))
            FakeModel.events.append(("dll", Path(path)))

        with mock.patch("platform.system", return_value="Windows"), \
                mock.patch.object(sys, "path", [str(site)] + sys.path), \
                mock.patch.dict(os.environ, {"PATH": "C:\\x"}), mock.patch.object(whisper, "_dll_dirs", []), \
                mock.patch.object(os, "add_dll_directory", side_effect=add_dll_directory, create=True):
            self.run_engine("txt")
            path = os.environ["PATH"]
        self.assertEqual(sorted(added), sorted(bins))
        self.assertEqual(FakeModel.events[0][0], "dll")  # before the model is created
        for b in bins:
            self.assertIn(str(b), path)


if __name__ == "__main__":
    unittest.main()
