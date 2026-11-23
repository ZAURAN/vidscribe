<!-- autopilot:glossary -->
# vidscribe

vidscribe lets an agent "watch" a video or listen to audio: speech becomes text with timestamps, and the video itself is kept so the agent can look at frames on its own.

## Language

**Engine**:
The speech recognizer that turns audio into text. There are three: one on-device for Apple Silicon Macs, one in the cloud, and one on-device for NVIDIA GPUs or CPUs.
_Avoid_: backend, model, provider

**Model**:
The particular recognition model an engine runs. It is a setting of an engine, not a synonym for it.
_Avoid_: engine

**Transcript**:
The text of what was said, with timestamps, saved as files for the agent to read. For a video it exists in two forms side by side: timed subtitles and plain text.
_Avoid_: captions, output

**Cue**:
One timed line of a transcript: a start, an end and the words spoken between them.
_Avoid_: segment, subtitle, line

**Piece**:
A stretch of audio of roughly 30 seconds that the on-device Mac engine recognizes on its own. Language detection and the repetition guard work piece by piece.
_Avoid_: chunk, segment

**Kept video**:
The video file that remains after a run, so the agent can pull frames from it. It is not a picture summary; vidscribe no longer produces frames or contact sheets.
_Avoid_: frames, screenshots

**Ends early**:
A transcript whose last cue stops well before the end of the media, a sign that recognition dropped the rest.
_Avoid_: truncated, incomplete

**Cut off**:
A stretch where the engine looped on a repeated phrase and the text there cannot be trusted.
_Avoid_: hallucination, glitch
