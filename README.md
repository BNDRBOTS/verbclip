# VerbClip

Single-file desktop app. Records from a global hotkey, transcribes with OpenAI
`whisper-1`, copies raw text to the clipboard. A disfluency style-prompt biases
the decoder toward keeping your self-corrections instead of resolving them into
the phrase it assumes you meant.

## ⚠️ Model retirement

`whisper-1` is removed from the OpenAI API on **26 February 2027**. OpenAI
notified developers on 26 August 2026. After that date the transcription call
will fail. The replacement model strings named by OpenAI are `gpt-transcribe`
(recorded files) or `gpt-live-transcribe` (live audio), but neither preserves
disfluencies the way `whisper-1` does. See Troubleshooting.

## Requirements

- Python 3.10 or newer.
- An OpenAI API key with access to `whisper-1`.
- A working microphone.

## Files

`verbclip.py` — the application.
`requirements.txt` — dependencies.
`.env` — your key, as `OPENAI_API_KEY=sk-...`.

## Setup

### macOS

1. `pip install -r requirements.txt`
2. Put your key in `.env`.
3. In **System Settings → Privacy & Security**, grant **Accessibility** AND
   **Input Monitoring** to the terminal app you launch Python from.
   Without both, the hotkey is silently disabled — the app will print a warning
   and the Record button still works.
4. Grant **Microphone** permission when macOS prompts on first recording.
5. `python verbclip.py`

`customtkinter` applies a dark titlebar automatically on macOS only if you are
running Python 3.10+ with Tcl/Tk ≥ 8.6.9. If the titlebar stays light, that is
the cause; the window interior is unaffected.

### Windows (PC)

1. `pip install -r requirements.txt`
2. Put your key in `.env`.
3. `python verbclip.py`
4. If the hotkey does not fire, run the terminal as Administrator — `keyboard`
   uses low-level input hooks that can be blocked otherwise.
5. Microphone permission: Settings → Privacy → Microphone.

### Linux

1. `sudo apt install libportaudio2 xclip`
2. `pip install -r requirements.txt`
3. Put your key in `.env`.
4. `python verbclip.py`
5. `keyboard` needs read access to `/dev/input`. Run `sudo -E python verbclip.py`
   (the `-E` preserves the environment) or use the Record button.
6. On Wayland, global hotkeys are restricted by the compositor. Use the Record
   button; the clipboard fallback is `xclip` on X11.

## Usage

- **Ctrl+Alt+Space** — start / stop recording.
- **Record** — same, for when the hotkey is unavailable.
- **Copy** — copies the full text box.
- **Clear** — empties it.

On stop, transcription runs in a background thread with two retries. The last
utterance is copied to the clipboard automatically; if `pyperclip` raises
(Wayland), the text stays in the box and the status line says
“clipboard unavailable — select and copy”.

## Model behaviour

The call is:

| Parameter | Value |
|---|---|
| `model` | `whisper-1` |
| `prompt` | disfluency style sample |
| `response_format` | `text` |
| `temperature` | `0.0` |

The prompt is a **style sample, not an instruction**. Whisper mimics the register
of the text it is given; the sample contains `wait, no`, `uh`, `I mean`,
`let me start over`. `temperature=0.0` removes sampling randomness.

### Limitation

This is steering, not enforcement. `whisper-1` was trained largely on clean
subtitle text and its default instinct is to resolve self-corrections. A very
rapid, fluent repair can still be collapsed. This is the maximum verbatim
fidelity available through this endpoint. Strict preservation of every
disfluency requires a self-hosted verbatim-tuned variant (e.g. CrisperWhisper),
not the OpenAI API.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `OPENAI_API_KEY missing` | `.env` not beside `verbclip.py`, or malformed | Must be exactly `OPENAI_API_KEY=sk-...`, no quotes, no spaces around `=` |
| Hotkey does nothing (macOS) | Accessibility or Input Monitoring not granted | Grant both to the Python/terminal app; restart the terminal |
| Hotkey does nothing (Windows) | Low-level hook blocked | Run terminal as Administrator |
| Hotkey does nothing (Linux) | No `/dev/input` access, or Wayland | `sudo -E python verbclip.py`, or use Record on Wayland |
| Recording silent | OS microphone permission | Check Privacy → Microphone; confirm default input device |
| `No audio captured` | Stopped before any block arrived | Hold recording for at least one second |
| Transcription fails after **26 Feb 2027** | `whisper-1` removed from the API | Change `model` in `_transcribe()` to `gpt-transcribe`; note the prompt field becomes `keywords`, and verbatim behaviour is not preserved |
| Clipboard does not update on Linux | `xclip` missing or Wayland blocks background clipboard writes | Install `xclip`; on Wayland select the text manually — the status line will say so |
| Titlebar light on macOS | Python < 3.10 or Tcl/Tk < 8.6.9 | Upgrade Python; window interior is unaffected |

## Design

Near-black `#0E0E10`, warm off-white `#E9E7E2`, one muted red `#A8403C` only
while recording. One border weight, two fonts. No gradients, no accent palette.
```

---

## Run

```
pip install -r requirements.txt
python verbclip.py
```
