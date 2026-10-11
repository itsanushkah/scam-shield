import { CheckIcon } from './icons.jsx'

// "Is it really them?": shown when the caller claims to be family and the call looks risky.
// Plain words, using the name the caller gave if we heard one.
export default function VerifyCard({ verify }) {
  return (
    <section className="verify-card evidence-in" aria-live="polite">
      <h3>Is it really {verify.name ?? 'them'}?</h3>
      <ul>
        {verify.steps.map((step) => (
          <li key={step}>
            <CheckIcon />
            {step}
          </li>
        ))}
      </ul>
    </section>
  )
}
