#!/usr/bin/env python3
"""VerbClip — whisper-1 voice to clipboard."""

import os
import sys
import time
import wave
import tempfile
import threading
from pathlib import Path

import numpy as np
import sounddevice as sd
import pyperclip
import customtkinter as ctk
from dotenv import load_dotenv
from openai import OpenAI

try:
    import keyboard
    KEYBOARD_OK = True
except Exception as _ke:
    KEYBOARD_OK = False
    _KEYBOARD_ERR = str(_ke)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
HOTKEY = "ctrl+alt+space"

# Style sample, not an instruction. Disfluent speech in → disfluent speech out.
VERBATIM_PROMPT = (
    "Okay so I think we should go to the store, wait, no, the market, "
    "yeah the market on Tuesday. Uh, I mean Wednesday. Let me start over. "
    "I was saying, uh, the market on Wednesday. Um, and then, like, "
    "we can, you know, figure it out from there."
)

BG       = "#0E0E10"
SURFACE  = "#16161A"
BORDER   = "#26262B"
TEXT     = "#E9E7E2"
MUTED    = "#7C7C82"
REC      = "#A8403C"

UI_FONT  = "Segoe UI"
MONO     = "Consolas"


def preflight() -> list[str]:
    """Return a list of fatal problems; empty list means ready."""
    problems: list[str] = []
    if not API_KEY:
        problems.append("OPENAI_API_KEY missing. Put it in .env next to verbclip.py.")
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE):
            pass
    except Exception as e:
        problems.append(f"Microphone unavailable: {e}")
    if sys.platform == "darwin" and not KEYBOARD_OK:
        problems.append(
            "macOS hotkey unavailable: grant Accessibility AND Input Monitoring "
            "to your Python/terminal in System Settings → Privacy & Security. "
            "The Record button still works."
        )
    return problems


