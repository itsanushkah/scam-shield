import { useEffect, useRef } from 'react'

// Live call transcript in large, readable text. Keeps the newest words in view.
export default function Transcript({ lines, live }) {
  const boxRef = useRef(null)

  // Scroll only this box, not the page.
  useEffect(() => {
    const box = boxRef.current
    if (box) box.scrollTo({ top: box.scrollHeight, behavior: 'smooth' })
  }, [lines.length])

  return (
    <section ref={boxRef} className="transcript" aria-label="Conversation transcript" aria-live="polite">
      <div className="transcript-heading">
        <span>CONVERSATION</span>
        <span>{live ? 'LIVE' : 'TRANSCRIPT'}</span>
      </div>
      {lines.length === 0 ? (
        <p className="transcript-text transcript-empty">
          {live ? 'Listening for speech…' : 'The conversation will appear here.'}
        </p>
      ) : (
        <p className="transcript-text">
          {lines.map((line, i) => (
            <span key={i} className={i === lines.length - 1 ? 'latest' : undefined}>
              {line.text}{' '}
            </span>
          ))}
        </p>
      )}
    </section>
  )
}
