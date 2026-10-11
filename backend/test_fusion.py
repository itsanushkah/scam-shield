"""Checks for fusion. Run: python backend/test_fusion.py"""

from fusion import Fusion, level_for


def result(risk, reason="", action="", signals=()):
    return {"risk": risk, "reason": reason, "suggested_action": action, "signals": list(signals)}


def check_levels():
    assert [level_for(r) for r in (0, 39, 40, 70, 71, 100)] == ["green", "green", "yellow", "yellow", "red", "red"]
    print("ok  levels")


def check_strong_evidence_goes_red_at_once():
    f = Fusion()
    f.update(rules=result(25))
    event, alert = f.update(rules=result(90, "The caller wants gift cards.", "Hang up.", ["payment_request"]))
    assert event["level"] == "red" and alert is not None, event
    assert alert["reason"] == "The caller wants gift cards."
    print("ok  strong evidence goes red at once, with one alert")


def check_no_flicker_on_one_calm_score():
    f = Fusion()
    f.update(rules=result(55, "The caller is rushing you."))
    event, _ = f.update(rules=result(0))
    assert event["level"] == "yellow", f"one calm score shouldn't drop yellow to green: {event}"
    print("ok  one calm score doesn't flicker back to green")


def check_latch():
    f = Fusion()
    _, alert = f.update(rules=result(100, "The caller wants gift cards.", "Hang up."))
    assert alert
    for _ in range(10):
        event, again = f.update(rules=result(0, "Nothing unusual so far."), llm=result(2, "Seems fine."))
        assert event["level"] == "red" and event["risk"] == 100 and again is None
    assert event["reason"] == "The caller wants gift cards."
    print("ok  latched red stays red, keeps the red reason, alerts once")


def check_llm_alone_can_warn():
    # With no keywords to back it up, one LLM answer gives "be careful"; a second one confirms red.
    f = Fusion()
    f.update(rules=result(12, "Nothing unusual so far."))
    worried = result(85, "He wants you to move your savings to a 'safe' account.", "Hang up.")
    event, _ = f.update(llm=worried)
    assert event["level"] == "yellow" and "savings" in event["reason"], event
    event, alert = f.update(llm=worried)
    assert event["level"] == "red" and alert, event
    print("ok  LLM alone warns yellow, then red when it repeats, with its own reason")


def check_rules_reason_preferred():
    f = Fusion()
    f.update(rules=result(90, "The caller wants gift cards."))
    event, _ = f.update(llm=result(95, "Something feels off."))
    assert event["reason"] == "The caller wants gift cards.", event
    print("ok  concrete rule reason wins over a vaguer LLM one")


def check_summary_tracking():
    f = Fusion()
    f.update(rules=result(55, "The caller is rushing you.", signals=["urgency"]))
    f.update(rules=result(100, "The caller wants gift cards.", signals=["payment_request", "secrecy"]))
    f.update(rules=result(0))
    assert f.worst_level == "red" and f.signals_seen == {"urgency", "payment_request", "secrecy"}, (f.worst_level, f.signals_seen)
    print("ok  tracks worst level and every signal seen, for the summary")


def check_green_has_no_reason():
    f = Fusion()
    event, _ = f.update(rules=result(25, "The caller says they're from a bank."), llm=result(2))
    assert event["level"] == "green" and event["reason"] == "" and event["signals"] == []
    print("ok  green shows no reason or signals")


if __name__ == "__main__":
    check_levels()
    check_strong_evidence_goes_red_at_once()
    check_no_flicker_on_one_calm_score()
    check_latch()
    check_llm_alone_can_warn()
    check_rules_reason_preferred()
    check_green_has_no_reason()
    check_summary_tracking()
