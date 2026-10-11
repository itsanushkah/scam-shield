import { CheckIcon, QuestionIcon, WarningIcon } from './icons.jsx'

// Shown when listening stops: what happened, in plain words.

const VERDICTS = {
  red: { title: 'This was likely a scam', Icon: WarningIcon },
  yellow: { title: 'Some warning signs', Icon: QuestionIcon },
  green: { title: 'No warning signs heard', Icon: CheckIcon },
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
    <div className="summary-overlay" role="dialog" aria-labelledby="summary-title">
      <p className="summary-label">SESSION SUMMARY</p>

      <div className="summary-verdict">
        <span className="summary-badge" data-verdict={summary.verdict} aria-hidden="true">
          <v.Icon />
        </span>
        <h2 id="summary-title">{v.title}</h2>
      </div>

      <p className="summary-meta">
        Listened for {clock(summary.duration)}
        {summary.red_at != null && <> · warning at {clock(summary.red_at)}</>}
      </p>

      {flagged ? (
        <>
          {summary.signals.length > 0 && (
            <Section title="WHAT THE CALLER DID">
              <ul>
                {summary.signals.map((s) => (
                  <li key={s}>{SIGNAL_WORDS[s] ?? s}</li>
                ))}
              </ul>
            </Section>
          )}

          {summary.phrases.length > 0 && (
            <Section title="WHAT THEY SAID">
              <div className="summary-quotes">
                {summary.phrases.map((p) => (
                  <span key={p}>“{p}”</span>
                ))}
              </div>
            </Section>
          )}

          {summary.verify && (
            <Section title={`CHECK IT’S REALLY ${(summary.verify.name ?? 'them').toUpperCase()}`}>
              <ul>
                {summary.verify.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ul>
            </Section>
          )}

          {summary.suggested_action && (
            <Section title="WHAT TO DO NOW">
              <p className="recommended-action">{summary.suggested_action}</p>
            </Section>
          )}
        </>
      ) : (
        <p className="summary-safe">
          Nothing worrying was heard. If something still feels off, hang up and call back on a number you know.
        </p>
      )}

      <button type="button" onClick={onClose}>
        Close
      </button>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <section className="summary-section">
      <h3>{title}</h3>
      {children}
    </section>
  )
}
