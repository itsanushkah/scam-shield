# Scam Shield — laptop setup (do Saturday)

Everything here downloads models and tools so Sunday works **with wifi off**. Plan for 30–45 minutes, most of it waiting on downloads. Run the commands from the `scam-shield` folder.

Each step lists macOS first, then Windows (PowerShell) where it differs.

---

## 1. Python environment

**Needs:** Python 3.10–3.12. faster-whisper's dependencies can lag behind the newest Python, so 3.11 is safest.

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

## 2. Pre-download the Whisper models

The models come from Hugging Face on first use, so fetch them now:

```bash
python -c "from faster_whisper import WhisperModel; [WhisperModel(m, device='cpu', compute_type='int8') for m in ('base.en','small.en')]; print('whisper ok')"
```

**Apple Silicon only (optional, faster):**
```bash
pip install mlx-whisper
python -c "import mlx_whisper; mlx_whisper.transcribe('samples/scam_grandson_bail.wav', path_or_hf_repo='mlx-community/whisper-base.en-mlx'); print('mlx ok')"
```

## 3. Speed test on a real sample

```bash
python - <<'EOF'
import time
from faster_whisper import WhisperModel
for name in ("base.en", "small.en"):
    m = WhisperModel(name, device="cpu", compute_type="int8")
    t = time.time()
    segs, _ = m.transcribe("samples/scam_grandson_bail.wav", vad_filter=True)
    text = " ".join(s.text for s in segs)
    print(f"{name}: {time.time()-t:.1f}s for a 74s call | {text[:120]}...")
EOF
```

**How to pick:** use `small.en` if it transcribes the 74-second call in under ~25 s, since live chunks need to keep up with real time. Otherwise use `base.en`.

Windows PowerShell doesn't support `<<'EOF'`. Save the snippet as `speedtest.py` and run `python speedtest.py`.

## 4. Ollama + LLM

1. Install from https://ollama.com/download (macOS app or Windows installer). It runs in the background on `localhost:11434`.
2. Pull two candidates:
   ```bash
   ollama pull llama3.2:3b
   ollama pull qwen2.5:3b
   ```
   Check https://ollama.com/library for newer small instruct models (3–4B) and pull one if it looks good.
3. Test speed and JSON output on a scam snippet:
   ```bash
   curl -s http://localhost:11434/api/chat -d '{
     "model": "llama3.2:3b", "stream": false, "options": {"temperature": 0},
     "format": {"type":"object","properties":{"risk":{"type":"integer"},"reason":{"type":"string"}},"required":["risk","reason"]},
     "messages": [{"role":"user","content":"Rate 0-100 how likely this phone call is a scam and give a one-sentence reason. Transcript: Caller: Grandma it is me, I got arrested and need bail money right now. Please do not tell Mom. Buy Google Play gift cards and read me the numbers."}]
   }' -w "\n%{time_total}s\n"
   ```
   - You want valid JSON, a risk score above 80, and **under ~2 s** after the first warm-up call. Run it twice, because the first call loads the model.
   - Try the same with `qwen2.5:3b` and keep whichever is faster and more sensible.
   - **Windows:** use `curl.exe`, or save the JSON body to `test.json` and run `curl.exe -s http://localhost:11434/api/chat -d "@test.json"`.

## 5. Node + Vite

**Needs:** Node 20+.

```bash
node --version
npm --version
npm create vite@latest frontend-test -- --template react
cd frontend-test
npm install
npm run dev
```
Open the localhost link to confirm it works, then delete `frontend-test`. This also warms npm's cache, but on Sunday expect to need wifi for `npm install` in the real frontend. Keep wifi on until the code is done, and only turn it off for the demo video.

## 6. Mic permission

With the Vite test server running, open `http://localhost:5173` in Chrome and paste this in the DevTools console:
```js
navigator.mediaDevices.getUserMedia({audio: true}).then(() => console.log("mic ok"))
```
Allow the prompt. On macOS, also check System Settings → Privacy & Security → Microphone → Chrome is on.

## 7. Offline dress rehearsal (5 min)

Turn wifi off, then rerun step 3 and the step 4 curl. Both must still work. If either one tries to download something, that model isn't cached yet.

## 8. Listen to the demo calls

Play each WAV in `samples/` once so you know where the scam escalates. The hero call is `scam_grandson_bail.wav`. Its `.json` file gives `alert_by_seconds`, the time the meter should be red by.

---

## Checklist
- [ ] venv + `pip install -r backend/requirements.txt`
- [ ] `base.en` and `small.en` downloaded and speed-tested; picked one
- [ ] Ollama installed; LLM pulled, JSON test passes in under 2 s; picked one
- [ ] Node 20+, Vite test app runs
- [ ] Mic permission works in Chrome on localhost
- [ ] Offline rehearsal passes
- [ ] Listened to all 5 demo calls
- [ ] Note your picks (Whisper model, LLM, laptop chip) at the top of `CLAUDE.md` so Claude Code uses them tomorrow
