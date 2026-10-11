// Runs on the audio thread. Turns mic samples (float, at the context's 16 kHz rate)
// into 100 ms frames of 16-bit PCM and posts them to the page.
const FRAME = 1600 // 100 ms at 16 kHz

class PcmCapture extends AudioWorkletProcessor {
  constructor() {
    super()
    this.frame = new Int16Array(FRAME)
    this.filled = 0
  }

  process(inputs) {
    const samples = inputs[0]?.[0]
    if (!samples) return true

    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]))
      this.frame[this.filled++] = s < 0 ? s * 0x8000 : s * 0x7fff
      if (this.filled === FRAME) {
        this.port.postMessage(this.frame.buffer, [this.frame.buffer])
        this.frame = new Int16Array(FRAME)
        this.filled = 0
      }
    }
    return true
  }
}

registerProcessor('pcm-capture', PcmCapture)
