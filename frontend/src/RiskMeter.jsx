// Risk meter: level in words, a green/yellow/red bar, the reason, and what was noticed.
// Big text and plain words, for older eyes.

const LEVELS = {
  green: { title: 'Looks safe', panel: 'bg-emerald-600', sub: 'text-emerald-50' },
  yellow: { title: 'Be careful', panel: 'bg-amber-500', sub: 'text-amber-950' },
  red: { title: 'Likely a scam', panel: 'bg-red-600', sub: 'text-red-50' },
}

// What the caller is doing, in plain present-tense words.
const SIGNAL_WORDS = {
  payment_request: 'Asking for money',
  credential_request: 'Asking for a code',
  secrecy: 'Wants it kept secret',
  urgency: 'Rushing you',
  impersonation: 'Pretending to be someone',
}

export default function RiskMeter({ score, live }) {
  const level = score?.level ?? 'green'
  const style = LEVELS[level]
  const risk = score?.risk ?? 0
  const title = score ? style.title : live ? 'Listening' : 'Ready'
  const darkText = level === 'yellow'

  return (
    <section
      className={`mx-5 rounded-2xl px-5 py-4 transition-colors duration-500 ${style.panel} ${darkText ? 'text-slate-950' : 'text-white'}`}
      aria-live="assertive"
    >
      <div className="flex items-baseline justify-between">
        <p className="text-2xl font-bold">{title}</p>
        {score && <p className={`text-sm font-semibold ${style.sub}`}>Risk {risk}</p>}
      </div>

      <Bar risk={risk} />

      {score?.evidence?.length > 0 ? (
        <Evidence rows={score.evidence} chip={darkText ? 'bg-black/15' : 'bg-white/20'} />
      ) : (
        <p className={`mt-2 text-lg leading-snug ${style.sub}`}>{score?.reason || 'No warning signs yet'}</p>
      )}
    </section>
  )
}

// The reasons, building up as the call goes on: one row per thing the caller is doing,
// with their own words. Rows and quotes are keyed, so only new ones animate in.
function Evidence({ rows, chip }) {
  return (
    <ul className="mt-3 space-y-1.5">
      {rows.map((row) => (
        <li key={row.signal} className="evidence-in">
          <span className="text-base font-bold">{SIGNAL_WORDS[row.signal] ?? row.signal}</span>
          {row.phrases.length > 0 && (
            <span className="ml-1.5 inline-flex flex-wrap gap-1 align-middle">
              {row.phrases.slice(0, 2).map((p) => (
                <span key={p} className={`evidence-in rounded-md px-1.5 py-0.5 text-sm ${chip}`}>
                  “{p}”
                </span>
              ))}
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}

// Track split into the three zones (0-40, 40-70, 70-100), with a marker at the current risk.
function Bar({ risk }) {
  return (
    <div className="relative mt-3 h-3 rounded-full bg-black/25" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={risk} aria-label="Scam risk">
      <div className="absolute inset-y-0 left-0 flex w-full overflow-hidden rounded-full opacity-60">
        <div className="w-[40%] bg-emerald-300" />
        <div className="w-[30%] bg-amber-300" />
        <div className="w-[30%] bg-red-300" />
      </div>
      <div
        className="absolute top-1/2 h-6 w-6 -translate-x-1/2 -translate-y-1/2 rounded-full border-4 border-white bg-slate-900 shadow transition-[left] duration-700 ease-out"
        style={{ left: `${risk}%` }}
      />
    </div>
  )
}
