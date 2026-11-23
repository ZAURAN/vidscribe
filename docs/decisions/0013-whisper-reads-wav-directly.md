# ADR-0013: The whisper engine reads the wav itself, not through PyAV

## Status
Accepted. Revisit when faster-whisper supports PyAV 19.

## Date
2026-11-23

## Context
The whisper engine uses faster-whisper, which by default opens an audio file with PyAV. faster-whisper 1.2.1 does not work with PyAV 19, and a fresh install pulls PyAV 19. The engine already makes a 16 kHz mono PCM wav of its own, so it needs no general decoder.

## Decision
The engine reads that wav with the standard library `wave` module, converts it to an array with numpy, and gives the array to faster-whisper. PyAV is not used for decoding. When faster-whisper supports PyAV 19, this can go and the file path can be passed again.

## Alternatives considered
- **Pass the file path to faster-whisper as normal.** Fails with the PyAV 19 that gets installed, so the local engine would not run.
- **Pin PyAV below 19.** It would hold a dependency back to serve a decode step that is not needed here, since the audio is already in the one format faster-whisper wants. It also puts a pin on the environment that users have to carry.
- **Wait for a faster-whisper release.** Leaves the engine broken for Windows users who chose `-Local`, with no date for a fix.

## Consequences
- The engine works with the PyAV that is installed today.
- Only the wav that vidscribe makes is read this way. Reading other formats would need PyAV and is not supported.
- The wav is held in memory as one array; this is acceptable for the lengths the tool targets but grows with the length of the audio.
