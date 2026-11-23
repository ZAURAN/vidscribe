# vidscribe installer for Windows (PowerShell 5.1 or 7). Safe to run again: it updates in place.
#   .\install.ps1          ElevenLabs Scribe (cloud) engine
#   .\install.ps1 -Local   also the local faster-whisper engine (NVIDIA GPU or CPU)
param([switch]$Local)
$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot

function Test-Tool($name) { [bool](Get-Command $name -ErrorAction SilentlyContinue) }
function Update-SessionPath {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machine;$user"
}
function Install-WithWinget($id) {
    if (-not (Test-Tool winget)) { throw "winget not found. Install '$id' by hand, then run this script again." }
    winget install --id $id -e --accept-package-agreements --accept-source-agreements
    Update-SessionPath
}

if (-not ((Test-Tool ffmpeg) -and (Test-Tool ffprobe))) { Install-WithWinget 'Gyan.FFmpeg' }
if (-not (Test-Tool uv)) { Install-WithWinget 'astral-sh.uv' }
if (-not ((Test-Tool ffmpeg) -and (Test-Tool ffprobe) -and (Test-Tool uv))) {
    throw 'ffmpeg, ffprobe or uv is still not on PATH. Open a new terminal and run this script again.'
}

$target = if ($Local) { "$repo[local,cuda]" } else { $repo }
uv tool install --force --python 3.12 $target
if ($LASTEXITCODE -ne 0) { throw 'uv tool install failed' }
uv tool update-shell
if ($LASTEXITCODE -ne 0) { Write-Host "Could not update PATH; add $(uv tool dir --bin) to your PATH by hand." }

# Replace the skill folder contents with the files from skill/ (no leftovers from older versions).
$dest = Join-Path $HOME '.claude\skills\vidscribe'
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Get-ChildItem -LiteralPath $dest -Force | Remove-Item -Recurse -Force
Copy-Item -Path (Join-Path $repo 'skill\*') -Destination $dest -Recurse -Force

Write-Host ''
Write-Host 'installed: vidscribe (open a new terminal if the command is not found yet)'
Write-Host "agent skill: $dest"
Write-Host ''
Write-Host 'Cloud engine (ElevenLabs Scribe): create an API key in your ElevenLabs account, then set it yourself:'
Write-Host '  setx ELEVENLABS_API_KEY "<your key>"   (then open a new terminal)'
Write-Host 'This script never asks for the key. Audio sent to Scribe leaves your PC.'
if (-not $Local) { Write-Host 'No key? Run .\install.ps1 -Local for the local engine.' }
