"""Scam Shield backend: FastAPI app with one WebSocket endpoint for a call session.

Everything runs locally. This file only routes messages; audio, STT and scoring
live in their own modules.
"""

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
            data = await ws.receive_json()

            if data.get("type") == "start":
                mode = data.get("mode", "demo")
                sample = data.get("sample")
                await ws.send_json({"type": "status", "state": "started", "mode": mode, "sample": sample})
            elif data.get("type") == "stop":
                await ws.send_json({"type": "status", "state": "stopped"})
    except WebSocketDisconnect:
        pass
