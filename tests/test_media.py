import contextlib
import importlib
import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from vidscribe import media


class RootTest(unittest.TestCase):
    def tearDown(self):
        importlib.reload(media)  # back to this OS's ROOT

    def test_root_per_os(self):
        with mock.patch("platform.system", return_value="Windows"):
            importlib.reload(media)
        self.assertEqual(media.ROOT, Path(tempfile.gettempdir()) / "vidscribe")
        for system in ("Darwin", "Linux"):
            with mock.patch("platform.system", return_value=system):
                importlib.reload(media)
            self.assertEqual(media.ROOT, Path("/tmp/vidscribe"))

    def test_default_outdir(self):
        with mock.patch.dict(os.environ, {"VIDSCRIBE_OUTDIR": ""}):
            self.assertEqual(media.default_outdir(), media.ROOT / "transcripts")
        with mock.patch.dict(os.environ, {"VIDSCRIBE_OUTDIR": "elsewhere"}):
            self.assertEqual(media.default_outdir(), Path("elsewhere"))


class PruneTest(unittest.TestCase):
    def test_prune_removes_only_entries_older_than_3_days(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            old = time.time() - 4 * 86400
            fresh = time.time() - 2 * 86400

            def make(rel, mtime, is_dir=False):
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                if is_dir:
                    p.mkdir()
                    (p / "inside.txt").write_text("x")
                else:
                    p.write_text("x")
                os.utime(p, (mtime, mtime))
                return p

            gone = [make("transcripts/old.txt", old), make("videos/old.mp4", old),
                    make("frames/olddir", old, is_dir=True)]
            kept = [make("transcripts/new.txt", fresh), make("videos/new.mp4", fresh),
                    make("other/old.txt", old)]
            with mock.patch.object(media, "ROOT", root):
                media.prune()
            for p in gone:
                self.assertFalse(p.exists(), p)
            for p in kept:
                self.assertTrue(p.exists(), p)

    def test_prune_without_folders_is_quiet(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.object(media, "ROOT", Path(t) / "none"):
            media.prune()


class RequireToolsTest(unittest.TestCase):
    def missing(self, system):
        err = io.StringIO()
        with mock.patch("shutil.which", return_value=None), \
                mock.patch("platform.system", return_value=system), \
                contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            media.require_tools()
        self.assertEqual(cm.exception.code, 1)
        return err.getvalue()

    def test_install_hint_per_os(self):
        self.assertIn("winget install", self.missing("Windows"))
        self.assertIn("brew install ffmpeg", self.missing("Darwin"))

    def test_tools_present(self):
        with mock.patch("shutil.which", return_value="/bin/x"):
            media.require_tools()


if __name__ == "__main__":
    unittest.main()
