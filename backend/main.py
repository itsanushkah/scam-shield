"""Scam Shield backend: FastAPI app with one WebSocket endpoint for a call session.

Everything runs locally. This file only routes messages; audio, STT and scoring
live in their own modules.
"""

import asyncio
import contextlib
import json

import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

import audio
import fusion
import llm
import rules
import stt
from summary import CallRecord

WINDOW_S = 60  # score the last minute of the call


@contextlib.asynccontextmanager
async def lifespan(app):
    # Load Whisper and the LLM before the first call, so the first chunk isn't slow.
    await asyncio.to_thread(stt.load_model)
    async with httpx.AsyncClient() as client:
        app.state.ollama = client
        app.state.llm_ok = await llm.warm_up(client)
        yield


app = FastAPI(title="Scam Shield", lifespan=lifespan)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/samples")
def samples():
    """Demo calls the frontend can pick from."""
    return {"samples": audio.list_samples()}


@app.get("/samples/{name}")
def sample_audio(name: str):
    """The WAV itself, so the browser can play a recording out loud while it's analysed."""
    try:
        return FileResponse(audio.sample_path(name), media_type="audio/wav")
    except FileNotFoundError:
        raise HTTPException(404, "no such sample")


@app.websocket("/ws/call")
async def call_session(ws: WebSocket):
    await ws.accept()
    llm_state = "ok" if ws.app.state.llm_ok else "down"
    await ws.send_json({"type": "status", "stt": "ok", "llm": llm_state, "offline": True})
    stream = None  # background task running the current call
    mic = None  # live mode: queue of PCM16 frames from the browser

    try:
        while True:
            msg = await ws.receive()

            if msg["type"] == "websocket.disconnect":
                break

            # Binary frames are live-mode mic audio: 16 kHz mono PCM16.
            if msg.get("bytes") is not None:
                if mic is not None:
                    mic.put_nowait(msg["bytes"])
                continue

            data = _parse(msg.get("text"))
            if data is None:
                await ws.send_json({"type": "error", "message": "expected JSON"})
                continue

            if data.get("type") == "start":
                mode = data.get("mode", "demo")
                sample = data.get("sample") if mode == "demo" else None
                if mode == "live":
                    await _cancel(stream)
                    mic = asyncio.Queue()
                    stream = asyncio.create_task(_run_call(ws, audio.live_chunks(mic)))
                elif mode == "demo":
                    try:
                        samples = audio.load_wav(audio.sample_path(sample or ""))
                    except (FileNotFoundError, ValueError) as e:
                        await ws.send_json({"type": "error", "message": str(e)})
                        continue
                    await _cancel(stream)
                    mic = None
                    duration = len(samples) / audio.SAMPLE_RATE
                    stream = asyncio.create_task(_run_call(ws, audio.stream_chunks(samples), duration))
                else:
                    await ws.send_json({"type": "error", "message": f"unknown mode: {mode}"})
                    continue
                await ws.send_json({"type": "status", "state": "started", "mode": mode, "sample": sample})
            elif data.get("type") == "stop":
                await _cancel(stream)
                stream, mic = None, None
                await ws.send_json({"type": "status", "state": "stopped"})
            else:
                await ws.send_json({"type": "error", "message": f"unknown type: {data.get('type')}"})
    except WebSocketDisconnect:
        pass
    finally:
        await _cancel(stream)


async def _run_call(ws: WebSocket, chunks, duration: float | None = None):
    """Run one call: transcribe each audio chunk as it arrives, score it, and send events.

    chunks is audio.stream_chunks (demo WAV, real-time paced) or audio.live_chunks (mic).
    duration is known for demo files only, so the final chunk can keep its last word.
    """
    transcriber = stt.Transcriber()
    heard = []  # every word so far, with call-time stamps
    scores = fusion.Fusion()
    record = CallRecord()  # for the end-of-call summary
    llm_task = None

    try:
        async for t_start, t_end, chunk in chunks:
            is_last = duration is not None and t_end >= duration
            # Whisper blocks for ~0.5 s, so keep it off the event loop.
            words = await asyncio.to_thread(transcriber.feed, chunk, t_start, t_end, is_last)
            record.heard_until(t_end)
            if not words:
                continue

            text = "".join(w["word"] for w in words).strip()
            await ws.send_json({"type": "transcript", "text": text, "t": round(words[0]["start"], 1)})

            heard.extend(words)
            recent = "".join(w["word"] for w in heard if w["end"] >= t_end - WINDOW_S)
            result = rules.score(recent)
            record.note_rules(result)
            await _send_score(ws, record, *scores.update(rules=result))

            # One LLM call at a time. If it's still busy, skip this chunk rather than queue it.
            if llm_task is None or llm_task.done():
                llm_task = asyncio.create_task(_ask_llm(ws, recent, scores, record))

        if llm_task:
            await llm_task  # let the last answer land before the call ends
    finally:
        await _cancel(llm_task)  # stopped mid-call: don't leave the LLM request running
        # Sent on a normal end and on stop/hang up. The socket may already be gone.
        with contextlib.suppress(Exception):
            await ws.send_json(record.summary(scores))

    await ws.send_json({"type": "status", "state": "ended"})


async def _ask_llm(ws: WebSocket, transcript: str, scores: fusion.Fusion, record: CallRecord):
    try:
        result = await llm.score(transcript, ws.app.state.ollama)
    except (httpx.HTTPError, ValueError):
        # Ollama down, too slow, or a bad answer: keep going on rules alone.
        await ws.send_json({"type": "status", "llm": "down"})
        return
    # Tell the UI the AI check is back, in case an earlier call timed out.
    await ws.send_json({"type": "status", "llm": "ok"})
    await _send_score(ws, record, *scores.update(llm=result))


async def _send_score(ws: WebSocket, record: CallRecord, event: dict, alert: dict | None):
    record.note_score(event, alert)
    # Keep adding to "what the caller is doing" for the rest of the call, even after it latches red.
    event["evidence"] = record.evidence(event["signals"]) if event["level"] != "green" else []
    await ws.send_json(event)
    if alert:
        await ws.send_json(alert)


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
