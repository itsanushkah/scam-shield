import { useEffect, useState } from 'react'

// Two ways in: Live listens through this laptop's mic; Recording plays a test call on the backend.
export default function ControlPanel({ call }) {
  const [mode, setMode] = useState('live')
  const [sample, setSample] = useState('')
  const live = call.callState === 'started' || call.callState === 'starting'
  const canStart = call.connected && (mode === 'live' || sample)

  return (
    <section className="rounded-3xl bg-white p-6 text-slate-800 shadow-xl ring-1 ring-slate-900/5">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">{live ? 'Listening…' : 'Ready to listen'}</h2>
        <StatusDot ok={call.connected} label={call.connected ? 'Connected' : 'Starting up…'} />
      </div>

      <ModeSwitch mode={mode} setMode={setMode} disabled={live} />

      {mode === 'live' ? (
        <div className="mt-4">
          <MicLevel level={call.micLevel} active={live && mode === 'live'} />
        </div>
      ) : (
        <SamplePicker connected={call.connected} disabled={live} sample={sample} setSample={setSample} />
      )}

      <div className="mt-5 flex gap-3">
        {!live ? (
          <button
            type="button"
            onClick={() => call.start(mode === 'live' ? null : sample, mode)}
            disabled={!canStart}
            className="flex-1 rounded-2xl bg-emerald-600 py-3.5 text-lg font-bold text-white shadow hover:bg-emerald-500 disabled:opacity-40"
          >
            {mode === 'live' ? 'Start listening' : 'Play file'}
          </button>
        ) : (
          <button
            type="button"
            onClick={call.stop}
            className="flex-1 rounded-2xl bg-slate-900 py-3.5 text-lg font-bold text-white shadow hover:bg-slate-700"
          >
            Stop
          </button>
        )}
      </div>

      {call.error && <p className="mt-3 text-sm text-red-700">{call.error}</p>}
    </section>
  )
}

function StatusDot({ ok, label }) {
  return (
    <span className={`flex items-center gap-1.5 text-sm font-medium ${ok ? 'text-emerald-700' : 'text-amber-700'}`}>
      <span className={`h-2 w-2 rounded-full ${ok ? 'bg-emerald-500' : 'animate-pulse bg-amber-500'}`} />
      {label}
    </span>
  )
}

function MicLevel({ level, active }) {
  return (
    <div className="mt-3 flex items-center gap-3">
      <svg
        viewBox="0 0 24 24"
        className={`h-5 w-5 fill-current ${active ? 'text-emerald-600' : 'text-slate-400'}`}
        aria-hidden="true"
      >
        <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11h-2Z" />
      </svg>
      <div
        className="h-2.5 flex-1 overflow-hidden rounded-full bg-slate-200"
        role="meter"
        aria-label="Mic level"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(level * 100)}
      >
        <div
          className="h-full rounded-full bg-emerald-500 transition-[width] duration-100"
          style={{ width: `${Math.round(level * 100)}%` }}
        />
      </div>
    </div>
  )
}

function ModeSwitch({ mode, setMode, disabled }) {
  return (
    <div
      className="mt-4 grid grid-cols-2 rounded-xl bg-slate-100 p-1 text-sm font-semibold"
      role="radiogroup"
      aria-label="Audio source"
    >
      {[
        ['live', 'Live'],
        ['demo', 'Recording'],
      ].map(([value, label]) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={mode === value}
          onClick={() => setMode(value)}
          disabled={disabled}
          className={`rounded-lg py-1.5 ${mode === value ? 'bg-white shadow' : 'text-slate-500'}`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

// Backup only: plays a sample file on the backend instead of using the mic.
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
      aria-label="Call to play"
      value={sample}
      onChange={(e) => setSample(e.target.value)}
      disabled={disabled}
      className="mt-4 w-full rounded-xl border border-slate-300 bg-white px-3 py-2"
    >
      {samples.map((s) => (
        <option key={s} value={s}>
          {s.replace('.wav', '')}
        </option>
      ))}
    </select>
  )
}
