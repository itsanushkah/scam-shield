// Risk card: level in plain words, a green/amber/red bar, and the reasons building up.
// Green means no warning signs so far, not a promise that the call is safe.

const LEVELS = {
  green: { title: 'No warning signs', detail: 'Nothing worrying so far.' },
  yellow: { title: 'Be careful', detail: 'Some warning signs. Take your time.' },
  red: { title: 'Likely a scam', detail: '' },
}

// What the caller is doing, in plain present-tense words.
const SIGNAL_WORDS = {
  payment_request: 'Asking for money',
  credential_request: 'Asking for a code',
  secrecy: 'Wants it kept secret',
  urgency: 'Rushing you',
  impersonation: 'Pretending to be someone',
}

export default function RiskMeter({ score, state }) {
  const level = score?.level ?? 'idle'
  const listening = state === 'started' || state === 'starting'

  let title, detail
  if (score) {
    title = LEVELS[score.level].title
    detail = (score.level !== 'green' && score.reason) || LEVELS[score.level].detail
  } else if (listening) {
    title = 'Listening'
    detail = 'Nothing to flag yet.'
  } else {
    title = 'Ready'
    detail = 'Start listening to check a call.'
  }

  return (
    <section className="risk-card" data-level={level} aria-live="assertive">
      <div className="risk-card-head">
        <h3>{title}</h3>
        {score && <p className="risk-number">Risk {score.risk}</p>}
      </div>

      {score && <Bar risk={score.risk} />}

      {score?.evidence?.length > 0 ? <Evidence rows={score.evidence} /> : <p>{detail}</p>}
    </section>
  )
}

// The reasons, one row per thing the caller is doing, with their own words.
// Rows and quotes are keyed, so only new ones animate in.
function Evidence({ rows }) {
  return (
    <ul className="evidence">
      {rows.map((row) => (
        <li key={row.signal} className="evidence-in">
          <strong>{SIGNAL_WORDS[row.signal] ?? row.signal}</strong>
          {row.phrases.slice(0, 2).map((p) => (
            <span key={p} className="evidence-quote evidence-in">
              “{p}”
            </span>
          ))}
        </li>
      ))}
    </ul>
  )
}

// Track split into the three zones (0-40, 40-70, 70-100), with a marker at the current risk.
function Bar({ risk }) {
  return (
    <div
      className="risk-bar"
      role="meter"
      aria-label="Scam risk"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={risk}
    >
      <div className="risk-bar-zones" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div className="risk-bar-marker" style={{ left: `${risk}%` }} />
    </div>
  )
}
