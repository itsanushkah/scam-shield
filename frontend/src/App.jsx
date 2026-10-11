import PhoneFrame from './PhoneFrame.jsx'

export default function App() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-200 p-4">
      <PhoneFrame>
        <CallHeader />

        {/* Risk meter goes here (part 8). */}
        <section className="mx-5 rounded-2xl bg-emerald-600 px-5 py-4 text-center">
          <p className="text-2xl font-bold">Listening</p>
          <p className="text-lg text-emerald-100">No warning signs yet</p>
        </section>

        {/* Live transcript goes here (part 5). */}
        <section className="mx-5 mt-4 flex-1 overflow-y-auto rounded-2xl bg-slate-900 p-5">
          <p className="text-lg text-slate-400">The conversation will appear here.</p>
        </section>

        <CallControls />
      </PhoneFrame>
    </main>
  )
}

function CallHeader() {
  return (
    <header className="px-6 pb-5 pt-6 text-center">
      <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-slate-700 text-3xl font-semibold">
        ?
      </div>
      <h1 className="mt-3 text-3xl font-bold">Unknown caller</h1>
      <p className="mt-1 text-xl text-slate-300">(814) 555-0142</p>
      <p className="mt-1 text-lg tabular-nums text-slate-400">0:00</p>
    </header>
  )
}

function CallControls() {
  return (
    <footer className="flex justify-center py-6">
      <button
        type="button"
        className="flex h-20 w-20 items-center justify-center rounded-full bg-red-600 text-white shadow-lg hover:bg-red-500"
        aria-label="End call"
      >
        <svg viewBox="0 0 24 24" className="h-9 w-9 rotate-[135deg] fill-current" aria-hidden="true">
          <path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.46.57 3.6a1 1 0 0 1-.25 1L6.6 10.8Z" />
        </svg>
      </button>
    </footer>
  )
}
