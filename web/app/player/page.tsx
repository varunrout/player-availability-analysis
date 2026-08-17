import Link from "next/link";
import { OperatingPointBanner } from "@/components/OperatingPointBanner";
import { RiskSeriesChart } from "@/components/RiskSeriesChart";
import { ApiError, getCoveredPeriod, getPlayerDetail } from "@/lib/api-client";

interface PlayerPageProps {
  searchParams: Promise<{
    player_id?: string;
    date?: string;
    review_rate?: string;
  }>;
}

export default async function PlayerPage({ searchParams }: PlayerPageProps) {
  const params = await searchParams;
  const covered = await getCoveredPeriod();
  const playerId = params.player_id;
  const asAtDate = params.date ?? covered.default_as_at_date;
  const reviewRate = params.review_rate ?? "0.025";

  if (!playerId) {
    return (
      <div>
        <div className="as-at-banner">
          As at <strong>{asAtDate}</strong>. Data covers {covered.covered_date_start} to{" "}
          {covered.covered_date_end}. This is a retrospective demonstration, not a live
          operational view.
        </div>
        <p>
          Select a player from the <Link href="/squad">squad overview</Link> to see their risk
          history and driver contributions.
        </p>
      </div>
    );
  }

  let detail = null;
  let error: string | null = null;
  try {
    detail = await getPlayerDetail(playerId, asAtDate, reviewRate);
  } catch (caught) {
    error = caught instanceof ApiError ? caught.message : "Unable to load this player.";
  }

  const sortedDrivers = detail
    ? [...detail.driver_contributions].sort((a, b) => b.contribution - a.contribution)
    : [];

  return (
    <div>
      <div className="as-at-banner">
        As at <strong>{asAtDate}</strong>. Player <strong>{playerId}</strong>. Data covers{" "}
        {covered.covered_date_start} to {covered.covered_date_end}. This is a retrospective
        demonstration, not a live operational view.
      </div>

      <form className="selector-form" action="/player" method="get">
        <input type="hidden" name="player_id" value={playerId} />
        <label>
          Date
          <input
            type="date"
            name="date"
            defaultValue={asAtDate}
            min={covered.covered_date_start}
            max={covered.covered_date_end}
          />
        </label>
        <label>
          Review rate
          <select name="review_rate" defaultValue={reviewRate}>
            <option value="0.025">2.5% (default)</option>
            <option value="0.05">5%</option>
          </select>
        </label>
        <button type="submit">Update</button>
      </form>

      {error && (
        <div className="error-panel">
          <strong>Could not load this player.</strong> {error}
        </div>
      )}

      {detail && (
        <>
          <OperatingPointBanner operatingPoint={detail.operating_point} />

          <p>
            Data completeness on {asAtDate}:{" "}
            <strong>{(detail.data_completeness * 100).toFixed(0)}%</strong>
          </p>

          <h2>Risk over time</h2>
          <RiskSeriesChart
            series={detail.risk_series}
            onsetDates={detail.onset_dates}
            threshold={detail.operating_point.probability_threshold}
          />
          <p className="no-alerts-note">
            Solid line: predicted probability. Vertical black lines: onset dates (the day an
            injury episode actually started; never itself a scored day, since a day inside an
            active episode is not eligible for scoring). Red dots: days flagged at the operating
            point in force. Dashed red line: the operating threshold.
          </p>

          <h2>Drivers on {asAtDate}</h2>
          <p className="no-alerts-note">
            Restricted to the eight predictors with constant coefficient sign across every
            estimable fold (EXP-018). daily_load_log1p is not shown: its sign is unstable and it
            is not eligible for display as a driver, per DEC-060.
          </p>
          <table>
            <thead>
              <tr>
                <th>Predictor</th>
                <th>Contribution</th>
              </tr>
            </thead>
            <tbody>
              {sortedDrivers.map((driver) => (
                <tr key={driver.predictor}>
                  <td>{driver.predictor}</td>
                  <td style={{ color: driver.contribution > 0 ? "#d9534f" : "#1f4e79" }}>
                    {driver.contribution >= 0 ? "+" : ""}
                    {driver.contribution.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
