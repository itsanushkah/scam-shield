import { useCallback, useEffect, useRef, useState } from 'react'

const RECONNECT_MS = 1000

// One WebSocket to the backend's /ws/call. Reconnects on its own, so the
// backend can be started (or restarted) after the page is open.
export function useCallSocket() {
  const wsRef = useRef(null)
  const [connected, setConnected] = useState(false)
  const [llmState, setLlmState] = useState(null) // ok | down
  const [callState, setCallState] = useState('idle') // idle | started | stopped | ended
  const [transcript, setTranscript] = useState([])
  const [score, setScore] = useState(null)
  const [error, setError] = useState(null)
  const [callNumber, setCallNumber] = useState(0)

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
          if (msg.stt) setConnected(true)
          if (msg.llm) setLlmState(msg.llm)
        } else if (msg.type === 'transcript') {
          setTranscript((lines) => [...lines, { text: msg.text, t: msg.t }])
        } else if (msg.type === 'score') {
          setScore(msg)
        } else if (msg.type === 'error') {
          setError(msg.message)
        }
      }

      ws.onclose = () => {
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
    }
  }, [])

  const send = useCallback((msg) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(JSON.stringify(msg))
  }, [])

  const start = useCallback(
    (sample) => {
      setError(null)
      setTranscript([])
      setScore(null)
      setCallNumber((n) => n + 1)
      send({ type: 'start', mode: 'demo', sample })
    },
    [send],
  )

  const stop = useCallback(() => send({ type: 'stop' }), [send])

  return { connected, llmState, callState, callNumber, transcript, score, error, start, stop }
}
