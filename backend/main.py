"""Scam Shield backend: FastAPI app with one WebSocket endpoint for a call session.

Everything runs locally. This file only routes messages; audio, STT and scoring
live in their own modules.
"""

import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="Scam Shield")


@app.get("/health")
def health():
    return {"ok": True}


@app.websocket("/ws/call")
async def call_session(ws: WebSocket):
    await ws.accept()
    await ws.send_json({"type": "status", "stt": "idle", "llm": "idle", "offline": True})

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
                await ws.send_json({"type": "status", "state": "started", "mode": mode, "sample": sample})
            elif data.get("type") == "stop":
                await ws.send_json({"type": "status", "state": "stopped"})
            else:
                await ws.send_json({"type": "error", "message": f"unknown type: {data.get('type')}"})
    except WebSocketDisconnect:
        pass


def _parse(text):
    try:
        return json.loads(text) if text else None
    except json.JSONDecodeError:
        return None
