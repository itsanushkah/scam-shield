"""Evaluate Scam Shield on the held-out eval set (eval/eval_set.json).

Each transcript is fed line by line, the way a live call arrives: the rule scorer
and the local LLM score the call so far after every line, and fusion decides the
level with the same smoothing and red latch the app uses. A call counts as
flagged if it ever goes red (the full alert).

Nothing in the scorers was tuned on this set.

Usage:
  python eval/run_eval.py                              # held-out set, rules + LLM (needs Ollama)
  python eval/run_eval.py --no-llm                     # rules only
  python eval/run_eval.py --data eval/dev/dev_set.json --out /tmp/dev.json
  python eval/run_eval.py --whole                      # one LLM call per call on the full text (fast)
  python eval/run_eval.py --llm-cache cache.json       # save/reuse every LLM answer (for tuning fusion)
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


async def run_call(item: dict, client: httpx.AsyncClient | None, whole: bool = False, cache: dict | None = None) -> dict:
    trackers = {name: fusion.Fusion() for name in SYSTEMS}
    first_red = {name: None for name in SYSTEMS}
    llm_times = []
    so_far = ""

    lines = lines_of(item["text"])
    steps = [" ".join(lines)] if whole else lines
    for i, line in enumerate(steps):
        so_far = line if whole else f"{so_far} {line}".strip()
        r = rules.score(so_far)
        trackers["rules"].update(rules=r)
        trackers["fused"].update(rules=r)

        if client:
            key = f"{item['id']}:{'whole' if whole else i}"
            t = time.monotonic()
            if cache is not None and key in cache:
                answer = cache[key]
            else:
                try:
                    answer = await llm.score(so_far, client)
                except (httpx.HTTPError, ValueError):
                    answer = None
                if cache is not None and answer:
                    cache[key] = answer
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
        "lines": len(lines),
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
    hard_scams = [r for r in scams if r["hard"]]
    return {
        "accuracy": (caught + len(normals) - len(false_alarms)) / len(results),
        "scams_caught": f"{caught}/{len(scams)}",
        "false_alarms": f"{len(false_alarms)}/{len(normals)}",
        "hard_negative_false_alarms": f"{sum(r[name]['flagged'] for r in hard)}/{len(hard)}",
        "hard_scams_caught": f"{sum(r[name]['flagged'] for r in hard_scams)}/{len(hard_scams)}",
        "missed": [r["id"] for r in scams if not r[name]["flagged"]],
        "false_alarm_ids": false_alarms,
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true", help="rules only")
    ap.add_argument("--data", default=str(ROOT / "eval/eval_set.json"), help="dataset JSON with an 'items' list")
    ap.add_argument("--out", default=str(ROOT / "eval/results.json"), help="where to save results")
    ap.add_argument("--whole", action="store_true", help="score each full transcript once instead of line by line")
    ap.add_argument("--llm-cache", help="JSON file of LLM answers to reuse and extend")
    args = ap.parse_args()

    items = json.loads(Path(args.data).read_text())["items"]
    cache = json.loads(Path(args.llm_cache).read_text()) if args.llm_cache and Path(args.llm_cache).exists() else ({} if args.llm_cache else None)
    results = []

    async with httpx.AsyncClient() as client:
        use_llm = not args.no_llm and await llm.warm_up(client)
        if not args.no_llm and not use_llm:
            print("Ollama isn't reachable: running rules only.\n")

        for item in items:
            res = await run_call(item, client if use_llm else None, args.whole, cache)
            results.append(res)
            marks = "  ".join(
                f"{n}:{'RED' if res[n]['flagged'] else '---'}" for n in SYSTEMS if n in res
            )
            print(f"{res['id']:38} {res['label']:6} {'hard' if res['hard'] else '    '}  {marks}")

    systems = [n for n in SYSTEMS if n in results[0]]
    summary = {n: summarize(results, n) for n in systems}

    print()
    print(f"{'':8} {'accuracy':>9} {'scams caught':>13} {'false alarms':>13} {'hard negatives':>15} {'hard scams':>11}")
    for n in systems:
        s = summary[n]
        print(f"{n:8} {s['accuracy']:9.0%} {s['scams_caught']:>13} {s['false_alarms']:>13} {s['hard_negative_false_alarms']:>15} {s['hard_scams_caught']:>11}")
    for n in systems:
        if summary[n]["missed"] or summary[n]["false_alarm_ids"]:
            print(f"\n{n}: missed {summary[n]['missed'] or 'none'}; false alarms {summary[n]['false_alarm_ids'] or 'none'}")
    if use_llm:
        times = [r["llm_seconds"] for r in results if r["llm_seconds"]]
        print(f"\nLLM: {sum(times) / len(times):.1f} s per call on average ({llm.MODEL})")

    if cache is not None:
        Path(args.llm_cache).write_text(json.dumps(cache, indent=1))
    out = Path(args.out)
    out.write_text(json.dumps({"model": llm.MODEL if use_llm else None, "data": args.data, "summary": summary, "calls": results}, indent=2))
    print(f"\nSaved {out}")


if __name__ == "__main__":
    asyncio.run(main())
