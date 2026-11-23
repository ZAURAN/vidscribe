# ADR-0011: A Python package installed with `uv tool`, yt-dlp as its dependency

## Status
Accepted. Spells out the packaging choice that [ADR-0010](0010-cross-platform-engines.md) states in one line.

## Date
2026-11-23

## Context
The original was a ~200-line bash script, and its installer ran `brew install uv ffmpeg yt-dlp` and symlinked the script. Neither half works on Windows. Moving the tool to Windows meant choosing what it is written in, how it is installed, and where yt-dlp comes from. These are expensive to undo: the language fixes the code base, and the install route is what the skill, both installers and the docs describe.

## Decision
- The tool is a Python package whose core uses only the standard library. Optional engines import their libraries lazily.
- It is installed with `uv tool install` on both systems, pinned to Python 3.12. uv brings its own Python, so a Mac needs no system `python3` and a Windows machine does not depend on the Store stub.
- yt-dlp is a dependency of the package and runs from the same environment, not from `PATH`.
- ffmpeg and ffprobe stay outside the package and are taken from `PATH` (brew on Mac, winget on Windows); a missing one gives an error with the command for the user's system.
- The pin is 3.12 because ready-made wheels for ctranslate2 and the NVIDIA libraries exist for it.

## Alternatives considered
- **Keep the bash script and write a PowerShell twin for Windows.** Every change, including the mlx patch, flag parsing and the ends-early check, would have to be made twice and would drift. The spec also asks for the same tests on both systems, which two scripts cannot share.
- **Run the bash script under WSL or Git Bash on Windows.** Path handling, UTF-8 and the user's Cyrillic folders would depend on a layer the user has to install first, and the tool would still not be a normal Windows command.
- **Install with `pip` into whatever Python is present.** The installed Python differs between machines (a Mac may have none, Windows may have the Store stub), and a global install can clash with other packages. `uv tool` gives each machine an isolated environment with a known Python.
- **Take yt-dlp from `PATH` (brew, winget), as the original did.** The version then differs between the two systems and between machines, and it does not update with vidscribe. Downloads break when sites change, so a version that drifts per machine is a recurring failure.
- **Bundle ffmpeg in the package too.** Rejected: it is a large native binary, and both systems already have a standard way to install it.

## Consequences
- One code base, one test command, one installed command name on both systems.
- The user needs uv, which both installers add.
- yt-dlp is updated by reinstalling vidscribe, not by the system package manager.
- Python 3.12 is a fixed install-time choice; moving to a newer Python means checking that those wheels exist for it first.
