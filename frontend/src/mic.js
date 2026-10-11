// Live mic capture: 16 kHz mono PCM16 in 100 ms frames, for the backend's live mode.
// Audio only goes to our own backend on localhost.

export async function startMic(onFrame, onLevel) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      // Off, so a phone playing the scammer on speaker isn't filtered out as "echo" or "noise".
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: true,
    },
  })

  // Ask the browser to resample the mic to 16 kHz, which is what Whisper expects.
  const ctx = new AudioContext({ sampleRate: 16000 })
  await ctx.audioWorklet.addModule(new URL('./pcmWorklet.js', import.meta.url))

  const source = ctx.createMediaStreamSource(stream)
  const capture = new AudioWorkletNode(ctx, 'pcm-capture')
  // Connected to the output through a muted gain so the browser keeps it running, without playback.
  const mute = ctx.createGain()
  mute.gain.value = 0

  capture.port.onmessage = (e) => {
    onFrame(e.data)
    if (onLevel) onLevel(rms(new Int16Array(e.data)))
  }
  source.connect(capture).connect(mute).connect(ctx.destination)

  return () => {
    capture.port.onmessage = null
    source.disconnect()
    stream.getTracks().forEach((t) => t.stop())
    ctx.close()
  }
}

// 0-1 loudness of a frame, for the mic level bar.
function rms(frame) {
  let sum = 0
  for (const s of frame) sum += (s / 32768) ** 2
  return Math.min(1, Math.sqrt(sum / frame.length) * 4)
}
