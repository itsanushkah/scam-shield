"""Speech-to-text with faster-whisper, run locally on CPU.

Chunks from audio.stream_chunks overlap by OVERLAP_S. A Transcriber remembers
where the last emitted word ended, so words in the overlap are only emitted
once. Words touching the end of a chunk may be cut off mid-word, so they are
left for the next chunk, which hears them whole.

base.en is used rather than small.en: on 3 s chunks it was as accurate
(5.1% vs 5.6% WER on the hero call) and ~4x faster (0.46 s vs 1.74 s per chunk,
with small.en spiking to 7 s).
"""

import numpy as np
from faster_whisper import WhisperModel

MODEL_NAME = "base.en"
SILENCE_RMS = 0.003  # chunks quieter than this are skipped (Whisper invents text on silence)
EDGE_S = 0.15  # words ending this close to a chunk's end wait for the next chunk
SLACK_S = 0.05  # timestamp jitter allowed when comparing against the last word

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

    def feed(self, chunk: np.ndarray, t_start: float, t_end: float, is_last: bool) -> list[dict]:
        """Return the new words in this chunk as [{"word", "start", "end"}] in call time."""
        if np.sqrt(np.mean(chunk**2)) < SILENCE_RMS:
            return []

        segments, _ = load_model().transcribe(
            chunk,
            language="en",
            beam_size=1,
            temperature=0.0,  # no retries at higher temperatures: those caused 13 s spikes
            max_new_tokens=64,  # a 3 s chunk is ~15 words; stops runaway repetition
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
                    return words
                words.append({"word": w.word, "start": start, "end": end})
                self.cursor = end
        return words
