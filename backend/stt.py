"""Speech-to-text with faster-whisper, run locally on CPU.

Chunks from audio.stream_chunks overlap by OVERLAP_S. A Transcriber remembers
where the last emitted word ended, so words in the overlap are only emitted
once. Words touching the end of a chunk may be cut off mid-word, so they are
left for the next chunk, which hears them whole.

Each decode hears the last CONTEXT_S seconds, not just the 3 s chunk: more
context means fewer dropped or misheard words (4.2% -> 3.2% WER across the 7
demo calls) for ~0.15 s more per chunk.

base.en is used rather than small.en: on short windows it was as accurate and
several times faster (small.en couldn't keep up with real time on this CPU).
"""

import time

import numpy as np
from faster_whisper import WhisperModel

MODEL_NAME = "base.en"
CONTEXT_S = 6.0  # seconds of audio each decode hears
FAST_CONTEXT_S = 3.0  # used instead while decoding is falling behind
SLOW_DECODE_S = 1.5  # a decode slower than this means we're falling behind (chunks come every 2.5 s)
SILENCE_RMS = 0.003  # chunks quieter than this are skipped (Whisper invents text on silence)
EDGE_S = 0.15  # words ending this close to a chunk's end wait for the next chunk
SLACK_S = 0.05  # timestamp jitter allowed when comparing against the last word
REPEAT_WORDS = 3  # how many words back to look for a repeat across a chunk edge

_model = None


def load_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
        # Warm up with the same options as real chunks, so the VAD and word timing load now.
        list(_model.transcribe(np.zeros(16000, dtype=np.float32), language="en", vad_filter=True, word_timestamps=True)[0])
    return _model


class Transcriber:
    """Turns one call's overlapping chunks into a stream of new words."""

    def __init__(self):
        self.cursor = 0.0  # call time where the last emitted word ended
        self.tail = []  # last few emitted words, normalized, for catching repeats
        self.audio = np.zeros(0, dtype=np.float32)  # the last CONTEXT_S seconds heard
        self.audio_end = 0.0  # call time at the end of self.audio
        self.last_decode_s = 0.0

    def feed(self, chunk: np.ndarray, t_start: float, t_end: float, is_last: bool) -> list[dict]:
        """Return the new words in this chunk as [{"word", "start", "end"}] in call time."""
        self._remember(chunk, t_start, t_end)
        if np.sqrt(np.mean(chunk**2)) < SILENCE_RMS:
            return []

        # Decode the last CONTEXT_S seconds, but only words after the cursor are new.
        # If the laptop is struggling (low memory, LLM busy), drop to a shorter window to keep up.
        context = FAST_CONTEXT_S if self.last_decode_s > SLOW_DECODE_S else CONTEXT_S
        window = self.audio[-int(context * 16000) :]
        t_start = t_end - len(window) / 16000
        started = time.monotonic()

        segments, _ = load_model().transcribe(
            window,
            language="en",
            beam_size=1,
            temperature=0.0,  # no retries at higher temperatures: those caused 13 s spikes
            max_new_tokens=96,  # a 6 s window is ~30 words; stops runaway repetition
            vad_filter=True,
            word_timestamps=True,
            condition_on_previous_text=False,
        )

        words = []
        for seg in segments:
            for w in seg.words or []:
                start, end = t_start + w.start, t_start + w.end
                if start < self.cursor - SLACK_S:
                    continue
                if not is_last and end > t_end - EDGE_S:
                    break
                words.append({"word": w.word, "start": start, "end": end})
            else:
                continue
            break

        self.last_decode_s = time.monotonic() - started
        words = self._drop_repeat(words)
        if words:
            self.cursor = words[-1]["end"]
            self.tail = (self.tail + [_norm(w["word"]) for w in words])[-REPEAT_WORDS:]
        return words

    def _remember(self, chunk: np.ndarray, t_start: float, t_end: float):
        """Append the part of this chunk not heard before, keeping only the last CONTEXT_S."""
        new = chunk[max(0, round((self.audio_end - t_start) * 16000)) :]
        self.audio = np.concatenate([self.audio, new])[-int(CONTEXT_S * 16000) :]
        self.audio_end = t_end

    def _drop_repeat(self, words: list[dict]) -> list[dict]:
        """Timestamps are loose at chunk edges, so the start of a chunk can repeat the
        end of the last one ("Thanksgiving." then "giving."). Drop that repeat by text."""
        new = [_norm(w["word"]) for w in words]
        for k in range(min(REPEAT_WORDS, len(new), len(self.tail)), 0, -1):
            if new[:k] == self.tail[-k:]:
                return words[k:]
        if new and self.tail and len(new[0]) >= 3 and self.tail[-1].endswith(new[0]):
            return words[1:]
        return words


def _norm(word: str) -> str:
    return "".join(c for c in word.lower() if c.isalnum() or c == "'")
