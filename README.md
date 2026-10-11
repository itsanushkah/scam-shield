# Scam Shield

**On-device AI that listens to a phone call and warns older adults about scams, in real time.**

Phone scams aimed at grandparents ("Grandma, it's me, I've been arrested, I need bail money, don't tell Mom") are getting more convincing with voice cloning. Scam Shield listens to the call as it happens, spots the pressure tactics scammers use, and puts a plain-English warning on screen with one clear thing to do: *"Don't send money. Hang up and call your family member on their usual number."*

**Everything runs on the device.** No audio or transcript ever leaves the laptop. It works with wifi off.

Built solo at **c0mpiled-15** (Penn State, Oct 11 2026) for Track 1B, YC Request for Startups Fall 2026: *AI for the Aging Population* and *Proving You're Human*.

---

## What it does

- **Live transcript** of the call in large, readable text.
- **Risk meter** that moves from green ("Looks safe") to yellow ("Be careful") to red ("Likely a scam"), with the reason in plain words and tags like *Asks for money* or *Wants secrecy*.
- **Full-screen warning** the moment a call turns red, with one instruction and big **Hang up** / **Keep listening** buttons.
- **Call summary** when the call ends: the verdict, when the warning fired, what the caller did, the phrases they used ("gift cards", "don't tell Mom"), and what to do now. Built from what was tracked during the call, so it's instant.
- **Two input modes:** **Live** listens through the laptop microphone (put a call on speaker next to it), and **Recording** plays one of the included test calls out loud while analysing it.

It looks at what the caller **wants**, not single words. A real grandson saying "Grandma, it's me" stays green. A real bank saying *"we will never ask for your PIN"* stays green. A fake bank demanding the code goes red.

## How it works

```
 Mic (live) or test call (recording)
        │  16 kHz mono audio, 3 s chunks every 2.5 s
        ▼
 Speech-to-text ─ faster-whisper base.en, on CPU, last ~6 s of context
        │  new words only (overlap de-duplicated)
        ▼
 Last 60 s of transcript
        ├──► Rule scorer ── 5 signal categories, instant and explainable
        └──► LLM scorer ─── llama3.2:3b in Ollama on this laptop, JSON output
        ▼
 Fusion ─ max of both, smoothed (fast up, slow down), latches red once red
        ▼
 WebSocket ──► React phone-style screen: transcript, meter, warning
```

**The five scam signals:** payment by gift card, wire or crypto · urgency · secrecy ("don't tell anyone", "stay on the line") · impersonation (family, bank, IRS, police) · requests for codes, PINs or account numbers.

