# Scam Shield — Project Overview

On-device AI that listens to a phone call in real time and warns the user (especially older adults) when the call looks like a scam: urgency, secrecy, gift-card or crypto payment requests, impersonation of a grandchild, bank, IRS or police. **Everything runs locally. No audio or transcript ever leaves the device.**

Built at c0mpiled-15 (Penn State, Sun Oct 11 2026, building 12:00–7:00 PM).
- **Track:** 1B — YC Request for Startups Fall 2026 ("Proving You're Human" + "AI for the Aging Population")
- **Side prize:** AGI Inc — Best use of on-device intelligence
- **Submission:** 90-second demo video plus an optional live demo.

### Setup picks (measured Sat Oct 10 on this laptop)
- **Laptop:** Apple M2, macOS. Python 3.11.5 in `.venv`.
- **STT:** faster-whisper `small.en`, int8 CPU. It transcribed the 74 s hero call in 12.6 s (`base.en`: 4.6 s, no punctuation). Backup: `mlx-whisper` `mlx-community/whisper-base.en-mlx` at 0.9 s. **ffmpeg is not installed**, so pass mlx a float32 numpy array, never a file path.
- **LLM:** Ollama `llama3.2:3b`, 1.6 s warm, risk 95 with a specific reason. `qwen2.5:3b` is also pulled (1.2 s warm, but its reasons are more generic). First call after load takes 6–10 s, so warm up at backend startup and send `keep_alive`.
- **Frontend:** Node 24.21.0 + npm 11 (official binary in `~/.local/node-v24`, put first on PATH via `~/.zshrc`). The old Node 20.13 in `/usr/local/bin` is too old for Vite 8, so if `node --version` shows 20.x, open a new terminal. Homebrew has no Node bottle for this macOS, so don't `brew install node` (it compiles from source and takes ages).
- **Disk is nearly full** (~3.5 GB free). Don't pull more models.

---

## Rules for working in this repo (read first)

