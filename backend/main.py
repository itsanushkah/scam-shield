"""Scam Shield backend: FastAPI app with one WebSocket endpoint for a call session.

Everything runs locally. This file only routes messages; audio, STT and scoring
live in their own modules.
"""

import asyncio
import contextlib
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

import audio

app = FastAPI(title="Scam Shield")


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
    await ws.send_json({"type": "status", "stt": "idle", "llm": "idle", "offline": True})
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
    """Stream a demo WAV at real-time speed. Each chunk will feed STT in a later part."""
    async for t_start, t_end, _chunk in audio.stream_chunks(samples):
        # Dev-only timing event until transcription replaces it.
        await ws.send_json({"type": "chunk", "t_start": t_start, "t_end": t_end})
    await ws.send_json({"type": "status", "state": "ended"})


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
