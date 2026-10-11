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
  const [error, setError] = useState(null)
  const [callNumber, setCallNumber] = useState(0)
  const [micLevel, setMicLevel] = useState(0) // 0-1, live mode only
  const stopMicRef = useRef(null)

  const stopMic = useCallback(() => {
    stopMicRef.current?.()
    stopMicRef.current = null
    setMicLevel(0)
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
          if (msg.state === 'stopped' || msg.state === 'ended') stopMic()
          if (msg.stt) setConnected(true)
          if (msg.llm) setLlmState(msg.llm)
        } else if (msg.type === 'transcript') {
          setTranscript((lines) => [...lines, { text: msg.text, t: msg.t }])
        } else if (msg.type === 'score') {
          setScore(msg)
        } else if (msg.type === 'alert') {
          setAlert(msg)
        } else if (msg.type === 'error') {
          setError(msg.message)
        }
      }

      ws.onclose = () => {
        stopMic()
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
    }
  }, [stopMic])

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
      setCallNumber((n) => n + 1)
      setCallState('starting') // until the backend confirms; stops the old 'ended' showing
      stopMic()

      if (mode === 'demo') {
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
    [send, stopMic],
  )

  const stop = useCallback(() => {
    stopMic()
    send({ type: 'stop' })
  }, [send, stopMic])

  return { connected, llmState, callState, callNumber, transcript, score, alert, error, micLevel, start, stop }
}
