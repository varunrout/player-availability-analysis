import type { OperatingPointInForce } from "@/lib/api-client";

// DEC-063 fix: the development burden (EXP-019) and the held-out burden (V1-P5,
// DEC-062) must both be shown wherever an operating-point burden is displayed,
// with the held-out figure at least equally prominent — never development alone,
// which would leave a reviewer to encounter an unreconciled, more flattering
// number here than in the model card.
export function OperatingPointBanner({
  operatingPoint,
}: {
  operatingPoint: OperatingPointInForce;
}) {
  return (
    <div className="operating-point-banner">
      <div>
        Operating point: {(operatingPoint.review_rate * 100).toFixed(1)}% review rate,
        probability threshold {operatingPoint.probability_threshold.toFixed(4)}.
      </div>
      {operatingPoint.development_false_alerts_per_captured_onset !== null && (
        <div>
          Development burden:{" "}
          {operatingPoint.development_false_alerts_per_captured_onset.toFixed(1)} false
          alerts per captured onset (EXP-019, pooled rolling-origin evidence).
        </div>
      )}
      {operatingPoint.held_out_false_alerts_per_captured_onset !== null &&
        operatingPoint.held_out_realised_alert_rate !== null && (
          <div className="held-out-burden">
            <strong>Held-out result:</strong> on the locked final-test partition this
            threshold issued alerts on{" "}
            {(operatingPoint.held_out_realised_alert_rate * 100).toFixed(1)}% of
            player-days and cost{" "}
            {operatingPoint.held_out_false_alerts_per_captured_onset.toFixed(1)} false
            alerts per captured onset, measured on{" "}
            {operatingPoint.held_out_represented_onsets} represented onsets (V1-P5,
            DEC-062/DEC-063 — a confirmatory check, not a performance claim).
          </div>
        )}
    </div>
  );
}
