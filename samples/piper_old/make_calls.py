"""Generate two-voice demo call WAVs with Piper, then resample to 16 kHz mono."""
import os, subprocess, sys, tempfile, wave

ROOT = "/Users/anushka/coding_good_proj/projects/scamshield"
PY = f"{ROOT}/.venv/bin/python"
VOICES = {"G": f"{ROOT}/voices/en_US-lessac-medium.onnx",   # grandma
          "C": f"{ROOT}/voices/en_US-ryan-medium.onnx"}     # caller / grandson
PAUSE_S = 0.6

CALLS = {
    "normal_family_dinner": [
        ("C", "Hi Grandma, it's Sam!"),
        ("G", "Oh Sam, how nice to hear from you!"),
        ("C", "I just wanted to say I'll be home for dinner on Sunday. Mom's making lasagna."),
        ("G", "Wonderful. Should I bake a pie?"),
        ("C", "Yes please, the apple one! Love you, see you Sunday."),
    ],
    "grandson_bail": [
        ("C", "Grandma? It's me."),
        ("G", "Sam? You sound different."),
        ("C", "I have a cold. Grandma, I'm in trouble. I was in a car accident and the police arrested me."),
        ("G", "Oh no! Are you okay?"),
        ("C", "I'm okay, but I need bail money right now, before they move me. Please don't tell Mom and Dad, they'll be so angry."),
        ("G", "How much do you need?"),
        ("C", "My lawyer says you can pay with gift cards. Go to the store, buy two thousand dollars in Google Play cards, and read me the numbers. Please hurry, and stay on the line."),
    ],
}


def synth(voice, text, out):
    subprocess.run([PY, "-m", "piper", "-m", VOICES[voice], "-f", out],
                   input=text.encode(), check=True, capture_output=True)


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name, lines in CALLS.items():
            frames, params = [], None
            for i, (v, text) in enumerate(lines):
                p = os.path.join(tmp, f"{name}_{i}.wav")
                synth(v, text, p)
                with wave.open(p) as w:
                    params = params or w.getparams()
                    frames.append(w.readframes(w.getnframes()))
            silence = b"\x00" * int(params.framerate * PAUSE_S) * params.sampwidth
            raw = os.path.join(tmp, f"{name}_22k.wav")
            with wave.open(raw, "wb") as w:
                w.setparams(params)
                w.writeframes(silence + silence.join(frames) + silence)
            out = os.path.join(out_dir, f"{name}.wav")
            subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", raw, out], check=True)
            print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1])
