import type { TeamDataQualityPoint } from "@/lib/api-client";

// Server-rendered inline SVG reporting-coverage series, no client JS or chart library.
export function CoverageChart({ series }: { series: TeamDataQualityPoint[] }) {
  if (series.length === 0) {
    return <p>No coverage history available.</p>;
  }

  const width = 900;
  const height = 200;
  const padding = { top: 12, right: 12, bottom: 28, left: 44 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const xStep = series.length > 1 ? plotWidth / (series.length - 1) : 0;
  const xAt = (index: number) => padding.left + index * xStep;
  const yAt = (value: number) => padding.top + plotHeight - value * plotHeight;

  const linePath = series
    .map(
      (point, index) => `${index === 0 ? "M" : "L"} ${xAt(index)} ${yAt(point.mean_data_completeness)}`,
    )
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Reporting coverage over time">
      <path d={linePath} fill="none" stroke="#2a9d8f" strokeWidth={1.5} />
      <line
        x1={padding.left}
        y1={padding.top + plotHeight}
        x2={width - padding.right}
        y2={padding.top + plotHeight}
        stroke="#999"
      />
      <text x={padding.left} y={height - 6} fontSize={10} fill="#5b6472">
        {series[0].prediction_date}
      </text>
      <text x={width - padding.right} y={height - 6} fontSize={10} fill="#5b6472" textAnchor="end">
        {series[series.length - 1].prediction_date}
      </text>
      <text x={4} y={padding.top + 4} fontSize={10} fill="#5b6472">
        100%
      </text>
      <text x={4} y={padding.top + plotHeight} fontSize={10} fill="#5b6472">
        0%
      </text>
    </svg>
  );
}
