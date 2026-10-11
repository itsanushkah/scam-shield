"""Evaluate Scam Shield on the held-out eval set (eval/eval_set.json).

Each transcript is fed line by line, the way a live call arrives: the rule scorer
and the local LLM score the call so far after every line, and fusion decides the
level with the same smoothing and red latch the app uses. A call counts as
flagged if it ever goes red (the full alert).

Nothing in the scorers was tuned on this set.

Usage:
  python eval/run_eval.py            # rules + LLM (needs Ollama running)
  python eval/run_eval.py --no-llm   # rules only
"""

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import fusion  # noqa: E402
import llm  # noqa: E402
import rules  # noqa: E402

SPEAKER = re.compile(r"^\s*(caller|you)\s*:\s*", re.I)
SYSTEMS = ("rules", "llm", "fused")


def lines_of(text: str) -> list[str]:
    # The live app gets Whisper text with no speaker names, so strip them here too.
    return [SPEAKER.sub("", line).strip() for line in text.splitlines() if line.strip()]


async def run_call(item: dict, client: httpx.AsyncClient | None) -> dict:
    trackers = {name: fusion.Fusion() for name in SYSTEMS}
    first_red = {name: None for name in SYSTEMS}
    llm_times = []
    so_far = ""

    for i, line in enumerate(lines_of(item["text"])):
        so_far = f"{so_far} {line}".strip()
        r = rules.score(so_far)
        trackers["rules"].update(rules=r)
        trackers["fused"].update(rules=r)

        if client:
            t = time.monotonic()
            try:
                answer = await llm.score(so_far, client)
            except (httpx.HTTPError, ValueError):
                answer = None
            llm_times.append(time.monotonic() - t)
            if answer:
                trackers["llm"].update(llm=answer)
                trackers["fused"].update(llm=answer)

        for name, f in trackers.items():
            if f.latched and first_red[name] is None:
                first_red[name] = i

    out = {
        "id": item["id"],
        "label": item["label"],
        "hard": bool(item.get("hard")),
        "type": item.get("type", ""),
        "lines": i + 1,
        "llm_seconds": round(sum(llm_times) / len(llm_times), 2) if llm_times else None,
    }
    for name, f in trackers.items():
        if name == "llm" and not client:
            continue
        out[name] = {
            "flagged": f.latched,
            "first_red_line": first_red[name],
            "final_risk": round(f.smoothed) if f.smoothed is not None else None,
            "reason": f.reason,
        }
    return out


def summarize(results: list[dict], name: str) -> dict:
    scams = [r for r in results if r["label"] == "scam"]
    normals = [r for r in results if r["label"] == "normal"]
    caught = sum(r[name]["flagged"] for r in scams)
    false_alarms = [r["id"] for r in normals if r[name]["flagged"]]
    hard = [r for r in normals if r["hard"]]
    return {
        "accuracy": (caught + len(normals) - len(false_alarms)) / len(results),
        "scams_caught": f"{caught}/{len(scams)}",
        "false_alarms": f"{len(false_alarms)}/{len(normals)}",
        "hard_negative_false_alarms": f"{sum(r[name]['flagged'] for r in hard)}/{len(hard)}",
        "missed": [r["id"] for r in scams if not r[name]["flagged"]],
        "false_alarm_ids": false_alarms,
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true", help="rules only")
    args = ap.parse_args()

    items = json.loads((ROOT / "eval/eval_set.json").read_text())["items"]
    results = []

    async with httpx.AsyncClient() as client:
        use_llm = not args.no_llm and await llm.warm_up(client)
        if not args.no_llm and not use_llm:
            print("Ollama isn't reachable: running rules only.\n")

        for item in items:
            res = await run_call(item, client if use_llm else None)
            results.append(res)
            marks = "  ".join(
                f"{n}:{'RED' if res[n]['flagged'] else '---'}" for n in SYSTEMS if n in res
            )
            print(f"{res['id']:38} {res['label']:6} {'hard' if res['hard'] else '    '}  {marks}")

    systems = [n for n in SYSTEMS if n in results[0]]
    summary = {n: summarize(results, n) for n in systems}

    print()
    print(f"{'':8} {'accuracy':>9} {'scams caught':>13} {'false alarms':>13} {'hard negatives':>15}")
    for n in systems:
        s = summary[n]
        print(f"{n:8} {s['accuracy']:9.0%} {s['scams_caught']:>13} {s['false_alarms']:>13} {s['hard_negative_false_alarms']:>15}")
    for n in systems:
        if summary[n]["missed"] or summary[n]["false_alarm_ids"]:
            print(f"\n{n}: missed {summary[n]['missed'] or 'none'}; false alarms {summary[n]['false_alarm_ids'] or 'none'}")
    if use_llm:
        times = [r["llm_seconds"] for r in results if r["llm_seconds"]]
        print(f"\nLLM: {sum(times) / len(times):.1f} s per call on average ({llm.MODEL})")

    out = ROOT / "eval/results.json"
    out.write_text(json.dumps({"model": llm.MODEL if use_llm else None, "summary": summary, "calls": results}, indent=2))
    print(f"\nSaved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(main())
