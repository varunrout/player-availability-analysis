import { CoverageChart } from "@/components/CoverageChart";
import { ApiError, getCoveredPeriod, getDataQuality } from "@/lib/api-client";

interface QualityPageProps {
  searchParams: Promise<{
    team_id?: string;
    date?: string;
  }>;
}

export default async function QualityPage({ searchParams }: QualityPageProps) {
  const params = await searchParams;
  const covered = await getCoveredPeriod();
  const teamId = params.team_id ?? covered.team_ids[0];
  const asAtDate = params.date ?? covered.default_as_at_date;

  let quality = null;
  let error: string | null = null;
  try {
    quality = await getDataQuality(teamId, asAtDate);
  } catch (caught) {
    error = caught instanceof ApiError ? caught.message : "Unable to load data quality.";
  }

  const coverageValues = quality
    ? quality.player_coverage_range.map((player) => player.mean_data_completeness)
    : [];
  const minCoverage = coverageValues.length ? Math.min(...coverageValues) : null;
  const maxCoverage = coverageValues.length ? Math.max(...coverageValues) : null;
  const sortedPlayers = quality
    ? [...quality.player_coverage_range].sort(
        (a, b) => a.mean_data_completeness - b.mean_data_completeness,
      )
    : [];

  return (
    <div>
      <div className="as-at-banner">
        As at <strong>{asAtDate}</strong>. Team <strong>{teamId}</strong>. Data covers{" "}
        {covered.covered_date_start} to {covered.covered_date_end}. This is a retrospective
        demonstration, not a live operational view.
      </div>

      <form className="selector-form" action="/quality" method="get">
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
        <button type="submit">Update</button>
      </form>

      {error && (
        <div className="error-panel">
          <strong>Could not load data quality for this team.</strong> {error}
        </div>
      )}

      {quality && (
        <>
          <h2>Reporting coverage over time</h2>
          <p className="no-alerts-note">
            Mean wellness-reporting data completeness across the squad, by day.
          </p>
          <CoverageChart series={quality.coverage_over_time} />

          <h2>Onsets by year</h2>
          <p>{quality.onset_decline_note}</p>
          <table>
            <thead>
              <tr>
                <th>Year</th>
                <th>Represented onsets</th>
                <th>Player-days</th>
              </tr>
            </thead>
            <tbody>
              {quality.onsets_by_year.map((row) => (
                <tr key={row.year}>
                  <td>{row.year}</td>
                  <td>{row.represented_onsets}</td>
                  <td>{row.player_days}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h2>Coverage range across players</h2>
          {minCoverage !== null && maxCoverage !== null && (
            <p className="no-alerts-note">
              Mean data completeness ranges from {(minCoverage * 100).toFixed(0)}% to{" "}
              {(maxCoverage * 100).toFixed(0)}% across {sortedPlayers.length} players on the
              covered period, sorted lowest first below.
            </p>
          )}
          <table>
            <thead>
              <tr>
                <th>Player</th>
                <th>Mean data completeness</th>
              </tr>
            </thead>
            <tbody>
              {sortedPlayers.map((player) => (
                <tr key={player.player_id}>
                  <td>{player.player_id}</td>
                  <td>{(player.mean_data_completeness * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
