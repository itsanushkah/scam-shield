"""Scam Shield backend: FastAPI app with one WebSocket endpoint for a call session.

Everything runs locally. This file only routes messages; audio, STT and scoring
live in their own modules.
"""

from fastapi import FastAPI

app = FastAPI(title="Scam Shield")


@app.get("/health")
def health():
    return {"ok": True}
