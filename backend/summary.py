"""End-of-call summary: what happened on the call, built from what was tracked live.

No extra model call, so it's instant and works even when the LLM is paused.
"""

import math

from fusion import LEVELS

MAX_PHRASES = 6
# Most telling first, for the "what they said" list.
SIGNAL_ORDER = ["payment_request", "credential_request", "secrecy", "urgency", "impersonation"]


class CallRecord:
    """Collects the facts for the summary while a call runs."""

    def __init__(self):
        self.t = 0.0  # latest call time heard
        self.red_at = None  # call time the warning first fired
        self.phrases = {}  # lowercased phrase -> (signal, phrase as said), clear signs only
        self.reason = ""
        self.action = ""
        self._reason_level = -1

    def heard_until(self, t: float):
        self.t = max(self.t, t)

    def note_rules(self, result: dict):
        for m in result["matches"]:
            # Weak hints ("Grandma", a dollar amount) are normal on real calls; only quote clear signs.
            if m["strength"] == 1.0:
                self.phrases.setdefault(m["phrase"].strip().lower(), (m["signal"], m["phrase"].strip()))

    def _top_phrases(self) -> list[str]:
        ranked = sorted(self.phrases.values(), key=lambda sp: SIGNAL_ORDER.index(sp[0]))
        return [phrase for _, phrase in ranked[:MAX_PHRASES]]

    def note_score(self, event: dict, alert: dict | None):
        if alert and self.red_at is None:
            self.red_at = round(self.t, 1)
        # Keep the reason from the most serious moment of the call.
        level = LEVELS.index(event["level"])
        if event["reason"] and level >= self._reason_level:
            self._reason_level = level
            self.reason = event["reason"]
            self.action = event["suggested_action"] or self.action

    def summary(self, scores) -> dict:
        flagged = scores.worst_level != "green"
        return {
            "type": "summary",
            "verdict": scores.worst_level,  # green | yellow | red
            "duration": math.ceil(self.t),
            "red_at": self.red_at,
            "signals": sorted(scores.signals_seen),
            "phrases": self._top_phrases() if flagged else [],
            "reason": self.reason if flagged else "",
            "suggested_action": self.action if flagged else "",
        }
