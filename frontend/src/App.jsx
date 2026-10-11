import { useEffect, useState } from 'react'

import AlertBanner from './AlertBanner.jsx'
import CallSummary from './CallSummary.jsx'
import ControlPanel from './ControlPanel.jsx'
import PhoneFrame from './PhoneFrame.jsx'
import RiskMeter from './RiskMeter.jsx'
import Transcript from './Transcript.jsx'
import VerifyCard from './VerifyCard.jsx'
import { useCallSocket } from './useCallSocket.js'

export default function App() {
  const call = useCallSocket()
  const live = call.callState === 'started'
  // The warning shows once per call; "Keep listening" or "Hang up" closes it for that call.
  const [dismissedCall, setDismissedCall] = useState(null)
  const showAlert = call.alert && dismissedCall !== call.callNumber
  const dismiss = () => setDismissedCall(call.callNumber)
  // After the call ends, a summary of what happened, until closed.
  const [closedSummary, setClosedSummary] = useState(null)
  const showSummary = call.summary && !showAlert && closedSummary !== call.callNumber

  return (
    <main className="flex min-h-screen flex-wrap items-center justify-center gap-x-14 gap-y-8 bg-gradient-to-br from-slate-100 via-slate-200 to-emerald-100 p-4">
      <div className="w-full max-w-sm">
        <Brand llmOn={call.llmState === 'ok'} />
        <ControlPanel call={call} />
      </div>

      <PhoneFrame>
        <CallHeader
          key={call.callNumber}
          live={live}
          ended={call.callState === 'ended' || call.callState === 'stopped'}
          compact={call.score?.level === 'red'}
        />

        <RiskMeter score={call.score} live={live} />

        {call.score?.verify && <VerifyCard verify={call.score.verify} />}

        <Transcript lines={call.transcript} live={live} />

        <CallControls onEnd={call.stop} disabled={!live} compact={call.score?.level === 'red'} />

        {showAlert && (
          <AlertBanner
            // Live reason, not the one frozen in the alert: if the LLM fired first, the
            // clearer rule reason ("wants gift cards") replaces it a moment later.
            alert={{
              reason: call.score?.reason || call.alert.reason,
              suggested_action: call.score?.suggested_action || call.alert.suggested_action,
              verify: call.score?.verify,
            }}
            onHangUp={() => {
              call.stop()
              dismiss()
            }}
            onDismiss={dismiss}
          />
        )}

        {showSummary && <CallSummary summary={call.summary} onClose={() => setClosedSummary(call.callNumber)} />}
      </PhoneFrame>
    </main>
  )
}

function Brand({ llmOn }) {
  return (
    <header className="mb-6">
      <div className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-600 text-white shadow">
          <svg viewBox="0 0 24 24" className="h-7 w-7 fill-current" aria-hidden="true">
            <path d="M12 2 4 5v6c0 5 3.4 9.7 8 11 4.6-1.3 8-6 8-11V5l-8-3Zm-1.2 14.2-3.5-3.5 1.4-1.4 2.1 2.1 4.9-4.9 1.4 1.4-6.3 6.3Z" />
          </svg>
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight text-slate-900">Scam Shield</h1>
      </div>
      <p className="mt-3 text-lg leading-snug text-slate-700">
        Listens to a phone call and warns older adults about scams, in real time.
      </p>
      <ul className="mt-4 flex flex-wrap gap-2 text-sm font-medium">
        <Badge>Speech-to-text on device</Badge>
        <Badge muted={!llmOn}>{llmOn ? 'AI check on device' : 'AI check paused: using keyword rules'}</Badge>
        <Badge>No internet needed</Badge>
      </ul>
    </header>
  )
}

function Badge({ children, muted }) {
  return (
    <li
      className={`rounded-full px-3 py-1 ring-1 ${muted ? 'bg-amber-50 text-amber-800 ring-amber-200' : 'bg-white/70 text-emerald-800 ring-emerald-200'}`}
    >
      {children}
    </li>
  )
}

// Shrinks while a warning is showing, so the meter and transcript keep their room.
function CallHeader({ live, ended, compact }) {
  const seconds = useCallTimer(live)
  const status = ended ? 'Call ended' : `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`

  if (compact) {
    return (
      <header className="flex items-center gap-3 px-6 pb-3 pt-4">
        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-slate-700 text-xl font-semibold">?</div>
        <div>
          <p className="text-xl font-bold leading-tight">Unknown caller</p>
          <p className="text-base tabular-nums text-slate-400">{status}</p>
        </div>
      </header>
    )
  }

  return (
    <header className="px-6 pb-5 pt-6 text-center">
      <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-slate-700 text-3xl font-semibold">
        ?
      </div>
      <p className="mt-3 text-3xl font-bold">Unknown caller</p>
      <p className="mt-1 text-xl text-slate-300">(814) 555-0142</p>
      <p className="mt-1 text-lg tabular-nums text-slate-400">{status}</p>
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

// Smaller while red, so the reasons, the check card and the transcript all fit.
function CallControls({ onEnd, disabled, compact }) {
  return (
    <footer className={`flex justify-center ${compact ? 'py-3' : 'py-6'}`}>
      <button
        type="button"
        onClick={onEnd}
        disabled={disabled}
        className={`flex ${compact ? 'h-16 w-16' : 'h-20 w-20'} items-center justify-center rounded-full bg-red-600 text-white shadow-lg hover:bg-red-500 disabled:opacity-40`}
        aria-label="End call"
      >
        <svg viewBox="0 0 24 24" className="h-9 w-9 rotate-[135deg] fill-current" aria-hidden="true">
          <path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.46.57 3.6a1 1 0 0 1-.25 1L6.6 10.8Z" />
        </svg>
      </button>
    </footer>
  )
}
