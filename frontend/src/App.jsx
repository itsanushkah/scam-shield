import { useEffect, useState } from 'react'

import AlertBanner from './AlertBanner.jsx'
import PhoneFrame from './PhoneFrame.jsx'
import RiskMeter from './RiskMeter.jsx'
import Transcript from './Transcript.jsx'
import { useCallSocket } from './useCallSocket.js'

export default function App() {
  const call = useCallSocket()
  const live = call.callState === 'started'
  // The warning shows once per call; "Keep listening" or "Hang up" closes it for that call.
  const [dismissedCall, setDismissedCall] = useState(null)
  const showAlert = call.alert && dismissedCall !== call.callNumber
  const dismiss = () => setDismissedCall(call.callNumber)

  return (
    <main className="flex min-h-screen flex-wrap items-center justify-center gap-8 bg-slate-200 p-4">
      <PhoneFrame>
        <CallHeader key={call.callNumber} live={live} ended={call.callState === 'ended'} />

        <RiskMeter score={call.score} live={live} />

        <Transcript lines={call.transcript} live={live} />

        <CallControls onEnd={call.stop} disabled={!live} />

        {showAlert && (
          <AlertBanner
            // Live reason, not the one frozen in the alert: if the LLM fired first, the
            // clearer rule reason ("wants gift cards") replaces it a moment later.
            alert={{
              reason: call.score?.reason || call.alert.reason,
              suggested_action: call.score?.suggested_action || call.alert.suggested_action,
            }}
            onHangUp={() => {
              call.stop()
              dismiss()
            }}
            onDismiss={dismiss}
          />
        )}
      </PhoneFrame>

      <DemoPanel call={call} />
    </main>
  )
}

function CallHeader({ live, ended }) {
  const seconds = useCallTimer(live)

  return (
    <header className="px-6 pb-5 pt-6 text-center">
      <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-slate-700 text-3xl font-semibold">
        ?
      </div>
      <h1 className="mt-3 text-3xl font-bold">Unknown caller</h1>
      <p className="mt-1 text-xl text-slate-300">(814) 555-0142</p>
      <p className="mt-1 text-lg tabular-nums text-slate-400">
        {ended ? 'Call ended' : `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`}
      </p>
    </header>
  )
}

// Counts up while the call is live. CallHeader is keyed per call, so each call starts at 0.
function useCallTimer(running) {
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    if (!running) return
    const started = Date.now()
    const id = setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 250)
    return () => clearInterval(id)
  }, [running])

  return seconds
}

function CallControls({ onEnd, disabled }) {
  return (
    <footer className="flex justify-center py-6">
      <button
        type="button"
        onClick={onEnd}
        disabled={disabled}
        className="flex h-20 w-20 items-center justify-center rounded-full bg-red-600 text-white shadow-lg hover:bg-red-500 disabled:opacity-40"
        aria-label="End call"
      >
        <svg viewBox="0 0 24 24" className="h-9 w-9 rotate-[135deg] fill-current" aria-hidden="true">
          <path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.46.57 3.6a1 1 0 0 1-.25 1L6.6 10.8Z" />
        </svg>
      </button>
    </footer>
  )
}

// Operator controls for the demo. Sits outside the phone.
function DemoPanel({ call }) {
  const [samples, setSamples] = useState([])
  const [sample, setSample] = useState('')

  useEffect(() => {
    if (!call.connected) return
    fetch('/samples')
      .then((r) => r.json())
      .then((d) => {
        setSamples(d.samples)
        setSample((s) => s || d.samples.find((n) => n.includes('grandson_bail')) || d.samples[0] || '')
      })
      .catch(() => {})
  }, [call.connected])

  const live = call.callState === 'started'

  return (
    <aside className="w-72 rounded-2xl bg-white p-5 text-slate-800 shadow">
      <h2 className="text-lg font-bold">Demo controls</h2>
      <p className={`mt-1 text-sm ${call.connected ? 'text-emerald-700' : 'text-amber-700'}`}>
        {call.connected ? 'Backend connected' : 'Waiting for backend…'}
      </p>
      {call.connected && (
        <p className={`text-sm ${call.llmState === 'ok' ? 'text-emerald-700' : 'text-amber-700'}`}>
          {call.llmState === 'ok' ? 'AI check on (Ollama)' : 'AI check off: using rules only'}
        </p>
      )}

      <label className="mt-4 block text-sm font-medium" htmlFor="sample">
        Call to play
      </label>
      <select
        id="sample"
        value={sample}
        onChange={(e) => setSample(e.target.value)}
        disabled={live}
        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
      >
        {samples.map((s) => (
          <option key={s} value={s}>
            {s.replace('.wav', '')}
          </option>
        ))}
      </select>

      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={() => call.start(sample)}
          disabled={!call.connected || !sample || live}
          className="flex-1 rounded-lg bg-slate-900 px-3 py-2 font-semibold text-white disabled:opacity-40"
        >
          Start
        </button>
        <button
          type="button"
          onClick={call.stop}
          disabled={!live}
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 font-semibold disabled:opacity-40"
        >
          Stop
        </button>
      </div>

      {call.error && <p className="mt-3 text-sm text-red-700">{call.error}</p>}
    </aside>
  )
}
