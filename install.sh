#!/usr/bin/env bash
set -euo pipefail
[[ "$(uname -sm)" == "Darwin arm64" ]] || { echo "vidscribe needs an Apple Silicon Mac (MLX); on Windows run install.ps1" >&2; exit 1; }
command -v brew >/dev/null || { echo "install Homebrew first: https://brew.sh" >&2; exit 1; }
here="$(cd "$(dirname "$0")" && pwd)"
brew install uv ffmpeg
uv tool install --force mlx-audio --prerelease=allow
# an older install symlinked a bash script here; it would shadow the uv command
[[ -L "$HOME/.local/bin/vidscribe" ]] && rm "$HOME/.local/bin/vidscribe"
uv tool install --force --python 3.12 "$here"
uv tool update-shell || true
# replace the skill folder contents with the files from skill/
dest="$HOME/.claude/skills/vidscribe"
mkdir -p "$dest"
find "$dest" -mindepth 1 -delete
cp -R "$here"/skill/. "$dest"/
echo "installed: vidscribe (open a new terminal if the command is not found yet)"
echo "agent skill: $dest"
echo "cloud engine (optional): set ELEVENLABS_API_KEY yourself, e.g. add 'export ELEVENLABS_API_KEY=<your key>' to ~/.zshrc"
