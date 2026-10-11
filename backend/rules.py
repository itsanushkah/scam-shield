"""Rule scorer: weighted keyword categories over the rolling transcript.

Instant and explainable, and works even when the LLM is slow. The score comes
from how many categories are hit, not how many keywords, so one category alone
stays green and several together go red.

Tuned on the demo call scripts in samples/scripts and on eval/dev only, never on the test sets.
"""

import re

# Signal names match the LLM scorer's, so fusion can merge them.
# Each phrase is (regex, strength): 1.0 is a clear sign, 0.5 is weak on its own.
CATEGORIES = {
    "payment_request": [
        (r"gift ?cards?", 1.0),
        (r"itunes|google play|apple card|steam card", 1.0),
        (r"bitcoin|crypto(currency)?|bitcoin atm", 1.0),
        (r"\bwire\b|wire transfer|western union|moneygram|zelle|venmo|cash app", 1.0),
        (r"bail money|\bbail\b", 1.0),
        (r"scratch off the back|read me the numbers", 1.0),
        (r"cashier'?s check|money order|prepaid (debit )?card", 1.0),
        # Moving savings to a "safe" account, or paying into an escrow/new account.
        (r"(safe|secure|protected|holding|escrow) account|transfer (the|your) (full |entire |whole )?balance", 1.0),
        (r"(switched|changed|new) (banks?|account|bank details|payment details)", 0.5),
        # Someone coming to the house (or the bank) to collect cash.
        (r"(courier|driver|deputy|agent|someone|runner)\b.{0,40}\b(pick up|collect) (the |your )?(cash|money|payment|check|envelope)", 1.0),
        (r"(courier|deputy|agent|runner)\b.{0,40}\b(pick (it |them )?up|collect (it|them))", 1.0),
        (r"withdraw\b.{0,25}\bcash", 1.0),
        (r"take out .{0,20}cash", 0.5),
        (r"(filing|processing|release|customs|clearance|unlock) fee", 1.0),
        (r"\bbond (of|today|money)\b|pay (the|a|her|his) bond", 1.0),
        (r"guaranteed (returns?|profit)|returns? of \d+ ?(percent|%)|risk[- ]free", 0.5),
        # Whisper writes spoken amounts as digits ("two thousand dollars" -> "$2,000").
        (r"\$\s?\d[\d,]*|\b\d[\d,]* dollars|\b(hundred|thousand) dollars", 0.5),
    ],
    "urgency": [
        (r"right now|immediately|right away|as soon as possible", 1.0),
        (r"before it'?s too late|within the hour|in the next (minute|hour)|hurry", 1.0),
        (r"emergency|urgent", 0.5),
        (r"act now|move now|window closes", 1.0),
        (r"last chance|until the \w+ arrives", 0.5),
        (r"(by|before) (tomorrow|tonight|end of (the )?day)|late fees?|or (else|the funds)", 0.5),
    ],
    "secrecy": [
        (r"don'?t tell|do not tell|do not speak to anyone|don'?t speak to anyone", 1.0),
        (r"keep (this|it) (between us|a secret|quiet)|confidential", 1.0),
        (r"don'?t hang up|do not hang up|stay on the line|if you hang up", 1.0),
        (r"don'?t call (the|your) (bank|branch|police)", 1.0),
        (r"(keep|handle|leave|just) (it |this |that )?between us|between (you and me|us) for now|gag order|(staff|employees|teller)s? (may|might|could) be involved", 1.0),
        (r"(cannot|can'?t|not to|don'?t|shouldn'?t) (tell|discuss|mention)\b.{0,25}\b(anyone|family|bank|branch|relatives)", 1.0),
        (r"settle it quietly|keep your phone with you", 0.5),
    ],
    "impersonation": [
        (r"\birs\b|internal revenue|social security (administration|office)", 1.0),
        (r"\bwarrant\b|arrested|under arrest|police|officer|sheriff", 1.0),
        (r"(fraud|security) (department|team)|from (your|the) bank|\bbank\b", 1.0),
        (r"microsoft|apple support|tech(nical)? support|medicare", 1.0),
        (r"\bgrand(ma|pa|mother|father)\b|it'?s me\b", 0.5),
        (r"account security|security office", 1.0),
        (r"customer care team", 0.5),
        (r"\b(sergeant|deputy|detective|public defender)\b|summons|court (order|requirement|fees?|date)", 1.0),
        (r"\bcourt\b|\bjudge\b|citation", 0.5),
        (r"fraud recovery|recovered your (funds|money)", 1.0),
        (r"unusual (traffic|activity)|(computer|network|device) (is|has been) (hacked|infected|compromised)|virus (on|in) your", 0.5),
    ],
    "credential_request": [
        (r"read me (the|that|your) code|verification code|security code|the code we (sent|texted)", 1.0),
        (r"\bpin\b|password|account number|routing number", 1.0),
        (r"social security number|\bssn\b|card number|medicare number", 1.0),
        # Reading back a code from a text, or a remote-access number.
        (r"read (me )?(the|those|that) (\w+ )?(numbers?|digits?) (in|from|on)", 1.0),
        (r"read (it|that|them) (back )?to me", 0.5),
        # Remote-access apps let a scammer control the computer.
        (r"remote (access|desktop|control)|anydesk|teamviewer|quick ?assist|accept the connection", 1.0),
        (r"install (a|an|the|this) (small |quick |free )?(app|program|software)", 0.5),
        (r"log ?in to your (bank|account) (so|while)", 1.0),
    ],
}

