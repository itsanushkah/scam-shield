# Scam Shield

**On-device AI that listens to a phone call and warns older adults about scams, in real time.**

🏆 **1st place, Transpose Platform (YC Requests for Startups)** · 🥈 **2nd place, AGI Inc: Best Use of On-Device Intelligence** · c0mpiled-15, Penn State, Oct 2026

> 🔒 **100% on-device.** Speech-to-text and the AI both run on the laptop. **No internet needed**, and no audio or words ever leave the device.

"Grandma, it's me. I've been arrested, I need bail money right now, don't tell Mom." Scam Shield hears the call as it happens, spots the pressure tactics, and tells the person what's going on and what to do: *"Don't send money. Hang up and call your family member on their usual number."*

Built solo in one day at **c0mpiled-15** (Penn State, Oct 11 2026) · YC Requests for Startups Fall 2026: *AI for the Aging Population* and *Proving You're Human*.

## What it does

- **Live transcript** of the call in large, readable text.
- **Risk meter** from green to yellow to red, with the reasons **building up as the call goes on**: *Asking for money: "bail money", "gift cards"* · *Wants it kept secret: "don't tell"* · *Rushing you: "right now"*.
- **Full-screen warning** when the call turns red, with one clear instruction and a big **Hang up** button.
- **"Is it really Ethan?"** When the caller claims to be family and the call looks wrong, it suggests how to check, using the name they gave: ask something only Ethan would know, ask for the family safe word, or hang up and call him back. *It doesn't just flag the scam: it tells Grandma how to prove who's really calling.*
- **Call summary** at the end: the verdict, when the warning fired, what the caller did and said, and what to do now.
- **Live** mode listens through the microphone (put a call on speaker nearby). **Recording** mode plays a test call out loud.

It judges what the caller **wants**, not single words: a real grandson saying "Grandma, it's me" stays green, and a real bank saying "we'll never ask for your PIN" stays green.

## How it works

```
Mic or recording ─► Whisper (speech-to-text, on device)
                 ─► last 60 s of transcript
                      ├─► rule scorer: money, urgency, secrecy, impersonation, codes
                      └─► Llama 3.2 3B via Ollama (on device): risk, reason, advice as JSON
                 ─► fusion: either can raise the alarm, smoothed, stays red once red
                 ─► phone-style screen: transcript, meter, reasons, warning, summary
```

## Results

Scored on test calls we **never tuned on**, including a fresh blind set written by an agent that never saw the code or prompts:

| | Fresh blind set (30 calls) | Held-out set (20 calls) |
|---|---|---|
| Keyword rules alone (baseline) | 4/15 scams caught · 0 false alarms | 4/10 · 0 |
| Improved rules (parallel agent round) | 9/15 · 0 | 7/10 · 0 |
| **Scam Shield (rules + on-device AI)** | **13/15 · 1** | **10/10 · 0** |

How we got there, round by round (including five agents working in parallel), is in [IMPROVEMENTS.md](IMPROVEMENTS.md). Reproduce with `python eval/run_eval.py --whole --data eval/fresh/fresh_set.json`.

## Run it

Needs Python 3.11, Node 20.19+, and [Ollama](https://ollama.com). Tested on an M2 MacBook Air.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
ollama pull llama3.2:3b
cd frontend && npm install && cd ..
```

```bash
.venv/bin/uvicorn main:app --app-dir backend --port 8000   # terminal 1
cd frontend && npm run dev                                   # terminal 2
```

Open http://localhost:5173 in Chrome. Test calls are in `samples/`. Once the models are downloaded, you can turn wifi off.

## What's next

- **On the phone.** The models are already phone-sized (about 150 MB for speech-to-text and about 2 GB for the AI), the same class of on-device model that phones now run. First step: a phone app that listens on speakerphone. Then built into the phone's dialer through a phone maker or carrier.
- **Family alert:** an opt-in text to a trusted contact when a scam is detected.
- **Voice-clone check:** flag when the caller's voice sounds synthetic.
