import hashlib
import os
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from vidscribe.engines import Options, mlx

REPO = Path(__file__).resolve().parent.parent
PATCH = REPO / "vidscribe" / "engines" / "mlx_patch.py"
# sha256 of the heredoc body in bin/vidscribe at 0eb1386 (LF line endings)
PATCH_SHA256 = "6a936dcc3e96023b0a41fe6812135670cfe7fc181179e2290bb880c2c86ca3c8"
GIB = 1024 ** 3


def original_heredoc():
    """The body between <<'PY' and PY in the original script, or None without git."""
    try:
        r = subprocess.run(["git", "show", "0eb1386:bin/vidscribe"], cwd=REPO,
                           capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode:
        return None
    lines = r.stdout.replace(b"\r\n", b"\n").split(b"\n")
    i = next(n for n, line in enumerate(lines) if line.endswith(b"<<'PY'")) + 1
    return b"\n".join(lines[i:lines.index(b"PY", i)]) + b"\n"


class PatchTest(unittest.TestCase):
    def test_patch_is_the_original_heredoc_byte_for_byte(self):
        body = PATCH.read_bytes().replace(b"\r\n", b"\n")
        original = original_heredoc()
        if original is not None:
            self.assertEqual(body, original)
        self.assertEqual(hashlib.sha256(body).hexdigest(), PATCH_SHA256)


class CommandTest(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("VIDSCRIBE_MODEL", None)

    def test_command_matches_the_original(self):
        cmd = mlx.command("/py", Path("w.wav"), Path("out/clip"), "srt", 100.7, Options(), 16 * GIB)
        self.assertEqual(cmd, [
            "/py", "-", "--model", "mlx-community/Qwen3-ASR-1.7B-8bit", "--audio", "w.wav",
            "--output-path", str(Path("out/clip")), "--format", "srt",
            "--max-tokens", "11414",  # int(8192 + 32 * 100.7)
            "--max-parallel-segments", "32",
        ])

    def test_small_ram_uses_8_parallel_segments(self):
        cmd = mlx.command("/py", Path("w.wav"), Path("o"), "txt", 0, Options(), 16 * GIB - 1)
        self.assertEqual(cmd[cmd.index("--max-parallel-segments") + 1], "8")
        self.assertEqual(cmd[cmd.index("--max-tokens") + 1], "8192")

    def test_language_context_and_model(self):
        opts = Options(lang="ru", context="Anthropic, Claude", model="my/model")
        cmd = mlx.command("/py", Path("w.wav"), Path("o"), "vtt", 10, opts, 8 * GIB)
        self.assertEqual(cmd[cmd.index("--model") + 1], "my/model")
        self.assertEqual(cmd[-4:], ["--language", "ru", "--context", "Anthropic, Claude"])

    def test_vidscribe_model_env(self):
        os.environ["VIDSCRIBE_MODEL"] = "env/model"
        cmd = mlx.command("/py", Path("w.wav"), Path("o"), "txt", 1, Options(), GIB)
        self.assertEqual(cmd[cmd.index("--model") + 1], "env/model")
        self.assertNotIn("--language", cmd)
        self.assertNotIn("--context", cmd)


if __name__ == "__main__":
    unittest.main()