- **Rule scorer** (`backend/rules.py`): weighted phrase categories. The score comes from *how many categories* are hit, not how many keywords, so one category alone stays green and several together go red. Phrases like "never ask for your PIN" are recognized as the opposite of a scam.
- **LLM scorer** (`backend/llm.py`): a 3B model reads the recent transcript and returns `risk`, `signals`, `reason` and `suggested_action` as structured JSON. One request at a time; if it's still busy when new speech arrives, that chunk is skipped rather than queued.
- **Fusion** (`backend/fusion.py`): either scorer can raise the alarm. The rule reason is shown when the rules found something (it's concrete); otherwise the LLM's, so scams without obvious keywords are still caught. If only the LLM is worried, it warns yellow first and goes red when it repeats.

## Results

Held-out eval set: 10 scam and 10 normal call transcripts, 6 of the normals deliberately tricky (a real bank, a police fundraiser, a grandchild asking for $20, a help desk asking you to type a code yourself). **Nothing was tuned on this set.** Each transcript is fed line by line like a live call.

| | Accuracy | Scams caught (red alert) | False alarms | Tricky normals flagged |
|---|---|---|---|---|
| Keyword rules only | 70% | 4/10 | 0/10 | 0/6 |
| Local LLM only | 90% | 9/10 | 1/10 | 1/6 |
| **Scam Shield (both)** | **90%** | **9/10** | **1/10** | **1/6** |

- The one missed scam (fake Medicare card, asks for an SSN) still got a yellow "Be careful".
- The one false alarm is a library help desk telling the caller to type a login code in themselves.
- Speech-to-text word error rate on the demo calls: about 3%.

Reproduce with `python eval/run_eval.py`. Per-call detail is in `eval/results.json`.

## Privacy

- Speech-to-text and the LLM both run locally. The LLM is served by Ollama on `localhost`.
- Nothing is written to disk during a call.
- No cloud APIs, no accounts, no analytics. The core pipeline makes no network calls.

## Run it

Tested on an Apple M2 MacBook Air (8 GB RAM), macOS.

**You need:** Python 3.10 to 3.12 (3.11 recommended), Node 20.19+ or 22.12+, and [Ollama](https://ollama.com).

```bash
# 1. Python backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 2. Local LLM
ollama pull llama3.2:3b

# 3. Frontend
cd frontend && npm install && cd ..
```

Then, in two terminals:

```bash
# Terminal 1: backend on :8000 (loads Whisper and warms up the LLM on start)
.venv/bin/uvicorn main:app --app-dir backend --port 8000
```

```bash
# Terminal 2: frontend on :5173
cd frontend && npm run dev
```

Open **http://localhost:5173** in Chrome.

- **Live:** press *Start listening*, allow the microphone, and play a call on a speaker nearby (a phone works well).
- **Recording:** pick a test call and press *Play file*.

The test calls are also in `samples/` for playing from another device.

**Checks:**

```bash
.venv/bin/python backend/test_rules.py    # rule scorer on the demo calls
.venv/bin/python backend/test_fusion.py   # smoothing, latch, reason choice
.venv/bin/python eval/run_eval.py         # held-out eval (needs Ollama)
```

**Low on memory?** On an 8 GB laptop, close other heavy apps (browsers with many tabs, chat apps). If the LLM can't answer in time, the app shows *"AI check paused"* and carries on with the keyword rules, and the transcript switches to a shorter window to keep up.

## Project layout

```
backend/
  main.py          FastAPI app, WebSocket /ws/call, runs each call
  audio.py         demo-file and live-mic chunking
  stt.py           faster-whisper transcriber
  rules.py         rule scorer
  llm.py           Ollama client, prompt and JSON schema
  fusion.py        combine, smooth, latch
  summary.py       end-of-call summary
  test_rules.py, test_fusion.py
frontend/src/
  App.jsx          page layout, call header
  ControlPanel.jsx Live / Recording controls
  PhoneFrame.jsx, RiskMeter.jsx, Transcript.jsx, AlertBanner.jsx, CallSummary.jsx
  useCallSocket.js WebSocket hook
  mic.js, pcmWorklet.js   16 kHz mic capture
samples/           test calls (WAV + per-line timing JSON) and their scripts
eval/              held-out eval set, run_eval.py, results.json
tools/             scripts that generated the test calls (offline TTS)
```

## From laptop to phone

This prototype runs on a laptop with a phone-shaped screen. The models are phone-sized: about 150 MB for speech-to-text and a 3B-parameter LLM (about 2 GB), the same size class as the on-device models Apple and Google now ship on phones.

The real obstacle is access to call audio, not the AI: ordinary apps can't listen to regular cellular calls on iOS or Android. Paths to a phone:

1. **Speakerphone mode:** the call on speaker, Scam Shield on a second device such as a tablet or an old phone. Works today, and it's what the live demo shows.
2. **Built into the phone or dialer** through a phone maker or carrier partnership.
3. **Own calling app** for internet calls, such as a family "safe line".

## Limitations

- Tested on synthetic, text-to-speech calls and short written transcripts, not real recorded scam calls.
- English only.
- The small speech model sometimes mishears words ("Buy" as "Bye").
- On an 8 GB laptop with other apps open, memory pressure can slow the transcript and the LLM.
- 20 held-out calls is a small eval. The numbers show the approach works, not production accuracy.

## Credits

Speech-to-text: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (OpenAI Whisper). LLM: Meta Llama 3.2 3B via [Ollama](https://ollama.com). Test calls generated offline with Kokoro and Piper TTS. Frontend: React, Vite, Tailwind. Backend: FastAPI.
