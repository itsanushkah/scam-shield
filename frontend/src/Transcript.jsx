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
    <section ref={boxRef} className="mx-5 mt-4 flex-1 overflow-y-auto rounded-2xl bg-slate-900 p-5" aria-live="polite">
      {lines.length === 0 ? (
        <p className="text-lg text-slate-400">{live ? 'Listening…' : 'The conversation will appear here.'}</p>
      ) : (
        <p className="text-xl leading-relaxed text-slate-100">
          {lines.map((line, i) => (
            <span key={i} className={i === lines.length - 1 ? 'text-white' : 'text-slate-300'}>
              {line.text}{' '}
            </span>
          ))}
        </p>
      )}
    </section>
  )
}
