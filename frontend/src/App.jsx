import { useEffect, useState } from 'react'

import AlertBanner from './AlertBanner.jsx'
import CallSummary from './CallSummary.jsx'
import ControlPanel from './ControlPanel.jsx'
import { LockIcon, ShieldIcon, WaveIcon } from './icons.jsx'
import PhoneFrame from './PhoneFrame.jsx'
import RiskMeter from './RiskMeter.jsx'
import Transcript from './Transcript.jsx'
import VerifyCard from './VerifyCard.jsx'
import { useCallSocket } from './useCallSocket.js'

export default function App() {
  const call = useCallSocket()
  const live = call.callState === 'started'
  // The warning shows once per call; "Keep listening" or "Stop listening" closes it for that call.
  const [dismissedCall, setDismissedCall] = useState(null)
  const showAlert = call.alert && dismissedCall !== call.callNumber
  const dismiss = () => setDismissedCall(call.callNumber)
  // After the session ends, a summary of what happened, until closed.
  const [closedSummary, setClosedSummary] = useState(null)
  const showSummary = call.summary && !showAlert && closedSummary !== call.callNumber
  const red = call.score?.level === 'red'

  return (
    <div className="scam-app">
      <header className="app-nav">
        <div className="brand-logo">
          <span className="brand-icon" aria-hidden="true">
            <ShieldIcon />
          </span>
          scam shield.
        </div>
        <span className="nav-note">
          <LockIcon />
          Private by design
        </span>
      </header>

      <main className="main-layout">
        <section className="intro-column" aria-labelledby="hero-title">
          <p className="eyebrow">CONFIDENCE ON EVERY CALL</p>
          <h1 id="hero-title" className="hero-title">
            Stay connected.
            <br />
            <span>Stay a step ahead.</span>
          </h1>
          <p className="hero-description">
            A second set of ears when something feels off. Understand the warning signs and know what to do next.
          </p>

          <ControlPanel call={call} />

          <p className="privacy-note">
            <LockIcon />
            <span>
              <strong>Your conversation stays yours.</strong>
              Audio and transcripts stay on this device. No internet needed.
            </span>
          </p>
        </section>

        <div className="phone-stage">
          <PhoneFrame>
            <CallHeader key={call.callNumber} state={call.callState} compact={red} />

            <div className="phone-body">
              <RiskMeter score={call.score} state={call.callState} />
              {call.score?.verify && <VerifyCard verify={call.score.verify} />}
              <Transcript lines={call.transcript} live={live} />
            </div>

            <footer className="phone-controls">
              <button type="button" className="stop-button" onClick={call.stop} disabled={!live}>
                Stop listening
              </button>
            </footer>

            {showAlert && (
              <AlertBanner
                // Live reason, not the one frozen in the alert: if the LLM fired first, the
                // clearer rule reason ("wants gift cards") replaces it a moment later.
                alert={{
                  reason: call.score?.reason || call.alert.reason,
                  suggested_action: call.score?.suggested_action || call.alert.suggested_action,
                  verify: call.score?.verify,
                }}
                onStop={() => {
                  call.stop()
                  dismiss()
                }}
                onDismiss={dismiss}
              />
            )}

            {showSummary && <CallSummary summary={call.summary} onClose={() => setClosedSummary(call.callNumber)} />}
          </PhoneFrame>
        </div>
      </main>

      <footer className="app-footer">
        <span>On-device. Offline. Always your conversation.</span>
        <span>Scam Shield</span>
      </footer>
    </div>
  )
}

// Keyed per session, so the timer starts at 0 each time.
function CallHeader({ state, compact }) {
  const live = state === 'started'
  const seconds = useCallTimer(live)
  const clock = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
  const status =
    state === 'started'
      ? `Listening · ${clock}`
      : state === 'starting'
        ? 'Starting…'
        : state === 'ended' || state === 'stopped'
          ? 'Stopped listening'
          : 'Ready when you are'

  return (
    <header className="call-header" data-compact={compact}>
      <div className="call-avatar" aria-hidden="true">
        <WaveIcon />
      </div>
      <div>
        <h2>Call protection</h2>
        {!compact && <p>A little peace of mind.</p>}
        <p className="call-time" aria-live="polite">
          {status}
        </p>
      </div>
    </header>
  )
}

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
