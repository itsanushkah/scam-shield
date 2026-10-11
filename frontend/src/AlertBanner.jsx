// Full-screen warning shown once, when the call first turns red.
// Large text, one clear instruction, and two big buttons.
export default function AlertBanner({ alert, onHangUp, onDismiss }) {
  return (
    <div
      role="alertdialog"
      aria-labelledby="alert-title"
      aria-describedby="alert-action"
      className="absolute inset-x-0 bottom-0 top-9 z-20 flex flex-col bg-red-700 px-6 pb-8 pt-6 text-white"
    >
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <div className="flex h-20 w-20 animate-pulse items-center justify-center rounded-full bg-white text-red-700">
          <svg viewBox="0 0 24 24" className="h-12 w-12 fill-current" aria-hidden="true">
            <path d="M12 2 1 21h22L12 2Zm1 15h-2v-2h2v2Zm0-4h-2V9h2v4Z" />
          </svg>
        </div>

        <h2 id="alert-title" className="mt-5 text-3xl font-extrabold leading-tight">
          This call looks like a scam
        </h2>

        {alert.suggested_action && (
          <p id="alert-action" className="mt-4 rounded-2xl bg-white px-4 py-3 text-2xl font-bold leading-snug text-red-800">
            {alert.suggested_action}
          </p>
        )}

        {alert.reason && <p className="mt-4 text-xl leading-snug text-red-50">{alert.reason}</p>}

        {alert.verify && (
          <p className="mt-4 rounded-2xl bg-sky-100 px-4 py-3 text-xl font-bold leading-snug text-slate-900">
            Is it really {alert.verify.name ?? 'them'}? {alert.verify.steps[0]}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-3">
        <button
          type="button"
          onClick={onHangUp}
          className="w-full rounded-2xl bg-white py-4 text-2xl font-extrabold text-red-700 shadow-lg hover:bg-red-50"
        >
          Hang up
        </button>
        <button
          type="button"
          onClick={onDismiss}
          className="w-full rounded-2xl border-2 border-white/70 py-3 text-xl font-semibold text-white hover:bg-white/10"
        >
          Keep listening
        </button>
      </div>
    </div>
  )
}
