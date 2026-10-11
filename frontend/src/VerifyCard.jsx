// "Check it's really them": shown when the caller claims to be family and the call looks risky.
// Plain words, big text, using the name the caller gave if we heard one.
export default function VerifyCard({ verify }) {
  return (
    <section className="evidence-in mx-5 mt-2 rounded-2xl bg-sky-100 px-4 py-2.5 text-slate-900" aria-live="polite">
      <p className="text-lg font-extrabold">Is it really {verify.name ?? 'them'}?</p>
      <ul className="mt-1 space-y-0.5">
        {verify.steps.map((step) => (
          <li key={step} className="flex gap-2 text-base leading-snug">
            <span className="font-bold text-sky-700" aria-hidden="true">
              ✓
            </span>
            {step}
          </li>
        ))}
      </ul>
    </section>
  )
}
