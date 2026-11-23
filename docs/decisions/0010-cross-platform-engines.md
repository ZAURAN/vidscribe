# ADR-0010: One program, three engines, Mac and Windows

## Status
Accepted. Softens [ADR-0001](0001-local-only.md): the cloud is allowed, only by explicit choice.

## Date
2026-11-23

## Context
vidscribe was a bash script around MLX, so it worked only on Apple Silicon Macs. A Windows user (RTX 4070) wanted the same system, with ElevenLabs Scribe for the speech. ADR-0001 rejected a hosted model because it is paid and sends media off the device. That reasoning still holds for the default on a Mac, but it should not stop a user who chooses the cloud.

## Decision
- vidscribe is a Python package (standard library only, plus yt-dlp), installed with `uv tool install` on both systems. `install.sh` (macOS) and `install.ps1` (Windows) also copy the skill.
- Three engines. `mlx`: the original, on-device, Apple Silicon. `scribe`: ElevenLabs cloud, any OS. `whisper`: faster-whisper, on-device, NVIDIA GPU or CPU, any OS, installed by choice (`-Local`).
- Choice: `-e` or `VIDSCRIBE_ENGINE`, else mlx on Apple Silicon, else scribe when `ELEVENLABS_API_KEY` is set, else whisper when installed, else an error that lists the options. On a Mac the default stays local.
- The cloud is never used silently: it needs the flag or the key, every run prints `engine: <name>`, scribe adds `(audio is uploaded to ElevenLabs)`, and the skill tells agents to ask the user before closed videos. Scribe requests are not retried, since each is paid.
- The key is set by the user and is never requested, printed or written by vidscribe or its installers.

## Alternatives considered
- **Keep the Mac-only script and add a separate Windows port.** Two code bases that drift apart, and two skills.
- **Local engine only.** Does not give the user the Scribe quality and speaker labels they asked for.
- **Cloud as the default everywhere.** Would break the "no keys, no cloud" promise for existing Mac users.

## Consequences
- Mac behaviour is unchanged: same default engine, flags and warnings.
- The benchmark figures in the README were measured on MLX. There are no measurements for Scribe or whisper.
- Linux and Intel Macs are not supported targets; scribe and whisper may work there but are not tested.
- The MLX engine could not be tested on this Windows machine; it is checked by tests of the command it builds.
