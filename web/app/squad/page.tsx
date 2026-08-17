import { ApiError, getCoveredPeriod, getSquadOverview } from "@/lib/api-client";

interface SquadPageProps {
  searchParams: Promise<{
    team_id?: string;
    date?: string;
    review_rate?: string;
  }>;
}

export default async function SquadPage({ searchParams }: SquadPageProps) {
  const params = await searchParams;
  const covered = await getCoveredPeriod();
  const teamId = params.team_id ?? covered.team_ids[0];
  const asAtDate = params.date ?? covered.default_as_at_date;
  const reviewRate = params.review_rate ?? "0.025";

  let overview = null;
  let error: string | null = null;
  try {
    overview = await getSquadOverview(teamId, asAtDate, reviewRate);
  } catch (caught) {
    error = caught instanceof ApiError ? caught.message : "Unable to load the squad overview.";
  }

  return (
    <div>
      <div className="as-at-banner">
        As at <strong>{asAtDate}</strong>. Data covers {covered.covered_date_start} to{" "}
        {covered.covered_date_end}. This is a retrospective demonstration, not a live
        operational view.
      </div>

      <form className="selector-form" action="/squad" method="get">
        <label>
          Team
          <select name="team_id" defaultValue={teamId}>
            {covered.team_ids.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </label>
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
          <strong>Could not load this view.</strong> {error}
        </div>
      )}

      {overview && (
        <>
          <div className="operating-point-banner">
            Operating point: {(overview.operating_point.review_rate * 100).toFixed(1)}% review
            rate, probability threshold {overview.operating_point.probability_threshold.toFixed(4)}
            .{" "}
            {overview.operating_point.false_alerts_per_captured_onset !== null && (
              <>
                Measured burden:{" "}
                {overview.operating_point.false_alerts_per_captured_onset.toFixed(1)} false
                alerts per captured onset (development evidence).
              </>
            )}
          </div>

          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Player</th>
                <th>Predicted probability</th>
                <th>Alert</th>
                <th>Data completeness</th>
              </tr>
            </thead>
            <tbody>
              {overview.players.map((player) => (
                <tr key={player.player_id} className={player.alert ? "alert-row" : undefined}>
                  <td>{player.rank_within_team_day}</td>
                  <td>{player.player_id}</td>
                  <td>{player.predicted_probability.toFixed(4)}</td>
                  <td>{player.alert ? <span className="alert-tag">Alert</span> : "—"}</td>
                  <td>{(player.data_completeness * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>

          {overview.players.every((player) => !player.alert) && (
            <p className="no-alerts-note">
              No alerts issued for this team on this date at this operating point. This is
              expected behaviour for an honest alerting rule, not a gap in coverage.
            </p>
          )}
        </>
      )}
    </div>
  );
}
