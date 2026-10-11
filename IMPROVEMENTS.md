# Improvement log

How Scam Shield got better during the hackathon: each round is one idea, measured, and what we learned decided the next round. Numbers come from the scripts in this repo (`eval/run_eval.py`, `backend/test_*.py`) and the demo calls in `samples/`.

**Datasets, kept separate so tuning can't leak into the score:**

| Set | Size | Used for |
|---|---|---|
| `samples/` demo calls | 7 calls (audio + script) | Tuning speech-to-text and the first rules |
| `eval/dev/` | 40 transcripts | Tuning in the parallel round (written by an agent that never saw the code) |
| `eval/eval_set.json` | 20 transcripts | Held-out test, never tuned on |
| `eval/fresh/` | 30 transcripts | Fresh blind test, written by an agent that never saw the code or prompts; never tuned on |

## Baseline

Keyword rules alone on the held-out set: **4/10 scams caught**, 0/10 false alarms (70% accuracy).

## Speech-to-text rounds (measured on the 7 demo calls)

| Round | Idea | Before → after | What it taught us |
|---|---|---|---|
| S1 | `small.en` vs `base.en` on live 3 s chunks | small: 5.6% WER, 1.7 s/chunk, spikes to 7 s · base: 5.1% WER, 0.46 s/chunk | Bigger isn't better on short chunks; latency matters more. Kept `base.en`. |
| S2 | De-duplicate overlapping chunks by time, not by splitting the overlap | dropped edge words and an invented repeat → hero call clean | Words at chunk edges are the weak spot. |
| S3 | Single-pass decoding (no temperature fallback) | worst chunk 13.5 s → 1.45 s; all calls ≤ 0.83 s/chunk | Whisper's retries caused the stalls. |
| S4 | Drop repeated words across chunk edges by text | hero call 5.1% → 3.6% WER | Timestamps alone can't catch every repeat. |
| S5 | Give each decode 6 s of context instead of 3 s | all calls 4.2% → 3.2% WER; hero 3.6% → 2.1% | More context fixes dropped short words; added a fall-back to 3 s when the laptop falls behind. |

## Detection rounds

| Round | Idea | Before → after | What it taught us |
|---|---|---|---|
| D1 | Rule scorer: score by number of signal categories, not keyword count | demo calls: 5/5 correct, both tricky normals green | Category count separates "Grandma, it's me" from a scam. |
| D2 | "Never ask for your PIN" is the opposite of a scam | legit bank call: credentials flagged → green | Negation matters for the hardest negatives. |
| D3 | Local LLM: `llama3.2:3b` vs `qwen2.5:3b` | qwen faster but flagged the legit bank call (85) · llama 7/7 right | Judgment beats speed for the demo's key pair. |
| D4 | LLM JSON robustness: cap the signals list, salvage cut-off answers | 1/7 answers broken (a repetition loop) → 0/7 | Small models need guard rails in the schema. |
| D5 | Add the LLM to the rules, fused (either can raise the alarm, red latches) | held-out: **4/10 → 9/10 scams caught**, false alarms 0 → 1 | The LLM catches scams with no obvious keywords. |
| D6 | Whisper inserts full stops mid-sentence; let "never ask" span them | legit bank call on live audio: yellow (65) → green | Test on real transcripts, not just the scripts. |

## Parallel round (Sunday 4–5:30 PM)

Five agents, run in parallel. Two wrote data and three each attacked a different part of the detector, each in its own copy of the code, tuning **only on the dev set**:

| Agent | Approach | Outcome |
|---|---|---|
| Dev-set writer | 40 labeled dialogues (15 hard), without seeing the code | Used for all tuning |
| Blind test writer | 30 labeled dialogues (22 hard), without seeing the code **or prompts** | Used only for the final score |
| **Rules** | Tried (A) broader general scam patterns, (B) a scoring change (a clear money/code ask + another clear sign → red), (C) tightening for ordinary speech; kept A+B+C | **Dev: 8/20 → 16/20 scams caught, 0 false alarms**. Found and fixed a false alarm it caused ("gift card … call me right now" in family talk) by not letting urgency count as the partner. |
| Prompt | Wrote a checklist prompt built around "what does the caller want you to DO?" plus new keyword-free examples | Couldn't measure in time: the shared local LLM was overloaded by parallel runs (34/40 calls timed out). Scored afterwards, below. |
| Fusion | Added an agreement boost, an LLM-only cap, and smoothing knobs | Couldn't build its LLM answer cache for the same reason; kept old behavior. **Finding:** rule-only scams plateaued at 65, just under red, which is what the rules agent's scoring change then fixed. |

**Lesson:** on an 8 GB laptop, LLM-bound experiments can't share one local model in parallel. Rule experiments parallelize perfectly. Next time: run LLM experiments one after another, and parallelize everything else.

### Rules: before vs after, on test sets never tuned on

| Rules only | Before | After |
|---|---|---|
| **Fresh blind test** (30) | 4/15 caught · 0/15 false alarms · hard scams 1/11 | **9/15 caught · 0/15 false alarms · hard scams 6/11** |
| **Held-out test** (20) | 4/10 caught · 0/10 false alarms | **7/10 caught · 0/10 false alarms** |

### Prompt agent's new prompt, scored afterwards (dev only, Ollama free)

| LLM prompt | LLM alone, dev | Full system, dev |
|---|---|---|
| Current | 19/20 caught · 0/20 false alarms | 20/20 · 0/20 |
| New checklist prompt | 20/20 · 0/20 | 20/20 · 0/20 |

**Not adopted:** the full system was already 20/20, and the new prompt is 1.5× longer, which slows every call.

## Final results: full system on test sets never tuned on

One LLM call per transcript (`run_eval.py --whole`), run one after another so the local model wasn't overloaded.

| Full system (rules + local AI) | Before the parallel round | After |
|---|---|---|
| **Held-out set** (20) | 9/10 caught · 0/10 false alarms | **10/10 caught · 0/10 false alarms** |
| **Fresh blind set** (30) | 13/15 caught · 1/15 false alarms | **13/15 caught · 1/15 false alarms** |

- **Baseline to final, fresh blind test:** keyword rules alone caught **4/15**; the full system catches **13/15**.
- **What the parallel round added:** robustness. On the held-out set the LLM timed out on 2 scam calls, and the improved rules still caught both. On the fresh set the LLM already caught most of what the new rules add, so the full-system score didn't move.
- Remaining misses on the fresh set: reading back a texted code, and a remote-access app (where the LLM timed out). False alarm: a grandchild casually asking for a little money.