class App(ctk.CTk):
    def __init__(self, client: OpenAI):
        super().__init__()
        self.title("VerbClip")
        self.geometry("600x460")
        self.minsize(500, 380)
        self.configure(fg_color=BG)

        self.client = client
        self.recording = False
        self.frames: list[np.ndarray] = []
        self.stream = None

        self._build()
        self._bind_hotkey()

    # -- layout -------------------------------------------------------------
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 0))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="VERBCLIP",
            font=ctk.CTkFont(family=UI_FONT, size=11, weight="bold"),
            text_color=MUTED,
        ).grid(row=0, column=0, sticky="w")

        self.status = ctk.CTkLabel(
            header, text="●  idle",
            font=ctk.CTkFont(family=UI_FONT, size=11),
            text_color=MUTED, anchor="e",
        )
        self.status.grid(row=0, column=1, sticky="e")

        self.text = ctk.CTkTextbox(
            self,
            fg_color=SURFACE, border_color=BORDER, border_width=1,
            corner_radius=12, text_color=TEXT,
            font=ctk.CTkFont(family=MONO, size=13),
            wrap="word", activate_scrollbars=True,
        )
        self.text.grid(row=1, column=0, sticky="nsew", padx=22, pady=(16, 14))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 20))
        footer.grid_columnconfigure(0, weight=1)

        self.rec_btn = ctk.CTkButton(
            footer, text="Record", command=self.toggle,
            height=44, corner_radius=10,
            fg_color=TEXT, hover_color="#FFFFFF", text_color=BG,
            font=ctk.CTkFont(family=UI_FONT, size=13, weight="bold"),
        )
        self.rec_btn.grid(row=0, column=0, sticky="w")

        self.copy_btn = ctk.CTkButton(
            footer, text="Copy", command=self.copy,
            height=44, width=90, corner_radius=10,
            fg_color="transparent", hover_color=SURFACE,
            border_width=1, border_color=BORDER, text_color=MUTED,
            font=ctk.CTkFont(family=UI_FONT, size=13),
        )
        self.copy_btn.grid(row=0, column=1, padx=(10, 0))

        self.clear_btn = ctk.CTkButton(
            footer, text="Clear", command=self.clear,
            height=44, width=90, corner_radius=10,
            fg_color="transparent", hover_color=SURFACE,
            border_width=1, border_color=BORDER, text_color=MUTED,
            font=ctk.CTkFont(family=UI_FONT, size=13),
        )
        self.clear_btn.grid(row=0, column=2, padx=(10, 0))

    # -- hotkey -------------------------------------------------------------
    def _bind_hotkey(self):
        if not KEYBOARD_OK:
            msg = f"Hotkey off ({_KEYBOARD_ERR}). Use Record."
            self.status.configure(text=f"●  {msg}", text_color=REC)
            print(msg, file=sys.stderr)
            return
        try:
            keyboard.add_hotkey(HOTKEY, lambda: self.after(0, self.toggle))
        except Exception as e:
            self.status.configure(text="●  hotkey failed — use Record", text_color=REC)
            print(f"Hotkey bind failed: {e}", file=sys.stderr)

    # -- recording ----------------------------------------------------------
    def _audio_cb(self, indata, frames, time_info, status):
        if status:
            print(f"[audio] {status}", file=sys.stderr)
        if self.recording:
            self.frames.append(indata.copy())

    def toggle(self):
        if self.recording:
            self.stop()
        else:
            self.start()

    def start(self):
        if self.recording:
            return
        self.frames = []
        self.recording = True
        try:
            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE, channels=CHANNELS,
                dtype=DTYPE, callback=self._audio_cb, blocksize=1024,
            )
            self.stream.start()
        except Exception as e:
            self.recording = False
            self.status.configure(text=f"●  mic error: {e}", text_color=REC)
            return
        self.rec_btn.configure(text="Stop", fg_color=REC, hover_color="#8F3632",
                               text_color="#FFFFFF")
        self.status.configure(text="●  recording", text_color=REC)

    def stop(self):
        if not self.recording:
            return
        self.recording = False
        try:
            self.stream.stop()
            self.stream.close()
        except Exception:
            pass
        self.stream = None

        self.rec_btn.configure(text="Record", fg_color=TEXT, hover_color="#FFFFFF",
                               text_color=BG)
        self.status.configure(text="●  transcribing", text_color=MUTED)

        if not self.frames:
            self.status.configure(text="●  idle")
            return

        audio = np.concatenate(self.frames, axis=0)
        threading.Thread(target=self._transcribe, args=(audio,), daemon=True).start()

    # -- transcription ------------------------------------------------------
    def _transcribe(self, audio: np.ndarray):
        tmp = Path(tempfile.mkstemp(suffix=".wav")[1])
        try:
            with wave.open(str(tmp), "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio.tobytes())

            last_err = None
            for attempt in range(3):
                try:
                    with open(tmp, "rb") as f:
                        result = self.client.audio.transcriptions.create(
                            model="whisper-1",
                            file=f,
                            prompt=VERBATIM_PROMPT,
                            response_format="text",
                            temperature=0.0,
                        )
                    text = result.strip() if isinstance(result, str) else result.text.strip()
                    self.after(0, self._deliver, text)
                    return
                except Exception as e:
                    last_err = e
                    time.sleep(0.6 * (attempt + 1))
            self.after(0, self._fail, str(last_err))
        finally:
            tmp.unlink(missing_ok=True)

    def _deliver(self, text: str):
        self.text.insert("end", text + "\n")
        self.text.see("end")
        try:
            pyperclip.copy(text)
            self.status.configure(text="●  copied", text_color=MUTED)
        except Exception:
            self.status.configure(
                text="●  clipboard unavailable — select and copy", text_color=REC)
        self.after(1600, lambda: self.status.configure(text="●  idle"))

    def _fail(self, msg: str):
        self.status.configure(text="●  transcription failed", text_color=REC)
        print(f"Transcription failed: {msg}", file=sys.stderr)

    # -- buttons ------------------------------------------------------------
    def copy(self):
        text = self.text.get("1.0", "end").strip()
        if not text:
            return
        try:
            pyperclip.copy(text)
            self.status.configure(text="●  copied", text_color=MUTED)
        except Exception:
            self.status.configure(
                text="●  clipboard unavailable — select and copy", text_color=REC)
        self.after(1600, lambda: self.status.configure(text="●  idle"))

    def clear(self):
        self.text.delete("1.0", "end")


def main():
    ctk.set_appearance_mode("dark")

    problems = preflight()
    if problems:
        for p in problems:
            print(f"[preflight] {p}", file=sys.stderr)
        if not API_KEY:
            sys.exit(1)

    client = OpenAI(api_key=API_KEY) if API_KEY else None
    if client is None:
        sys.exit(1)

    app = App(client)
    if problems:
        app.status.configure(text="●  preflight issues — see terminal", text_color=REC)
    app.mainloop()


if __name__ == "__main__":
    main()
