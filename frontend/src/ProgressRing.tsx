export default function ProgressRing({ value }: { value: number }) {
  const percent = Math.max(0, Math.min(100, value));
  return <div className="progress-ring" role="img" aria-label={`${percent}% of sections complete`}>
    <svg viewBox="0 0 100 100" aria-hidden="true">
      <circle className="ring-track" cx="50" cy="50" r="40" />
      <circle className="ring-value" cx="50" cy="50" r="40" pathLength="100" strokeDasharray={`${percent} 100`} />
    </svg>
    <strong>{percent}<small>%</small></strong>
  </div>;
}
