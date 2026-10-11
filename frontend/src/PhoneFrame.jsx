import { useEffect, useState } from 'react'

const formatTime = () => new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })

// Wall-clock time for the status bar, refreshed every few seconds.
function useClock() {
  const [time, setTime] = useState(formatTime)

  useEffect(() => {
    const id = setInterval(() => setTime(formatTime()), 5000)
    return () => clearInterval(id)
  }, [])

  return time
}

// Phone-shaped shell: body, notch and status bar. The call screen goes inside.
export default function PhoneFrame({ children }) {
  return (
    <div className="relative h-[min(820px,calc(100dvh-2rem))] w-[min(400px,100%)] rounded-[3.25rem] border-[12px] border-neutral-900 bg-neutral-900 shadow-2xl ring-1 ring-neutral-700">
      <div className="absolute left-1/2 top-2 z-10 h-7 w-32 -translate-x-1/2 rounded-full bg-black" />

      <div className="flex h-full flex-col overflow-hidden rounded-[2.5rem] bg-slate-950 text-white">
        <StatusBar />
        {children}
      </div>
    </div>
  )
}

function StatusBar() {
  const time = useClock()

  return (
    <div className="flex items-center justify-between px-7 pb-1 pt-3 text-sm font-semibold">
      <span>{time}</span>
      <span className="flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs text-emerald-300">
        <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 fill-current" aria-hidden="true">
          <path d="M12 2 4 5v6c0 5 3.4 9.7 8 11 4.6-1.3 8-6 8-11V5l-8-3Z" />
        </svg>
        On-device
      </span>
    </div>
  )
}
