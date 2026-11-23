# Decisions

Why the shipped defaults are what they are. An ADR is written when a default changes; ideas checked and dropped without changing one are recorded in [`docs/measurements.md`](../measurements.md).

| ADR | Decision |
|---|---|
| [0001](0001-local-only.md) | Stay local; no hosted video model |
| [0002](0002-frames-on-by-default.md) | Frames on by default for video (superseded by 0009) |
| [0003](0003-frame-cap.md) | Cap automatic frames at 40, split between refs and scenes (superseded by 0007) |
| [0004](0004-frames-on-demand.md) | Frames on demand (`--at`) instead of smarter scene choice (superseded by 0009) |
| [0005](0005-no-ocr.md) | No OCR timeline; contact sheets for unnamed moments (sheets removed by 0009) |
| [0006](0006-detect-language-per-piece.md) | Detect the language of every piece by default |
| [0007](0007-overview-sheets.md) | Overview sheets instead of default frames; `-v N` and `--at A-B/N` give full-size frames (tile count amended by 0008) (superseded by 0009) |
| [0008](0008-full-sheets.md) | Every overview sheet is full: 16 tiles per sheet, one sheet per 160 s of picture (1 to 6) (superseded by 0009) |
| [0009](0009-drop-picture-commands.md) | Drop sheets, `-v`, `--at` and `--scan`; print the video path for `ffmpeg` |
| [0010](0010-cross-platform-engines.md) | One Python program for Mac and Windows with three engines (mlx, scribe, whisper); the cloud only by explicit choice (softens 0001) |
| [0011](0011-python-package-uv-tool.md) | A Python package installed with `uv tool`; yt-dlp is a dependency of the package, not a system tool |
| [0012](0012-scribe-no-redirects.md) | Scribe requests follow no redirects, and the key is checked before anything is sent |
| [0013](0013-whisper-reads-wav-directly.md) | The whisper engine reads the wav with `wave`, bypassing PyAV, until faster-whisper supports PyAV 19 |

## Considered, not built

- **A hosted video model** (e.g. Gemini behind a flag): paid, and it sends media off the device ([ADR-0001](0001-local-only.md)).
- **OCR of on-screen text into `index.txt`**: with `--at`, agents answered 31/36 questions about moments the speech never names, above the bar set beforehand ([ADR-0005](0005-no-ocr.md)).
- **Smarter scene choice within the 40-frame cap**: two methods were tried on long videos and neither improved answers; fetching frames on demand did ([ADR-0004](0004-frames-on-demand.md)). The cap and its scene frames are gone since [ADR-0007](0007-overview-sheets.md).
- **Word timestamps (forced aligner)**: at most 1 of 72 misses came from frame timing, and the aligner covers only 11 languages ([measurements](../measurements.md#word-timestamps-forced-aligner-not-built)).
- **A readable-transcript mode (S1-mini cleanup)**: agents read the raw text fine, and a rewrite could change quoted words; English only ([measurements](../measurements.md#readable-transcript-s1-mini-not-built)).
