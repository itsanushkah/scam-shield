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

// Phone-shaped preview: thin dark-green frame, light interior, status bar on top.
export default function PhoneFrame({ children }) {
  const time = useClock()

  return (
    <section className="phone-frame" aria-label="Phone preview">
      <div className="phone-status">
        <span>{time}</span>
        <span className="device-badge">On-device</span>
      </div>
      {children}
    </section>
  )
}
