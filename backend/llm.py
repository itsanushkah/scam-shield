"""LLM scorer: a small local model in Ollama reads the recent transcript and returns JSON.

Ollama runs on this laptop (localhost:11434), so nothing leaves the device. The
few-shot examples are new text, never taken from eval/.
"""

import json
import re

import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:3b"
TIMEOUT_S = 15

SIGNALS = ["urgency", "secrecy", "payment_request", "impersonation", "credential_request"]

SCHEMA = {
    "type": "object",
    "properties": {
        "risk": {"type": "integer", "minimum": 0, "maximum": 100},
        # maxItems stops a repetition loop the 3B model fell into ("payment_request", "payment_request", ...).
        "signals": {"type": "array", "items": {"type": "string", "enum": SIGNALS}, "maxItems": 5, "uniqueItems": True},
        "reason": {"type": "string"},
        "suggested_action": {"type": "string"},
    },
    "required": ["risk", "signals", "reason", "suggested_action"],
}

SYSTEM = """You protect an older adult during a phone call. You get the recent transcript of both sides, without speaker names.
Rate 0-100 how likely the caller is a scammer.
Scam signs: rushing them, asking for secrecy or to stay on the line, payment by gift card, wire, crypto or cash, pretending to be family, a bank, the government or police, asking for codes, PINs or passwords.
A real family member chatting, or a real bank that does NOT ask for money or codes, is low risk. Judge what the caller wants, not single words.
reason: one plain sentence a grandparent would understand, at most 20 words.
suggested_action: one instruction of at most 12 words, or "" if the call looks fine.
Reply with JSON only."""

# (transcript, answer) pairs. New text, not from eval/.
EXAMPLES = [
    (
        "This is Deputy Harris with the county court. You missed jury duty and there's a warrant for your arrest. "
        "To clear it today you need to pay the fine with gift cards. Stay on the line and don't call anyone, or the deputies will come to your house.",
        {
            "risk": 96,
            "signals": ["impersonation", "urgency", "payment_request", "secrecy"],
            "reason": "He says he's from the court and wants the fine in gift cards. Courts never do that.",
            "suggested_action": "Hang up. Courts and police never ask for gift cards.",
        },
    ),
    (
        "Hi Grandpa, it's me, Lily! Mom said you had a cold, so I wanted to check on you. "
        "Do you want me to bring some soup over tomorrow after school? Okay, love you, feel better!",
        {
            "risk": 4,
            "signals": [],
            "reason": "Your granddaughter is checking on you and isn't asking for anything.",
            "suggested_action": "",
        },
    ),
    (
        "Hello, this is Sam from the fraud team at Lakeside Credit Union. We stopped a suspicious charge on your card and are mailing you a new one. "
        "We will never ask for your PIN or a code. If you want to check, hang up and call the number on the back of your card.",
        {
            "risk": 10,
            "signals": [],
            "reason": "This sounds like your real bank. They aren't asking for money or codes.",
            "suggested_action": "",
        },
    ),
]


def _messages(transcript: str) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM}]
    for text, answer in EXAMPLES:
        msgs.append({"role": "user", "content": f"Transcript: {text}"})
        msgs.append({"role": "assistant", "content": json.dumps(answer)})
    msgs.append({"role": "user", "content": f"Transcript: {transcript}"})
    return msgs


async def score(transcript: str, client: httpx.AsyncClient, model: str = MODEL) -> dict:
    """Ask the local model about this transcript. Raises httpx.HTTPError if Ollama is down,
    ValueError if the answer isn't valid JSON."""
    resp = await client.post(
        OLLAMA_URL,
        json={
            "model": model,
            "messages": _messages(transcript),
            "format": SCHEMA,
            "stream": False,
            "keep_alive": -1,  # keep the model loaded for the whole demo
            "options": {"temperature": 0, "num_predict": 200},
        },
        timeout=TIMEOUT_S,
    )
    resp.raise_for_status()
    result = _parse(resp.json()["message"]["content"])

    result["risk"] = max(0, min(100, int(result.get("risk", 0))))
    # Small models sometimes list signals on a call they rate safe. Trust the risk number.
    result["signals"] = [s for s in result.get("signals", []) if s in SIGNALS] if result["risk"] >= 40 else []
    return result


def _parse(content: str) -> dict:
    """Parse the model's JSON. If it was cut off, keep the risk (always the first field)."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r'"risk"\s*:\s*(\d+)', content)
        if not m:
            raise ValueError("no usable answer from the model")
        return {"risk": int(m.group(1)), "signals": [], "reason": "", "suggested_action": ""}


async def warm_up(client: httpx.AsyncClient) -> bool:
    """Load the model and cache the prompt prefix. Returns False if Ollama isn't reachable."""
    try:
        await score("Hello?", client)
        return True
    except (httpx.HTTPError, ValueError, KeyError):
        return False
