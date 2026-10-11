// Shown on the phone when a call ends: what happened, in plain words.

const VERDICTS = {
  red: { title: 'This was likely a scam', badge: 'bg-red-600', icon: '!' },
  yellow: { title: 'Some warning signs', badge: 'bg-amber-500', icon: '?' },
  green: { title: 'This call looked safe', badge: 'bg-emerald-600', icon: '✓' },
}

const SIGNAL_WORDS = {
  payment_request: 'Asked for money in a way scammers use',
  credential_request: 'Asked for a code or PIN',
  secrecy: 'Wanted it kept secret',
  urgency: 'Rushed you',
  impersonation: 'Pretended to be someone you trust',
}

const clock = (s) => `${Math.floor(s / 60)}:${String(Math.round(s) % 60).padStart(2, '0')}`

export default function CallSummary({ summary, onClose }) {
  const v = VERDICTS[summary.verdict] ?? VERDICTS.green
  const flagged = summary.verdict !== 'green'

  return (
    <div
      role="dialog"
      aria-labelledby="summary-title"
      className="absolute inset-x-0 bottom-0 top-9 z-20 flex flex-col overflow-y-auto bg-slate-950 px-6 pb-6 pt-5 text-white"
    >
      <p className="text-sm font-semibold uppercase tracking-wide text-slate-400">Call summary</p>

      <div className="mt-3 flex items-center gap-3">
        <span
          className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-2xl font-extrabold ${v.badge}`}
        >
          {v.icon}
        </span>
        <h2 id="summary-title" className="text-2xl font-extrabold leading-tight">
          {v.title}
        </h2>
      </div>

      <p className="mt-3 text-lg text-slate-300">
        Call length {clock(summary.duration)}
        {summary.red_at != null && <> · warning at {clock(summary.red_at)}</>}
      </p>

      {flagged ? (
        <>
          {summary.signals.length > 0 && (
            <Section title="What the caller did">
              <ul className="space-y-1.5">
                {summary.signals.map((s) => (
                  <li key={s} className="flex gap-2 text-lg">
                    <span className="text-red-400" aria-hidden="true">
                      •
                    </span>
                    {SIGNAL_WORDS[s] ?? s}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {summary.phrases.length > 0 && (
            <Section title="What they said">
              <div className="flex flex-wrap gap-2">
                {summary.phrases.map((p) => (
                  <span key={p} className="rounded-lg bg-slate-800 px-2.5 py-1 text-base text-slate-100">
                    “{p}”
                  </span>
                ))}
              </div>
            </Section>
          )}

          {summary.suggested_action && (
            <Section title="What to do now">
              <p className="rounded-2xl bg-white px-4 py-3 text-xl font-bold leading-snug text-slate-900">
                {summary.suggested_action}
              </p>
            </Section>
          )}
        </>
      ) : (
        <p className="mt-6 text-xl leading-snug text-slate-200">No warning signs during this call.</p>
      )}

      <div className="flex-1" />
      <button
        type="button"
        onClick={onClose}
        className="mt-6 w-full rounded-2xl border-2 border-white/60 py-3 text-xl font-semibold hover:bg-white/10"
      >
        Close
      </button>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <section className="mt-5">
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">{title}</h3>
      {children}
    </section>
  )
}
