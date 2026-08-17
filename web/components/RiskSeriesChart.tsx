import type { RiskSeriesPoint } from "@/lib/api-client";

function daysBetween(start: string, end: string): number {
  return (Date.parse(end) - Date.parse(start)) / (1000 * 60 * 60 * 24);
}

// Server-rendered inline SVG, no client JS and no charting library dependency.
// Onset dates are marked explicitly (DEC-064) as vertical markers positioned by
// calendar date, not by series index: an onset day is never itself a scored
// player-day (it is always inside an active episode, which is ineligible for
// scoring), so it can never correspond to a point on the probability line.
export function RiskSeriesChart({
  series,
  onsetDates,
  threshold,
}: {
  series: RiskSeriesPoint[];
  onsetDates: string[];
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

  const firstDate = series[0].prediction_date;
  const lastDate = series[series.length - 1].prediction_date;
  const totalDays = Math.max(daysBetween(firstDate, lastDate), 1);

  const xAtDate = (dateStr: string) =>
    padding.left + (daysBetween(firstDate, dateStr) / totalDays) * plotWidth;
  const yAt = (probability: number) =>
    padding.top + plotHeight - (probability / maxProbability) * plotHeight;

  const linePath = series
    .map((point, index) => `${index === 0 ? "M" : "L"} ${xAtDate(point.prediction_date)} ${yAt(point.predicted_probability)}`)
    .join(" ");

  const alertPoints = series.filter((point) => point.alert);
  const onsetMarkers = onsetDates.filter((d) => d >= firstDate && d <= lastDate);

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

      {onsetMarkers.map((onsetDate) => (
        <line
          key={`onset-${onsetDate}`}
          x1={xAtDate(onsetDate)}
          y1={padding.top}
          x2={xAtDate(onsetDate)}
          y2={padding.top + plotHeight}
          stroke="#333"
          strokeWidth={1.5}
        />
      ))}

      <path d={linePath} fill="none" stroke="#1f4e79" strokeWidth={1.5} />

      {alertPoints.map((point) => (
        <circle
          key={`alert-${point.prediction_date}`}
          cx={xAtDate(point.prediction_date)}
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
