import contextlib
import io
import os
import sys
import types
import unittest
from unittest import mock

from vidscribe import engines

KEY = "test-key-not-a-real-secret-123"


def fake_engine(ok):
    return types.SimpleNamespace(available=lambda: ok, transcribe=None)


class SelectTest(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        for k in ("VIDSCRIBE_ENGINE", "ELEVENLABS_API_KEY"):
            os.environ.pop(k, None)

    def machine(self, system, arch, mlx_on_path, whisper_ok=False, scribe_module=True):
        """Patch the platform, PATH and the optional engine modules."""
        which = lambda cmd: "/bin/" + cmd if mlx_on_path and cmd == "mlx_audio.stt.generate" else None
        modules = {
            "vidscribe.engines.scribe": fake_engine(True) if scribe_module else None,
            "vidscribe.engines.whisper": fake_engine(whisper_ok),
        }
        for p in (mock.patch("platform.system", return_value=system),
                  mock.patch("platform.machine", return_value=arch),
                  mock.patch("shutil.which", side_effect=which),
                  mock.patch.dict(sys.modules, modules)):
            p.start()
            self.addCleanup(p.stop)

    def select(self, name=None):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(err):
            try:
                return engines.select(name), err.getvalue()
            except SystemExit as e:
                return e.code, err.getvalue()

    def test_mac_arm64_with_mlx_audio_picks_mlx(self):
        self.machine("Darwin", "arm64", True, whisper_ok=True)
        os.environ["ELEVENLABS_API_KEY"] = KEY
        self.assertEqual(self.select()[0], "mlx")

    def test_mlx_needs_apple_silicon_and_mlx_audio(self):
        os.environ["ELEVENLABS_API_KEY"] = KEY
        self.machine("Darwin", "x86_64", True)
        self.assertEqual(self.select()[0], "scribe")

    def test_key_picks_scribe_on_windows(self):
        self.machine("Windows", "AMD64", False, whisper_ok=True)
        os.environ["ELEVENLABS_API_KEY"] = KEY
        self.assertEqual(self.select()[0], "scribe")

    def test_no_key_falls_back_to_whisper(self):
        self.machine("Windows", "AMD64", False, whisper_ok=True)
        self.assertEqual(self.select()[0], "whisper")

    def test_missing_scribe_module_is_not_offered(self):
        self.machine("Windows", "AMD64", False, whisper_ok=True, scribe_module=False)
        os.environ["ELEVENLABS_API_KEY"] = KEY
        self.assertEqual(self.select()[0], "whisper")

    def test_explicit_name_and_env_win(self):
        self.machine("Darwin", "arm64", True, whisper_ok=True)
        self.assertEqual(self.select("whisper")[0], "whisper")
        os.environ["VIDSCRIBE_ENGINE"] = "scribe"
        self.assertEqual(self.select()[0], "scribe")
        self.assertEqual(self.select("mlx")[0], "mlx")

    def test_unknown_name_exits_1(self):
        self.machine("Windows", "AMD64", False)
        code, err = self.select("nope")
        self.assertEqual(code, 1)
        self.assertIn("nope", err)

    def test_none_usable_exits_1_with_windows_hint(self):
        self.machine("Windows", "AMD64", False)
        code, err = self.select()
        self.assertEqual(code, 1)
        self.assertIn("setx ELEVENLABS_API_KEY", err)
        self.assertIn("install.ps1 -Local", err)

    def test_none_usable_exits_1_with_mac_hint(self):
        self.machine("Darwin", "arm64", False)
        code, err = self.select()
        self.assertEqual(code, 1)
        self.assertIn("~/.zshrc", err)
        self.assertIn("mlx-audio", err)

    def test_key_value_never_printed(self):
        self.machine("Windows", "AMD64", False)
        os.environ["ELEVENLABS_API_KEY"] = KEY
        for name in (None, "scribe", "nope"):
            self.assertNotIn(KEY, self.select(name)[1])


if __name__ == "__main__":
    unittest.main()
