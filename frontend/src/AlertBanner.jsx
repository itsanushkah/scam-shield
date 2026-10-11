import { WarningIcon } from './icons.jsx'

// Shown once, when the call first turns red. One clear instruction. This app can't end a
// phone call, so it tells the person to hang up on their own phone.
export default function AlertBanner({ alert, onStop, onDismiss }) {
  return (
    <div className="warning-overlay" role="alertdialog" aria-labelledby="alert-title" aria-describedby="alert-action">
      <div className="warning-icon" aria-hidden="true">
        <WarningIcon />
      </div>

      <h2 id="alert-title">This call looks like a scam</h2>

      {alert.suggested_action && (
        <p id="alert-action" className="recommended-action">
          {alert.suggested_action}
        </p>
      )}

      {alert.reason && <p className="warning-reason">{alert.reason}</p>}

      {alert.verify && (
        <p className="warning-verify">
          Is it really {alert.verify.name ?? 'them'}? {alert.verify.steps[0]}
        </p>
      )}

      <p className="warning-note">Hang up on your phone. Scam Shield can’t end the call for you.</p>

      <button type="button" onClick={onStop}>
        I’ve hung up · Stop listening
      </button>
      <button type="button" className="secondary-button" onClick={onDismiss}>
        Keep listening
      </button>
    </div>
  )
}
