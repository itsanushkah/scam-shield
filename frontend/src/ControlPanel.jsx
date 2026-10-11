import { useEffect, useState } from 'react'

import { MicIcon } from './icons.jsx'

// Two ways in: Microphone listens through this computer's mic; Recording plays a test call
// out loud while the backend analyses the same file.
export default function ControlPanel({ call }) {
  const [mode, setMode] = useState('live')
  const [sample, setSample] = useState('')
  const busy = call.callState === 'started' || call.callState === 'starting'
  const canStart = call.connected && (mode === 'live' || sample)

  return (
    <section className="control-panel" aria-labelledby="panel-title">
      <div className="panel-heading">
        <h2 id="panel-title">Let’s check your call</h2>
        <span className="connection-badge" data-state={call.connected ? 'ready' : 'waiting'} aria-live="polite">
          {call.connected ? 'Connected' : 'Connecting…'}
        </span>
      </div>

      <div className="mode-switch" role="group" aria-label="Audio source">
        {[
          ['live', 'Microphone'],
          ['demo', 'Recording'],
        ].map(([value, label]) => (
          <button key={value} type="button" aria-pressed={mode === value} onClick={() => setMode(value)} disabled={busy}>
            {label}
          </button>
        ))}
      </div>

      {mode === 'live' ? (
        <>
          <p className="source-help">Put your phone on speaker nearby, then start listening.</p>
          <MicLevel level={call.micLevel} active={busy} />
        </>
      ) : (
        <>
          <p className="source-help">Choose a test call. It plays out loud while Scam Shield listens.</p>
          <SamplePicker connected={call.connected} disabled={busy} sample={sample} setSample={setSample} />
        </>
      )}

      {busy ? (
        <button type="button" className="primary-button" data-variant="stop" onClick={call.stop}>
          Stop listening
        </button>
      ) : (
        <button
          type="button"
          className="primary-button"
          onClick={() => call.start(mode === 'live' ? null : sample, mode)}
          disabled={!canStart}
        >
          {mode === 'live' ? 'Start listening' : 'Play recording'}
        </button>
      )}

      {call.connected && call.llmState === 'down' && (
        <p className="panel-note">AI check paused: using the keyword rules for now.</p>
      )}
      {call.error && <p className="panel-error">{call.error}</p>}
    </section>
  )
}

function MicLevel({ level, active }) {
  const pct = Math.round(level * 100)
  return (
    <div className="mic-level" data-active={active}>
      <MicIcon />
      <div
        className="mic-track"
        role="meter"
        aria-label="Microphone level"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
      >
        <div className="mic-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

// Recordings come from the backend's samples/ folder.
function SamplePicker({ connected, disabled, sample, setSample }) {
  const [samples, setSamples] = useState([])

  useEffect(() => {
    if (!connected) return
    fetch('/samples')
      .then((r) => r.json())
      .then((d) => {
        setSamples(d.samples)
        setSample((s) => s || d.samples.find((n) => n.includes('short_scam_bail')) || d.samples[0] || '')
      })
      .catch(() => {})
  }, [connected, setSample])

  return (
    <select
      className="sample-picker"
      aria-label="Test call to play"
      value={sample}
      onChange={(e) => setSample(e.target.value)}
      disabled={disabled || samples.length === 0}
    >
      {samples.map((s) => (
        <option key={s} value={s}>
          {s.replace('.wav', '').replaceAll('_', ' ')}
        </option>
      ))}
    </select>
  )
}
