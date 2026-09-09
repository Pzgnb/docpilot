export function ScoreBar({ value, label }: { value: number; label: string }) {
  const percent = Math.max(0, Math.min(100, value * 100))
  return (
    <div className="score" title={`${label} ${value.toFixed(3)}`}>
      <div className="score-track"><span style={{ width: `${percent}%` }} /></div>
      <span>{value.toFixed(3)}</span>
    </div>
  )
}
