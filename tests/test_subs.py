import tempfile
import unittest
from pathlib import Path

from vidscribe.subs import Cue, fmt_ts, read_srt, srt_to_txt, write

CUES = [Cue(0.0, 1.5, "Привет"), Cue(3661.25, 3662.0, "second line")]
SRT = "1\n00:00:00,000 --> 00:00:01,500\nПривет\n\n2\n01:01:01,250 --> 01:01:02,000\nsecond line\n"
VTT = "WEBVTT\n\n00:00:00.000 --> 00:00:01.500\nПривет\n\n01:01:01.250 --> 01:01:02.000\nsecond line\n"


class SubsTest(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.dir = Path(t.name)

    def read(self, p):
        return p.read_bytes().decode("utf-8")

    def test_fmt_ts(self):
        self.assertEqual(fmt_ts(3661.25), "01:01:01,250")
        self.assertEqual(fmt_ts(59.9996, "."), "00:01:00.000")

    def test_write_formats(self):
        base = self.dir / "a.b"  # dots in the name stay in the name
        self.assertEqual(write(CUES, base, "srt"), self.dir / "a.b.srt")
        self.assertEqual(self.read(self.dir / "a.b.srt"), SRT)
        self.assertEqual(self.read(write(CUES, base, "vtt")), VTT)
        self.assertEqual(self.read(write(CUES, base, "txt")), "Привет\nsecond line\n")

    def test_read_srt_and_srt_to_txt(self):
        srt = self.dir / "x.srt"
        srt.write_bytes(("1\r\n00:00:00,000 --> 00:00:01,500\r\nПривет\r\nмир\r\n\r\n"
                         "2\r\n01:01:01,250 --> 01:01:02,000\r\n\r\n").encode("utf-8"))
        self.assertEqual(read_srt(srt), [Cue(0.0, 1.5, "Привет мир"), Cue(3661.25, 3662.0, "")])
        srt_to_txt(srt, self.dir / "x.txt")
        self.assertEqual(self.read(self.dir / "x.txt"), "Привет мир\n\n")

    def test_empty_srt(self):
        srt = self.dir / "e.srt"
        srt.write_text("")
        self.assertEqual(read_srt(srt), [])
        srt_to_txt(srt, self.dir / "e.txt")
        self.assertEqual(self.read(self.dir / "e.txt"), "")


if __name__ == "__main__":
    unittest.main()
