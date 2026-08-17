import { ReliabilityChart } from "@/components/ReliabilityChart";
import { ApiError, getModelHealth } from "@/lib/api-client";

export default async function HealthPage() {
  let health = null;
  let error: string | null = null;
  try {
    health = await getModelHealth();
  } catch (caught) {
    error = caught instanceof ApiError ? caught.message : "Unable to load model health.";
  }

  return (
    <div>
      {health && (
        <div className="as-at-banner">
          As at <strong>{health.as_at_date}</strong>. This is a retrospective demonstration, not
          a live operational view.
        </div>
      )}

      {error && (
        <div className="error-panel">
          <strong>Could not load model health.</strong> {error}
        </div>
      )}

      {health && (
        <>
          <h2>Reliability curve</h2>
          <p className="no-alerts-note">
            Development calibration (EXP-009, DEC-058/DEC-059), F1 arm. Faint points are bins
            with too few positive days to be treated as supported evidence on their own.
          </p>
          <ReliabilityChart bins={health.reliability_bins} />
          <table>
            <thead>
              <tr>
                <th>Bin</th>
                <th>Player-days</th>
                <th>Positive days</th>
                <th>Mean prediction</th>
                <th>Observed rate</th>
                <th>Supported</th>
              </tr>
            </thead>
            <tbody>
              {health.reliability_bins.map((bin) => (
                <tr key={bin.reliability_bin}>
                  <td>{bin.reliability_bin}</td>
                  <td>{bin.player_days}</td>
                  <td>{bin.positive_days}</td>
                  <td>{bin.mean_prediction.toFixed(4)}</td>
                  <td>{bin.observed_rate.toFixed(4)}</td>
                  <td>{bin.bin_supported ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h2>Operating points</h2>
          <p className="no-alerts-note">
            Burden and capture for every offered operating point, development (EXP-019) and
            held-out (V1-P5) side by side. Neither figure is shown alone (DEC-062, DEC-063).
          </p>
          <table>
            <thead>
              <tr>
                <th>Review rate</th>
                <th>Source</th>
                <th>Alerts per 100 player-days</th>
                <th>Recall</th>
                <th>False alerts per captured onset</th>
              </tr>
            </thead>
            <tbody>
              {health.operating_points.map((point) => (
                <tr key={`dev-${point.review_rate}`}>
                  <td>{(point.review_rate * 100).toFixed(1)}%</td>
                  <td>Development</td>
                  <td>{point.alerts_per_100_player_days.toFixed(2)}</td>
                  <td>{point.recall !== null ? point.recall.toFixed(3) : "—"}</td>
                  <td>
                    {point.false_alerts_per_captured_onset !== null
                      ? point.false_alerts_per_captured_onset.toFixed(1)
                      : "—"}
                  </td>
                </tr>
              ))}
              {health.held_out_operating_points.map((point) => (
                <tr key={`held-out-${point.review_rate}`} className="alert-row">
                  <td>{(point.review_rate * 100).toFixed(1)}%</td>
                  <td>Held-out (V1-P5)</td>
                  <td>{point.alerts_per_100_player_days.toFixed(2)}</td>
                  <td>{point.recall !== null ? point.recall.toFixed(3) : "—"}</td>
                  <td>
                    {point.false_alerts_per_captured_onset !== null
                      ? point.false_alerts_per_captured_onset.toFixed(1)
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <h2>V1-P5 confirmatory result</h2>
          <p>{health.final_test_result.interpretation}</p>
          <p className="no-alerts-note">
            {health.final_test_result.player_days} held-out player-days,{" "}
            {health.final_test_result.positive_days} positive days
            {health.final_test_result.roc_auc !== null
              ? `, ROC-AUC ${health.final_test_result.roc_auc.toFixed(3)}`
              : ""}
            .
          </p>
          <table>
            <thead>
              <tr>
                <th>Claim</th>
                <th>Statement</th>
                <th>Supported</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {health.final_test_result.claims.map((claim) => (
                <tr key={claim.claim_id} className={claim.supported ? undefined : "alert-row"}>
                  <td>{claim.claim_id}</td>
                  <td>{claim.statement}</td>
                  <td>{claim.supported ? "Yes" : "No"}</td>
                  <td>{claim.evidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="no-alerts-note">{health.final_test_result.c3_explanation}</p>
        </>
      )}
    </div>
  );
}
