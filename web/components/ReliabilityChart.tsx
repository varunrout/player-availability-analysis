import type { ReliabilityBin } from "@/lib/api-client";

// Server-rendered inline SVG reliability curve: mean prediction vs observed rate per bin,
// with bin player-day counts alongside so a reviewer can judge how much each point rests on.
export function ReliabilityChart({ bins }: { bins: ReliabilityBin[] }) {
  if (bins.length === 0) {
    return <p>No reliability bins available.</p>;
  }

  const width = 500;
  const height = 500;
  const padding = { top: 12, right: 12, bottom: 36, left: 44 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const maxValue = Math.max(...bins.map((bin) => Math.max(bin.mean_prediction, bin.observed_rate))) * 1.1;
  const xAt = (value: number) => padding.left + (value / maxValue) * plotWidth;
  const yAt = (value: number) => padding.top + plotHeight - (value / maxValue) * plotHeight;

  const diagonalPath = `M ${xAt(0)} ${yAt(0)} L ${xAt(maxValue)} ${yAt(maxValue)}`;
  const curvePath = bins
    .map(
      (bin, index) => `${index === 0 ? "M" : "L"} ${xAt(bin.mean_prediction)} ${yAt(bin.observed_rate)}`,
    )
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Reliability curve">
      <path d={diagonalPath} stroke="#999" strokeDasharray="4 3" strokeWidth={1} />
      <line x1={padding.left} y1={padding.top} x2={padding.left} y2={padding.top + plotHeight} stroke="#999" />
      <line
        x1={padding.left}
        y1={padding.top + plotHeight}
        x2={width - padding.right}
        y2={padding.top + plotHeight}
        stroke="#999"
      />
      <path d={curvePath} fill="none" stroke="#1f4e79" strokeWidth={1.5} />
      {bins.map((bin, index) => (
        <circle
          key={index}
          cx={xAt(bin.mean_prediction)}
          cy={yAt(bin.observed_rate)}
          r={bin.bin_supported ? 4 : 2.5}
          fill={bin.bin_supported ? "#1f4e79" : "#b6c4d6"}
        />
      ))}
      <text x={padding.left} y={height - 8} fontSize={10} fill="#5b6472">
        0
      </text>
      <text x={width - padding.right} y={height - 8} fontSize={10} fill="#5b6472" textAnchor="end">
        {maxValue.toFixed(3)} mean predicted probability
      </text>
      <text x={4} y={padding.top + 4} fontSize={10} fill="#5b6472">
        {maxValue.toFixed(3)}
      </text>
      <text x={4} y={padding.top + plotHeight} fontSize={10} fill="#5b6472">
        0 observed rate
      </text>
    </svg>
  );
}
