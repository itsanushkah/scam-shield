"""Generate short demo call WAVs from samples/scripts/short_calls.json using Piper TTS (offline).

Prep tooling only (not part of the Scam Shield app). Uses the Piper voices in voices/
and the same phone-line filter and output format as make_calls.py.

Usage:
  python tools/make_piper_calls.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from piper import PiperVoice
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_calls import ROOT, SR_OUT, phone_line  # noqa: E402

GAP_S = 0.45


def main():
    calls = json.load(open(ROOT / "samples/scripts/short_calls.json"))["calls"]
    voices = {}

    for call in calls:
        chunks, meta, t, sr = [], [], 0.0, None
        for i, (spk, text) in enumerate(call["lines"]):
            name = call["voices"][spk]
            if name not in voices:
                voices[name] = PiperVoice.load(str(ROOT / "voices" / f"{name}.onnx"))
            voice = voices[name]
            sr = voice.config.sample_rate

            audio = np.concatenate([c.audio_float_array for c in voice.synthesize(text)])
            dur = len(audio) / sr
            meta.append({"i": i, "speaker": spk, "start": round(t, 2), "end": round(t + dur, 2), "text": text})
            chunks += [audio, np.zeros(int(GAP_S * sr), np.float32)]
            t += dur + GAP_S

        wav = phone_line(np.concatenate(chunks), sr)
        wavfile.write(ROOT / f"samples/{call['id']}.wav", SR_OUT, wav)

        info = {k: call[k] for k in ("id", "label", "title")}
        if "alert_line" in call:
            info["alert_line"] = call["alert_line"]
            info["alert_by_seconds"] = meta[call["alert_line"]]["end"]
        info["duration_s"] = round(len(wav) / SR_OUT, 1)
        info["lines"] = meta
        json.dump(info, open(ROOT / f"samples/{call['id']}.json", "w"), indent=2)
        print(f"{call['id']}: {info['duration_s']}s")


if __name__ == "__main__":
    main()
