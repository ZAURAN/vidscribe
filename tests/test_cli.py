import contextlib
import io
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from vidscribe import cli, media

REPO = Path(__file__).resolve().parent.parent
HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
KEY = "test-key-not-a-real-secret-123"
REMOVED = ("vidscribe: {} was removed (docs/decisions/0009-drop-picture-commands.md); "
           "run ffmpeg on the video path a normal run prints")


def make_video(path, seconds, audio=True):
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y",
           "-f", "lavfi", "-i", f"testsrc=duration={seconds}:size=64x48:rate=5"]
    cmd += ["-f", "lavfi", "-i", f"sine=duration={seconds}"] if audio else ["-an"]
    subprocess.run(cmd + [str(path)], check=True)


def srt_until(end):
    return f"1\n00:00:01,000 --> 00:00:{end:02d},000\nпривет мир\n"


class Base(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.tmp = Path(t.name)
        self.outdir = self.tmp / "text"
        env = mock.patch.dict(os.environ, {"VIDSCRIBE_OUTDIR": str(self.outdir)})
        env.start()
        self.addCleanup(env.stop)
        for k in ("VIDSCRIBE_ENGINE", "ELEVENLABS_API_KEY"):
            os.environ.pop(k, None)
        self.calls = []

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = cli.main(list(argv))
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def fake_engine(self, name, srt):
        """Install a stand-in for engines/<name>.py that writes `srt` as its output."""
        def transcribe(src, tmp, out_base, fmt, opts):
            self.calls.append((src, fmt, opts))
            Path(f"{out_base}.{fmt}").write_text(srt, encoding="utf-8")
        fake = types.SimpleNamespace(available=lambda: True, transcribe=transcribe)
        p = mock.patch.dict(sys.modules, {f"vidscribe.engines.{name}": fake})
        p.start()
        self.addCleanup(p.stop)


class CliTest(Base):

    def test_removed_flags(self):
        for argv in (["-v"], ["--at", "12"], ["--scan"], ["clip.mp4", "--scan"]):
            code, _, err = self.run_cli(*argv)
            self.assertEqual(code, 1, argv)
            flag = next(a for a in argv if a.startswith("-"))
            self.assertIn(REMOVED.format(flag), err)

    def test_unknown_flag_exits_1(self):
        code, _, err = self.run_cli("clip.mp4", "--nope")
        self.assertEqual(code, 1)
        self.assertIn("--nope", err)

    def test_help_exits_0(self):
        code, out, _ = self.run_cli("-h")
        self.assertEqual(code, 0)
        self.assertIn("-e", out)

    def test_no_such_file(self):
        with mock.patch.object(media, "require_tools"):
            code, _, err = self.run_cli("missing.mp4", "-e", "mlx")
        self.assertEqual(code, 1)
        self.assertIn("no such file: missing.mp4", err)

    def test_no_such_file_before_engine_choice(self):
        """A typo in the path is reported even when no engine is set up."""
        with mock.patch.object(media, "require_tools"), mock.patch("platform.system", return_value="Linux"), \
                mock.patch.dict(sys.modules, {"faster_whisper": None}):
            code, _, err = self.run_cli("missing.mp4")
        self.assertEqual(code, 1)
        self.assertIn("no such file: missing.mp4", err)
        self.assertNotIn("engine", err)

    def test_missing_ffmpeg_names_the_install_command(self):
        with mock.patch("shutil.which", return_value=None):
            code, _, err = self.run_cli("clip.mp4")
        self.assertEqual(code, 1)
        self.assertIn("ffmpeg", err)
        self.assertIn("winget install" if platform.system() == "Windows" else "install", err)


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg/ffprobe not on PATH")
class CliMediaTest(Base):
    @classmethod
    def setUpClass(cls):
        t = tempfile.TemporaryDirectory()
        cls.addClassCleanup(t.cleanup)
        cls.media = Path(t.name)
        make_video(cls.media / "silent.mp4", 10, audio=False)
        make_video(cls.media / "talk.mp4", 40)
        (cls.media / "junk.mp4").write_bytes(b"not a video")

    def copy(self, name, dest=None):
        dest = dest or self.tmp / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.media / name, dest)
        return dest

    # port of tests/silent-video.sh
    def test_silent_video_absolute_and_relative(self):
        video = self.copy("silent.mp4")
        code, out, err = self.run_cli(str(video), "-e", "mlx")
        self.assertEqual(code, 0, err)
        for ext in ("txt", "srt"):
            f = self.outdir / f"silent.{ext}"
            self.assertTrue(f.is_file())
            self.assertEqual(f.stat().st_size, 0)
        self.assertIn("vidscribe: no audio track; writing an empty transcript", err.splitlines())
        self.assertIn(f"video: {video}", err.splitlines())
        self.assertEqual(out, "")
        cwd = os.getcwd()
        os.chdir(self.tmp)
        try:
            code, _, err = self.run_cli("silent.mp4", "-e", "mlx")
        finally:
            os.chdir(cwd)
        self.assertEqual(code, 0, err)
        self.assertIn(f"video: {video}", err.splitlines())

    def test_silent_video_audio_only_fails(self):
        code, _, err = self.run_cli(str(self.copy("silent.mp4")), "-e", "mlx", "-a")
        self.assertEqual(code, 1)
        self.assertIn("vidscribe: no audio track to transcribe", err)

    def test_no_usable_stream(self):
        code, _, err = self.run_cli(str(self.copy("junk.mp4")), "-e", "mlx")
        self.assertEqual(code, 1)
        self.assertIn("vidscribe: no usable audio or video stream", err)

    def test_video_with_speech(self):
        self.fake_engine("whisper", srt_until(38))
        video = self.copy("talk.mp4")
        code, out, err = self.run_cli(str(video), "-e", "whisper", "-l", "ru", "-n", "2")
        self.assertEqual(code, 0, err)
        lines = err.splitlines()
        self.assertEqual(lines[0], "engine: whisper")
        self.assertIn(f"video: {video}", lines)
        self.assertEqual(lines[-1], f"transcript: {self.outdir / 'talk.txt'}")
        self.assertNotIn("WARNING", err)
        self.assertEqual(out, "привет мир\n")
        self.assertTrue((self.outdir / "talk.srt").is_file())
        self.assertEqual((self.outdir / "talk.txt").read_text(encoding="utf-8"), "привет мир\n")
        src, fmt, opts = self.calls[0]
        self.assertEqual((fmt, opts.lang, opts.speakers), ("srt", "ru", 2))

    def test_transcript_only_formats(self):
        self.fake_engine("whisper", "WEBVTT\n")
        code, out, err = self.run_cli(str(self.copy("talk.mp4")), "-e", "whisper", "-f", "vtt")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.calls[0][1], "vtt")
        self.assertNotIn("video:", err)
        self.assertFalse((self.outdir / "talk.txt").exists())
        self.assertEqual(err.splitlines()[-1], f"transcript: {self.outdir / 'talk.vtt'}")
        self.assertEqual(out, "")

    def test_ends_early_warning(self):
        self.fake_engine("whisper", srt_until(5))
        code, _, err = self.run_cli(str(self.copy("talk.mp4")), "-e", "whisper")
        self.assertEqual(code, 0, err)
        self.assertIn("WARNING: last cue 5s < duration 40s; transcript ends early", err.splitlines())

    def test_downloaded_video_moves_and_ends_early_warns(self):
        self.fake_engine("whisper", srt_until(5))
        root = self.tmp / "root"

        def download(url, dest, want_video):
            self.assertTrue(want_video)
            return self.copy("talk.mp4", dest / "abc123.mp4")  # yt-dlp writes into the run's temp folder

        with mock.patch.object(media, "download", side_effect=download), mock.patch.object(media, "ROOT", root):
            code, _, err = self.run_cli("https://x.com/i/status/1", "-e", "whisper")
        self.assertEqual(code, 0, err)
        lines = err.splitlines()
        kept = root / "videos" / "abc123.mp4"
        self.assertIn(f"video: {kept}", lines)
        self.assertTrue(kept.is_file())
        self.assertIn("WARNING: last cue 5s < duration 40s; transcript ends early", lines)
        self.assertEqual(lines[-1], f"transcript: {self.outdir / 'abc123.txt'}")

    def test_key_selects_scribe_and_is_never_printed(self):
        self.fake_engine("scribe", srt_until(38))
        os.environ["ELEVENLABS_API_KEY"] = KEY
        with mock.patch("platform.system", return_value="Windows"):
            code, out, err = self.run_cli(str(self.copy("talk.mp4")))
        self.assertEqual(code, 0, err)
        self.assertEqual(err.splitlines()[0], "engine: scribe (audio is uploaded to ElevenLabs)")
        self.assertNotIn(KEY, out + err)
        for f in self.outdir.iterdir():
            self.assertNotIn(KEY, f.read_text(encoding="utf-8"))

    def test_cyrillic_path_and_utf8_output(self):
        """A separate process with the OS default encodings: stdout and stderr must be UTF-8."""
        video = self.copy("talk.mp4", self.tmp / "тест видео" / "клип.mp4")
        script = (
            "import sys, types\n"
            "from pathlib import Path\n"
            "def transcribe(src, tmp, out_base, fmt, opts):\n"
            f"    Path(f'{{out_base}}.{{fmt}}').write_text({srt_until(38)!r}, encoding='utf-8')\n"
            "sys.modules['vidscribe.engines.whisper'] = types.SimpleNamespace(\n"
            "    available=lambda: True, transcribe=transcribe)\n"
            "from vidscribe.cli import main\n"
            "sys.exit(main(sys.argv[1:]))\n"
        )
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
        r = subprocess.run([sys.executable, "-c", script, str(video), "-e", "whisper"],
                           cwd=REPO, env=env, capture_output=True)
        err = r.stderr.decode("utf-8").replace("\r\n", "\n")
        self.assertEqual(r.returncode, 0, err)
        self.assertEqual(r.stdout.decode("utf-8").replace("\r\n", "\n"), "привет мир\n")
        self.assertIn(f"video: {video}\n", err)
        self.assertIn(f"transcript: {self.outdir / 'клип.txt'}\n", err)


if __name__ == "__main__":
    unittest.main()
