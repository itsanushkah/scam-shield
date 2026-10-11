"""Fusion: combine the rule and LLM scores into one steady risk level for the UI.

- combined = max(rules, llm), so either scorer can raise the alarm.
- Exponential moving average to stop the meter flickering. It rises fast (strong
  evidence should show at once) and falls slowly (one calm sentence shouldn't
  undo a scam).
- Latch: once red, stay red for the rest of the call.
"""

GREEN_BELOW = 40
RED_ABOVE = 70

ALPHA_UP = 0.75  # weight of a new, higher score
ALPHA_DOWN = 0.25  # weight of a new, lower score


def level_for(risk: float) -> str:
    return "red" if risk > RED_ABOVE else "yellow" if risk >= GREEN_BELOW else "green"


class Fusion:
    """Per-call state. Call update() whenever either scorer has a new result."""

    def __init__(self):
        self.rules = None
        self.llm = None
        self.smoothed = None
        self.latched = False
        self.peak = 0
        self.reason = ""
        self.action = ""

    def update(self, rules: dict | None = None, llm: dict | None = None) -> tuple[dict, dict | None]:
        """Feed a new result. Returns (score event, alert event or None)."""
        if rules is not None:
            self.rules = rules
        if llm is not None:
            self.llm = llm

        combined = max(r["risk"] for r in (self.rules, self.llm) if r)
        if self.smoothed is None:
            self.smoothed = combined
        else:
            alpha = ALPHA_UP if combined > self.smoothed else ALPHA_DOWN
            self.smoothed += alpha * (combined - self.smoothed)

        alert = None
        if not self.latched and self.smoothed > RED_ABOVE:
            self.latched = True
            alert = True

        risk = round(self.smoothed)
        if self.latched:
            self.peak = max(self.peak, risk)
            risk = self.peak
        level = "red" if self.latched else level_for(risk)

        self._pick_reason(level)
        event = {
            "type": "score",
            "risk": risk,
            "level": level,
            "signals": self._signals(),
            "reason": self.reason,
            "suggested_action": self.action,
            "rules_risk": self.rules["risk"] if self.rules else None,
            "llm_risk": self.llm["risk"] if self.llm else None,
        }
        if alert:
            alert = {"type": "alert", "risk": risk, "reason": self.reason, "suggested_action": self.action}
        return event, alert

    def _pick_reason(self, level: str):
        """Rules give concrete reasons ("wants gift cards"), so prefer them when they see
        something. Otherwise use the LLM, which can spot scams without keywords. After the
        latch, only replace the reason with one from a result that is itself red, so a
        calmer later stretch can't water down the warning."""
        if level == "green":
            self.reason, self.action = "", ""
            return

        rules, llm = self.rules, self.llm
        if rules and rules["risk"] >= GREEN_BELOW and rules["reason"]:
            source = rules
        elif llm and llm["risk"] >= GREEN_BELOW and llm.get("reason"):
            source = llm
        else:
            return

        if self.latched and source["risk"] <= RED_ABOVE and self.reason:
            return
        self.reason = source["reason"]
        self.action = source.get("suggested_action") or self.action

    def _signals(self) -> list[str]:
        found = set()
        for r in (self.rules, self.llm):
            if r and r["risk"] >= GREEN_BELOW:
                found.update(r["signals"])
        return sorted(found)
