"""Checks the rule scorer against the demo call scripts. Run: python backend/test_rules.py"""

import json
from pathlib import Path

import rules

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def check_demo_calls():
    for path in sorted(SAMPLES.glob("*.json")):
        call = json.loads(path.read_text())
        text, first_red = "", None
        for line in call["lines"]:
            text += " " + line["text"]
            if first_red is None and rules.score(text)["risk"] > 70:
                first_red = line["start"]

        final = rules.score(text)["risk"]
        if call["label"] == "normal":
            assert final < 40, f"{call['id']} should stay green, got {final}"
        else:
            assert first_red is not None and first_red <= call["alert_by_seconds"], (
                f"{call['id']} should be red by {call['alert_by_seconds']}s, first red at {first_red}"
            )
        print(f"ok  {call['id']}: final {final}, first red {first_red}")


def check_edge_cases():
    assert rules.score("we will never ask you for your PIN or a code we text you")["risk"] == 0
    assert "credential_request" in rules.score("if you don't read me the code the money is gone")["signals"]
    assert rules.score("Hey Grandma, it's me!")["risk"] < 40
    assert rules.score("buy gift cards, $2,000, and don't tell mom")["risk"] >= 40
    assert rules.score("")["suggested_action"] == ""
    print("ok  edge cases")


if __name__ == "__main__":
    check_demo_calls()
    check_edge_cases()
