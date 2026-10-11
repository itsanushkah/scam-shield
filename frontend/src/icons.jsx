// Local line icons (no icon CDN). Decorative: hidden from screen readers.

const base = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
}

export const ShieldIcon = (props) => (
  <svg {...base} {...props}>
    <path d="M12 3 4 6v5c0 5 3.5 8.6 8 10 4.5-1.4 8-5 8-10V6l-8-3Z" />
    <path d="m8 12 3 3 5-6" />
  </svg>
)

export const LockIcon = (props) => (
  <svg {...base} {...props}>
    <rect x="5" y="11" width="14" height="10" rx="2" />
    <path d="M8 11V8a4 4 0 0 1 8 0v3" />
  </svg>
)

export const MicIcon = (props) => (
  <svg {...base} {...props}>
    <rect x="9" y="3" width="6" height="11" rx="3" />
    <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
  </svg>
)

export const WaveIcon = (props) => (
  <svg {...base} {...props}>
    <path d="M3 12h2M7 8v8M11 5v14M15 8v8M19 11v2" />
  </svg>
)

export const WarningIcon = (props) => (
  <svg {...base} {...props}>
    <path d="M12 3 2 20h20L12 3Z" />
    <path d="M12 10v4M12 17.5v.01" />
  </svg>
)

export const CheckIcon = (props) => (
  <svg {...base} {...props}>
    <path d="m5 12 4.5 4.5L19 7" />
  </svg>
)

export const QuestionIcon = (props) => (
  <svg {...base} {...props}>
    <path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14M12 17.5v.01" />
  </svg>
)
