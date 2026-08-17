import type { RiskSeriesPoint } from "@/lib/api-client";

// Server-rendered inline SVG, no client JS and no charting library dependency.
// Onset dates are marked explicitly (DEC-064): a vertical marker at the onset date,
// distinct from the forward-looking alert flag on any given day.
export function RiskSeriesChart({
  series,
  threshold,
}: {
  series: RiskSeriesPoint[];
  threshold: number;
}) {
  if (series.length === 0) {
    return <p>No risk history available for this player.</p>;
  }

  const width = 900;
  const height = 220;
  const padding = { top: 12, right: 12, bottom: 28, left: 44 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const maxProbability = Math.max(...series.map((point) => point.predicted_probability), threshold) * 1.15;
  const xStep = series.length > 1 ? plotWidth / (series.length - 1) : 0;

  const xAt = (index: number) => padding.left + index * xStep;
  const yAt = (probability: number) =>
    padding.top + plotHeight - (probability / maxProbability) * plotHeight;

  const linePath = series
    .map((point, index) => `${index === 0 ? "M" : "L"} ${xAt(index)} ${yAt(point.predicted_probability)}`)
    .join(" ");

  const onsetIndices = series
    .map((point, index) => ({ point, index }))
    .filter(({ point }) => point.is_onset_date);
  const alertIndices = series
    .map((point, index) => ({ point, index }))
    .filter(({ point }) => point.alert);

  const firstDate = series[0].prediction_date;
  const lastDate = series[series.length - 1].prediction_date;
  const thresholdY = yAt(threshold);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Predicted risk over time">
      <line
        x1={padding.left}
        y1={thresholdY}
        x2={width - padding.right}
        y2={thresholdY}
        stroke="#d9534f"
        strokeDasharray="4 3"
        strokeWidth={1}
      />
      <text x={width - padding.right} y={thresholdY - 4} textAnchor="end" fontSize={10} fill="#d9534f">
        operating threshold
      </text>

      {onsetIndices.map(({ index }) => (
        <line
          key={`onset-${index}`}
          x1={xAt(index)}
          y1={padding.top}
          x2={xAt(index)}
          y2={padding.top + plotHeight}
          stroke="#333"
          strokeWidth={1.5}
        />
      ))}

      <path d={linePath} fill="none" stroke="#1f4e79" strokeWidth={1.5} />

      {alertIndices.map(({ point, index }) => (
        <circle
          key={`alert-${index}`}
          cx={xAt(index)}
          cy={yAt(point.predicted_probability)}
          r={3}
          fill="#d9534f"
        />
      ))}

      <line
        x1={padding.left}
        y1={padding.top + plotHeight}
        x2={width - padding.right}
        y2={padding.top + plotHeight}
        stroke="#999"
      />
      <text x={padding.left} y={height - 6} fontSize={10} fill="#5b6472">
        {firstDate}
      </text>
      <text x={width - padding.right} y={height - 6} fontSize={10} fill="#5b6472" textAnchor="end">
        {lastDate}
      </text>
      <text x={4} y={padding.top + 4} fontSize={10} fill="#5b6472">
        {maxProbability.toFixed(3)}
      </text>
      <text x={4} y={padding.top + plotHeight} fontSize={10} fill="#5b6472">
        0
      </text>
    </svg>
  );
}
