import { useCallback, useEffect, useRef, useState } from 'react'

import { startMic } from './mic.js'

const RECONNECT_MS = 1000

// One WebSocket to the backend's /ws/call. Reconnects on its own, so the
// backend can be started (or restarted) after the page is open.
export function useCallSocket() {
  const wsRef = useRef(null)
  const [connected, setConnected] = useState(false)
  const [llmState, setLlmState] = useState(null) // ok | down
  const [callState, setCallState] = useState('idle') // idle | starting | started | stopped | ended
  const [transcript, setTranscript] = useState([])
  const [score, setScore] = useState(null)
  const [alert, setAlert] = useState(null) // set once, when the call first turns red
  const [summary, setSummary] = useState(null) // sent when the call ends
  const [error, setError] = useState(null)
  const [callNumber, setCallNumber] = useState(0)
  const [micLevel, setMicLevel] = useState(0) // 0-1, live mode only
  const stopMicRef = useRef(null)
  const playerRef = useRef(null) // recording mode: the same file, played out loud

  const stopMic = useCallback(() => {
    stopMicRef.current?.()
    stopMicRef.current = null
    setMicLevel(0)
  }, [])

  const stopPlayer = useCallback(() => {
    playerRef.current?.pause()
    playerRef.current = null
  }, [])

  useEffect(() => {
    let closedByUs = false
    let retry

    function connect() {
      const ws = new WebSocket(`ws://${location.host}/ws/call`)
      wsRef.current = ws

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)
        if (msg.type === 'status') {
          if (msg.state) setCallState(msg.state)
          if (msg.state === 'stopped') stopPlayer()
          if (msg.state === 'stopped' || msg.state === 'ended') stopMic()
          if (msg.stt) setConnected(true)
          if (msg.llm) setLlmState(msg.llm)
        } else if (msg.type === 'transcript') {
          setTranscript((lines) => [...lines, { text: msg.text, t: msg.t }])
        } else if (msg.type === 'score') {
          setScore(msg)
        } else if (msg.type === 'alert') {
          setAlert(msg)
        } else if (msg.type === 'summary') {
          setSummary(msg)
        } else if (msg.type === 'error') {
          setError(msg.message)
        }
      }

      ws.onclose = () => {
        stopMic()
        stopPlayer()
        setConnected(false)
        setCallState((s) => (s === 'started' ? 'stopped' : s))
        if (!closedByUs) retry = setTimeout(connect, RECONNECT_MS)
      }
    }

    connect()
    return () => {
      closedByUs = true
      clearTimeout(retry)
      wsRef.current?.close()
      stopMic()
      stopPlayer()
    }
  }, [stopMic, stopPlayer])

  const send = useCallback((msg) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(JSON.stringify(msg))
  }, [])

  // mode 'demo' plays a sample file on the backend; 'live' streams this computer's mic.
  const start = useCallback(
    async (sample, mode = 'demo') => {
      setError(null)
      setTranscript([])
      setScore(null)
      setAlert(null)
      setSummary(null)
      setCallNumber((n) => n + 1)
      setCallState('starting') // until the backend confirms; stops the old 'ended' showing
      stopMic()
      stopPlayer()

      if (mode === 'demo') {
        // Play the recording out loud while the backend analyses the same file, so people
        // watching hear the call. Started on the click, so the browser allows audio.
        playerRef.current = new Audio(`/samples/${encodeURIComponent(sample)}`)
        playerRef.current.play().catch((e) => setError(`Couldn't play audio: ${e.message}`))
        send({ type: 'start', mode: 'demo', sample })
        return
      }

      send({ type: 'start', mode: 'live' })
      try {
        stopMicRef.current = await startMic((frame) => {
          if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(frame)
        }, setMicLevel)
      } catch (e) {
        setError(`Microphone: ${e.message}`)
        send({ type: 'stop' })
      }
    },
    [send, stopMic, stopPlayer],
  )

  const stop = useCallback(() => {
    stopMic()
    stopPlayer()
    send({ type: 'stop' })
  }, [send, stopMic, stopPlayer])

  return { connected, llmState, callState, callNumber, transcript, score, alert, summary, error, micLevel, start, stop }
}