# A request phrase right after "never ask" (etc.) is the opposite of a scam:
# "we will never ask you for your PIN". Only checked for these categories.
NEGATABLE = {"payment_request", "credential_request"}
# Whisper scatters full stops mid-sentence ("never ask you for your pin. your password"),
# so the check runs across them, limited to the next ~60 characters.
NEGATION = re.compile(r"\b(never|not|won'?t|don'?t|doesn'?t) (ask|need|request)\b[^?!]{0,60}$")

# Score by effective number of categories hit (strengths summed), interpolated.
SCORE_BY_CATEGORIES = [0, 25, 55, 80, 92, 100]
ASK_BONUS = 10  # a concrete ask for money or a code, alongside another signal
ASK_PAIR_FLOOR = 85  # clear ask + another clear category: high enough to alert on the next line

# Short phrases for the reason sentence, most important first. Only the top two are used.
REASONS = {
    "payment_request": "wants money by gift card, wire or Bitcoin",
    "credential_request": "is asking for a code or PIN",
    "secrecy": "wants you to keep it secret",
    "urgency": "is rushing you",
    "impersonation": "says they're family, a bank, police or the government",
}

_compiled = {cat: [(re.compile(p, re.I), s) for p, s in phrases] for cat, phrases in CATEGORIES.items()}


def score(text: str) -> dict:
    """Score a transcript. Returns risk 0-100, signals, matched phrases and a plain-English reason."""
    strengths = {}
    matches = []

    for cat, phrases in _compiled.items():
        for pattern, strength in phrases:
            for m in pattern.finditer(text):
                if cat in NEGATABLE and NEGATION.search(text[max(0, m.start() - 80) : m.start()]):
                    continue
                matches.append({"signal": cat, "phrase": m.group(0), "strength": strength})
                strengths[cat] = max(strengths.get(cat, 0), strength)

    n = sum(strengths.values())
    risk = _interp(n)
    asks = strengths.get("payment_request", 0) == 1.0 or strengths.get("credential_request", 0) == 1.0
    if asks and n >= 2:
        risk += ASK_BONUS
    # A clear ask for money or a code, plus one other clear sign (a claimed authority,
    # secrecy, or a second kind of ask), is the core of almost every phone scam: go red.
    # Urgency alone doesn't count as the partner: "got him a gift card, call me right now"
    # is ordinary family talk.
    strong = sum(1 for c, v in strengths.items() if v == 1.0 and c != "urgency")
    if asks and strong >= 2:
        risk = max(risk, ASK_PAIR_FLOOR)
    risk = min(100, round(risk))

    signals = sorted(strengths, key=lambda c: -strengths[c])
    return {
        "risk": risk,
        "signals": signals,
        "matches": matches,
        "reason": _reason(signals, strengths),
        "suggested_action": _action(strengths, matches),
    }


def _interp(n: float) -> float:
    lo = min(int(n), len(SCORE_BY_CATEGORIES) - 1)
    hi = min(lo + 1, len(SCORE_BY_CATEGORIES) - 1)
    return SCORE_BY_CATEGORIES[lo] + (SCORE_BY_CATEGORIES[hi] - SCORE_BY_CATEGORIES[lo]) * (n - lo)


def _reason(signals: list[str], strengths: dict) -> str:
    strong = [s for s in REASONS if strengths.get(s) == 1.0][:2]
    if not strong:
        return "Nothing unusual so far."
    return "The caller " + " and ".join(REASONS[s] for s in strong) + "."


GOVERNMENT = re.compile(r"irs|internal revenue|social security|warrant|arrest|police|officer|sheriff|medicare", re.I)
FAMILY = re.compile(r"grand(ma|pa|mother|father)|it'?s me", re.I)


def _action(strengths: dict, matches: list[dict]) -> str:
    """One short instruction, picked from what the caller is asking for and who they claim to be."""
    if not any(v == 1.0 for v in strengths.values()):
        return ""
    claimed = " ".join(m["phrase"] for m in matches if m["signal"] == "impersonation")

    if strengths.get("credential_request") == 1.0:
        return "Don't share any codes. Hang up and call your bank using the number on your card."
    if strengths.get("payment_request") == 1.0:
        # Family first: the grandson scam mentions police too, but the caller claims to be family.
        if FAMILY.search(claimed):
            return "Don't send money. Hang up and call your family member on their usual number."
        if GOVERNMENT.search(claimed):
            return "Hang up. The IRS and police never ask for gift cards or Bitcoin."
        return "Don't send money or buy gift cards. Hang up and call someone you trust."
    return "Be careful. If unsure, hang up and call back on a number you know."
