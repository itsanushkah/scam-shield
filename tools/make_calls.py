"""Generate two-voice demo call WAVs from samples/scripts/calls.json using Kokoro TTS (offline, ONNX).

Prep tooling only (not part of the Scam Shield app). Runs fully offline once the model files exist.

Usage:
  python tools/make_calls.py --model kokoro-v1.0.onnx --voices voices-v1.0.bin \
      --vocab kokoro_config.json --lexicon us_gold.json us_silver.json

Outputs per call into samples/:
  <id>.wav        16 kHz mono PCM16, phone-line filtered (what the app streams in demo mode)
  <id>.json       per-line timestamps + text (ground truth for checking the transcript and alert timing)
"""
import argparse, json, re, sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
from scipy.signal import butter, resample_poly, sosfilt
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parent.parent
SR_TTS = 24000
SR_OUT = 16000
EXTRA = {"ethan": "ˈiθən", "chen": "ʧˈɛn", "margaret": "mˈɑɹɡɹət"}
TOKEN_RE =re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)*|[.,!?;:]")


class G2P:
    def __init__(self, lexicon_paths):
        self.lex = {}
        for p in reversed(lexicon_paths):  # earlier files win
            self.lex.update(json.load(open(p)))
        self.oov = set()

    def _lookup(self, w):
        for cand in (w, w.lower(), w.capitalize()):
            v = self.lex.get(cand)
            if isinstance(v, dict):
                v = v.get("DEFAULT")
            if v:
                return v
        lw = w.lower()
        if lw in EXTRA:
            return EXTRA[lw]
        if lw.endswith("'s"):
            base = self._lookup(w[:-2])
            if base:
                return base + "z"
        if lw.endswith("ed") and len(lw) > 4:
            for base_w in (lw[:-2], lw[:-1]):
                base = self._lookup(base_w)
                if base:
                    last = base.rstrip("ˈˌ")[-1]
                    return base + ("ᵻd" if last in "td" else "t" if last in "pkfsʃʧθ" else "d")
        if lw.endswith("s") and len(lw) > 3:
            base = self._lookup(lw[:-1])
            if base:
                last = base[-1]
                return base + ("ᵻz" if last in "szʃʒʧʤ" else "s" if last in "ptkfθ" else "z")
        return None

    def __call__(self, text):
        out = []
        for tok in TOKEN_RE.findall(text):
            if tok in ".,!?;:":
                if out:
                    out[-1] += tok
                continue
            ph = self._lookup(tok)
            if ph is None:
                self.oov.add(tok)
                continue
            out.append(ph)
        return " ".join(out)


class Kokoro:
    def __init__(self, model, voices, vocab):
        self.sess = ort.InferenceSession(model, providers=["CPUExecutionProvider"])
        self.inputs = {i.name: i for i in self.sess.get_inputs()}
        self.tok_name = "input_ids" if "input_ids" in self.inputs else "tokens"
        self.voices = np.load(voices)
        self.vocab = json.load(open(vocab))["vocab"]

    def speak(self, phonemes, voice, speed=1.0):
        ids = [self.vocab[c] for c in phonemes if c in self.vocab][:510]
        style = self.voices[voice][len(ids)]
        speed_dtype = np.int32 if "int" in self.inputs["speed"].type else np.float32
        feeds = {
            self.tok_name: np.array([[0, *ids, 0]], dtype=np.int64),
            "style": style.astype(np.float32),
            "speed": np.array([speed], dtype=speed_dtype),
        }
        return np.asarray(self.sess.run(None, feeds)[0]).ravel().astype(np.float32)


def phone_line(x, sr):
    """Telephone-band filter (300-3400 Hz), light noise, then 16 kHz mono PCM16."""
    x = resample_poly(x, 8000, sr)  # down to 8k (narrowband call); scipy reduces the ratio
    sos = butter(4, [300, 3400], btype="band", fs=8000, output="sos")
    x = sosfilt(sos, x)
    x = resample_poly(x, 2, 1)  # 8k -> 16k for the STT
    rng = np.random.default_rng(7)
    x = x + rng.normal(0, 0.003, len(x))
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.85
    return (x * 32767).astype(np.int16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--voices", required=True)
    ap.add_argument("--vocab", required=True)
    ap.add_argument("--lexicon", nargs="+", required=True)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()

    g2p, tts = G2P(a.lexicon), Kokoro(a.model, a.voices, a.vocab)
    calls = json.load(open(ROOT / "samples/scripts/calls.json"))["calls"]
    for call in calls:
        if a.only and call["id"] not in a.only:
            continue
        chunks, meta, t = [], [], 0.0
        gap = np.zeros(int(0.45 * SR_TTS), np.float32)
        for i, (spk, text) in enumerate(call["lines"]):
            audio = tts.speak(g2p(text), call["voices"][spk], speed=1.0 if spk == "caller" else 0.95)
            dur = len(audio) / SR_TTS
            meta.append({"i": i, "speaker": spk, "start": round(t, 2), "end": round(t + dur, 2), "text": text})
            chunks += [audio, gap]
            t += dur + len(gap) / SR_TTS
        wav = phone_line(np.concatenate(chunks), SR_TTS)
        wavfile.write(ROOT / f"samples/{call['id']}.wav", SR_OUT, wav)
        info = {k: call[k] for k in ("id", "label", "title")}
        if "alert_line" in call:
            info["alert_line"] = call["alert_line"]
            info["alert_by_seconds"] = meta[call["alert_line"]]["end"]
        info["duration_s"] = round(len(wav) / SR_OUT, 1)
        info["lines"] = meta
        json.dump(info, open(ROOT / f"samples/{call['id']}.json", "w"), indent=2)
        print(f"{call['id']}: {info['duration_s']}s")
    if g2p.oov:
        print("OOV words skipped:", sorted(g2p.oov), file=sys.stderr)


if __name__ == "__main__":
    main()
