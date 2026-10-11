"""Audio input: load demo WAVs and cut audio into overlapping chunks for STT.

Demo mode streams a WAV from samples/ at real-time speed, so the rest of the
pipeline sees it exactly as if the call were happening live.
"""

import asyncio
import time
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000
CHUNK_S = 3.0
OVERLAP_S = 0.5

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


def list_samples() -> list[str]:
    return sorted(p.name for p in SAMPLES_DIR.glob("*.wav"))


def sample_path(name: str) -> Path:
    """Resolve a sample name to a file in samples/, rejecting anything outside it."""
    path = (SAMPLES_DIR / name).resolve()
    if path.parent != SAMPLES_DIR or path.suffix != ".wav" or not path.is_file():
        raise FileNotFoundError(f"no such sample: {name}")
    return path


def load_wav(path: Path) -> np.ndarray:
    """Read a 16 kHz mono PCM16 WAV as float32 in [-1, 1]."""
    with wave.open(str(path), "rb") as w:
        if w.getframerate() != SAMPLE_RATE or w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError(f"{path.name}: expected 16 kHz mono PCM16")
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return pcm.astype(np.float32) / 32768.0


async def stream_chunks(audio: np.ndarray, chunk_s: float = CHUNK_S, overlap_s: float = OVERLAP_S, realtime: bool = True):
    """Yield (t_start, t_end, chunk) windows, each overlapping the previous by overlap_s.

    With realtime=True, a chunk is only yielded once wall-clock time since the
    start has reached its end, the same moment it would exist on a live call.
    """
    chunk = int(chunk_s * SAMPLE_RATE)
    step = int((chunk_s - overlap_s) * SAMPLE_RATE)
    started = time.monotonic()

    start = 0
    while start < len(audio):
        end = min(start + chunk, len(audio))
        if realtime:
            wait = end / SAMPLE_RATE - (time.monotonic() - started)
            if wait > 0:
                await asyncio.sleep(wait)
        yield start / SAMPLE_RATE, end / SAMPLE_RATE, audio[start:end]
        if end == len(audio):
            break
        start += step


async def live_chunks(queue: "asyncio.Queue[bytes | None]", chunk_s: float = CHUNK_S, overlap_s: float = OVERLAP_S):
    """Like stream_chunks, but for audio arriving live as PCM16 frames on a queue.

    Yields each window as soon as enough audio has arrived. A None on the queue
    means the caller stopped; whatever is left is yielded as a final chunk.
    """
    chunk = int(chunk_s * SAMPLE_RATE)
    step = int((chunk_s - overlap_s) * SAMPLE_RATE)
    buf = np.zeros(0, dtype=np.float32)
    offset = 0  # call-time sample index of buf[0]

    while True:
        frame = await queue.get()
        if frame is None:
            if len(buf):
                yield offset / SAMPLE_RATE, (offset + len(buf)) / SAMPLE_RATE, buf
            return

        pcm = np.frombuffer(frame[: len(frame) // 2 * 2], dtype=np.int16)
        buf = np.concatenate([buf, pcm.astype(np.float32) / 32768.0])

        while len(buf) >= chunk:
            yield offset / SAMPLE_RATE, (offset + chunk) / SAMPLE_RATE, buf[:chunk]
            buf = buf[step:]
            offset += step