- **Never add Claude as a co-author.** No `Co-Authored-By` trailer on any commit.
- **Commits: you may commit and push yourself.** Break each build part into several small commits (one logical step each, every one working). **Commit messages: short, lowercase, plain words, like a person would write** (e.g. `add audio chunking`, `fix stop button`, `hook up whisper`). No long descriptive sentences, no bodies. Test a part before committing it.
- **Push after each part** to `origin` (private repo: https://github.com/itsanushkah/scam-shield, branch `main`).
- **Still ask first** before force-pushing, rewriting pushed history, changing the repo's visibility (it stays private until I say), or creating other GitHub repos.
- **Setup commands are OK to run yourself** (installing packages, downloading models/tools, test runs), but say what you're about to download or change first.
- **Never add a network call** to the core pipeline (capture → STT → scoring → alert). The only allowed exception is the opt-in family alert (see Stretch goals), and it must be clearly labeled and off by default.
- **Hackathon rule:** the product must be built during the event. Pre-downloading models and tools is fine; application code gets written on Sunday.

---

## Architecture

```
[Mic / demo WAV] → [Audio chunker + VAD] → [Local STT: faster-whisper]
        → [Rolling transcript, last ~60s]
        → [Rule scorer]  ─┐
        → [Local LLM scorer (Ollama)] ─┴→ [Score fusion + smoothing] → [WebSocket] → [Phone-style UI + alert]
```

Two processes on one laptop:
1. **Backend:** Python, FastAPI. Does audio, STT, scoring, and pushes events over WebSocket.
2. **Frontend:** React (Vite). A phone-shaped call screen showing a live transcript, a risk meter, and the alert.

**Ollama** runs as a local service (`localhost:11434`).

---

## Components and services

| Piece | Choice | Notes |
|---|---|---|
| Backend | Python 3.11 + FastAPI + uvicorn | WebSocket endpoint `/ws/call` |
| Audio input (live) | Browser `getUserMedia` + AudioWorklet → 16 kHz mono PCM16 over WebSocket | Fallback: Python `sounddevice` on the backend |
| Audio input (demo mode) | Backend streams a WAV file from `samples/` in real-time-paced chunks | **Primary path for the video**, since it's deterministic |
| Voice activity detection | faster-whisper's built-in `vad_filter` (Silero) | Skips silence and saves compute |
| Speech-to-text | `faster-whisper`, model `base.en` or `small.en`, `compute_type="int8"`, CPU | On Apple Silicon, `mlx-whisper` is a faster alternative. Chunk ~3 s with ~0.5 s overlap |
| LLM scorer | Ollama, small instruct model (e.g. `llama3.2:3b` or `qwen2.5:3b`; check for newer small models) | Use Ollama's structured output (`format` = JSON schema). Target under 2 s per call |
| Rule scorer | Plain Python regex + weighted keywords | Instant, explainable, and works even if the LLM is slow |
| Frontend | React + Vite + Tailwind | Phone-frame layout, green/yellow/red meter, reason text |
| Test audio | Already generated (Kokoro TTS, phone-line filtered, 16 kHz mono PCM16) in `samples/`. See "Prepared assets" below | Regenerate with `tools/make_calls.py` if scripts change |
| Storage | None by default. Nothing written to disk during a call | This is part of the privacy pitch |

**Deliberately NOT used:** cloud STT or LLM APIs, MongoDB, and AWS. Any of them would break the on-device story.

---

## Scoring logic

### Rule scorer
Weighted signal categories, each matched against the rolling transcript:
- **Payment:** gift card, iTunes, Google Play, Bitcoin, crypto, wire, Western Union, Zelle, bail money
- **Urgency:** right now, immediately, before it's too late, within the hour
- **Secrecy:** don't tell, keep this between us, don't hang up, stay on the line
- **Impersonation:** grandma, grandpa, it's me, IRS, Social Security, your bank, police, warrant, arrested
- **Credentials:** read me the code, verification code, PIN, password, account number, SSN

**Whisper writes spoken amounts as digits** ("two thousand dollars" → "$2,000"), so match dollar amounts with a regex like `\$\s?\d[\d,]*`, not just number words. See `samples/STT_CHECK.md`.

The score comes from the categories hit, not raw keyword count. Hitting several categories together should score much higher than any one category alone.

### LLM scorer
Every new transcript chunk, send the last ~60 s of transcript. The prompt asks for JSON:
```json
{
  "risk": 0-100,
  "signals": ["urgency", "secrecy", "payment_request", "impersonation", "credential_request"],
  "reason": "one plain-English sentence a grandparent would understand",
  "suggested_action": "short instruction, e.g. 'Hang up and call your grandson on his usual number.'"
}
```
- Keep the prompt short, with 2–3 few-shot examples (one scam, one normal family call, one legit bank call).
- Use temperature 0.
- If the LLM call is still running when a new chunk arrives, skip that chunk. Don't queue.

### Fusion
- `combined = max(rule_score, llm_score)`, then an exponential moving average to avoid flicker.
- **Latch:** once red, stay red for the rest of the call.
- Thresholds:
  - **Green** (< 40)
  - **Yellow** (40–70): "Be careful"
  - **Red** (> 70): full alert

---

## WebSocket events (backend → frontend)
```json
{"type": "transcript", "text": "...", "t": 12.4}
{"type": "score", "risk": 63, "level": "yellow", "signals": ["urgency"], "reason": "...", "suggested_action": "..."}
{"type": "alert", "risk": 88, "reason": "...", "suggested_action": "..."}
{"type": "status", "stt": "ok", "llm": "ok", "offline": true}
```
Frontend → backend: `{"type": "start", "mode": "live" | "demo", "sample": "grandson_bail.wav"}`, `{"type": "stop"}`, and binary PCM frames in live mode.

---

## Repo structure
```
scam-shield/
  CLAUDE.md
  backend/
    main.py            # FastAPI app + WebSocket
    audio.py           # chunking, demo-mode WAV streaming
    stt.py             # faster-whisper wrapper
    rules.py           # rule scorer
    llm.py             # Ollama client + prompt
    fusion.py          # combine + smooth + latch
    requirements.txt
  frontend/
    src/
      App.jsx
      PhoneFrame.jsx
      RiskMeter.jsx
      Transcript.jsx
      AlertBanner.jsx
  samples/             # demo WAVs (scam + normal)
  eval/
    transcripts/       # labeled scam / normal text files
    run_eval.py        # accuracy on held-out examples
```

---

## Build plan (Sunday)

| Time | Goal |
|---|---|
| 12:00–1:00 | Repo skeleton. FastAPI + WebSocket echo. React phone frame. Demo-mode WAV streaming |
| 1:00–2:30 | faster-whisper streaming transcript visible in the UI |
| 2:30–4:00 | Rule scorer + Ollama LLM scorer + fusion. Risk meter moves live |
| 4:00–5:00 | Alert banner, reasons, suggested action. Polish the UI (big text, high contrast, senior-friendly) |
| 5:00–5:45 | Eval: run on ~10 scam + ~10 normal held-out transcripts, show accuracy and false positives |
| 5:45–6:30 | Record the 90 s demo video, **with wifi visibly turned off** |
| 6:30–7:00 | Buffer, submission, slides if needed |

**Freeze features by 5:00.** After that, only fixes and polish.

---

## Stretch goals (only if the core is solid)
1. **Synthetic voice detection:** an open-source anti-spoofing model (e.g. AASIST) to flag cloned voices. Show it as a separate "voice check" badge.
2. **Opt-in family alert:** text a trusted contact on red, using SMS via Twilio. This is the *only* network call and must be off by default and labeled.
3. **Live mic mode** polished enough to demo with a teammate playing the scammer.
4. **Verification prompt:** suggest a question only the real person would know.

---

## Demo video script (90 s)
1. **0–10 s:** The hook. Voice-clone scams target grandparents, and Scam Shield runs entirely on the phone.
2. **10–25 s:** A normal call. The transcript scrolls and the meter stays green.
3. **25–60 s:** The "grandson in jail" call. Signals light up, the meter climbs, and the red alert fires with a plain-English reason and what to do.
4. **60–75 s:** Wifi off on camera, everything still works, and the eval numbers.
5. **75–90 s:** The YC RFS fit, why on-device matters (nobody wants a cloud listening to their calls), and what's next.

---

## Prepared assets (done Saturday)

**`samples/`: demo call recordings.** 16 kHz mono PCM16 WAV, narrowband phone filter. Each WAV has a matching `.json` with per-line `start`/`end` seconds and text. Scam calls also have `alert_by_seconds`, the time by which the meter should be red. Use it to check alert timing.

| File | Label | Purpose |
|---|---|---|
| `scam_grandson_bail.wav` | scam | **Hero demo.** Escalates slowly: impersonation → arrest → secrecy → gift cards → stay on the line |
| `normal_grandson_checkin.wav` | normal | Real grandson. Says "Grandma, it's me" but asks for nothing. **Must stay green** |
| `scam_irs_warrant.wav` | scam | Fake IRS agent, warrant threat, Bitcoin/gift cards |
| `normal_bank_fraud_alert.wav` | normal | Legit bank call. Talks about card and account, explicitly never asks for codes. **Must stay green** |
| `scam_bank_code.wav` | scam | Fake bank call that demands the verification code. Pair with the legit one to show the model understands *intent*, not keywords |

- `samples/scripts/calls.json` holds the source scripts.
- `samples/STT_CHECK.md` has the Whisper base.en transcription check: 2–5% WER, all scam keywords correct.

**`eval/`: held-out eval set.** 10 scam + 10 normal transcripts in `eval/eval_set.json`, also split into `eval/transcripts/*.txt` plus `eval/labels.csv`. Six normals are hard negatives (bank, police, small family money ask, user-initiated code). **Never use these as few-shot examples or for tuning keywords.** Few-shot examples come from the demo scripts or new text.

**Older prep (archived, not the official set):**
- `eval/extra/transcripts/`: an earlier set of 10 scam + 10 normal monologue-style transcripts, unlabeled. Keep it out of `run_eval.py` by default. It can serve as a secondary check or as a source of few-shot text, since it isn't part of the held-out set.
- `samples/piper_old/`: earlier Piper-generated calls (`grandson_bail.wav`, `normal_family_dinner.wav`) and their script. Superseded by the Kokoro calls above.
- `voices/` (Piper voice models) and the root `piper_test.wav` / `test_call.wav` are local only and gitignored.

**Setup:** see `SETUP.md`.
