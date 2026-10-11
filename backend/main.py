"""Scam Shield backend: FastAPI app with one WebSocket endpoint for a call session.

Everything runs locally. This file only routes messages; audio, STT and scoring
live in their own modules.
"""

import asyncio
import contextlib
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

import audio
import rules
import stt

WINDOW_S = 60  # score the last minute of the call


@contextlib.asynccontextmanager
async def lifespan(_app):
    # Load Whisper before the first call, so the first chunk isn't slow.
    await asyncio.to_thread(stt.load_model)
    yield


app = FastAPI(title="Scam Shield", lifespan=lifespan)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/samples")
def samples():
    """Demo calls the frontend can pick from."""
    return {"samples": audio.list_samples()}


@app.websocket("/ws/call")
async def call_session(ws: WebSocket):
    await ws.accept()
    await ws.send_json({"type": "status", "stt": "ok", "llm": "idle", "offline": True})
    stream = None  # background task feeding audio for the current call

    try:
        while True:
            msg = await ws.receive()

            if msg["type"] == "websocket.disconnect":
                break

            # Binary frames are live-mode PCM audio. Handled in a later part.
            if msg.get("bytes") is not None:
                continue

            data = _parse(msg.get("text"))
            if data is None:
                await ws.send_json({"type": "error", "message": "expected JSON"})
                continue

            if data.get("type") == "start":
                mode = data.get("mode", "demo")
                sample = data.get("sample")
                if mode != "demo":
                    await ws.send_json({"type": "error", "message": "live mode not implemented yet"})
                    continue
                try:
                    samples = audio.load_wav(audio.sample_path(sample or ""))
                except (FileNotFoundError, ValueError) as e:
                    await ws.send_json({"type": "error", "message": str(e)})
                    continue
                await _cancel(stream)
                stream = asyncio.create_task(_run_demo(ws, samples))
                await ws.send_json({"type": "status", "state": "started", "mode": mode, "sample": sample})
            elif data.get("type") == "stop":
                await _cancel(stream)
                stream = None
                await ws.send_json({"type": "status", "state": "stopped"})
            else:
                await ws.send_json({"type": "error", "message": f"unknown type: {data.get('type')}"})
    except WebSocketDisconnect:
        pass
    finally:
        await _cancel(stream)


async def _run_demo(ws: WebSocket, samples):
    """Stream a demo WAV at real-time speed and send what's said as it's heard."""
    transcriber = stt.Transcriber()
    duration = len(samples) / audio.SAMPLE_RATE
    heard = []  # every word so far, with call-time stamps

    async for t_start, t_end, chunk in audio.stream_chunks(samples):
        # Whisper blocks for ~0.5 s, so keep it off the event loop.
        words = await asyncio.to_thread(transcriber.feed, chunk, t_start, t_end, t_end >= duration)
        if not words:
            continue

        text = "".join(w["word"] for w in words).strip()
        await ws.send_json({"type": "transcript", "text": text, "t": round(words[0]["start"], 1)})

        heard.extend(words)
        recent = "".join(w["word"] for w in heard if w["end"] >= t_end - WINDOW_S)
        result = rules.score(recent)
        await ws.send_json({
            "type": "score",
            "risk": result["risk"],
            "level": _level(result["risk"]),
            "signals": result["signals"],
            "reason": result["reason"],
            "suggested_action": result["suggested_action"],
        })

    await ws.send_json({"type": "status", "state": "ended"})


def _level(risk: int) -> str:
    # Thresholds from CLAUDE.md. Fusion (smoothing + latch) replaces this in a later part.
    return "red" if risk > 70 else "yellow" if risk >= 40 else "green"


async def _cancel(task):
    if task and not task.done():
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def _parse(text):
    try:
        return json.loads(text) if text else None
    except json.JSONDecodeError:
        return None
