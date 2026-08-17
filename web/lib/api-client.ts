// Server-only client for the internal V1-P6 API (DEC-064). Never imported by
// client components: the browser must never call the API directly, since the
// API runs with internal ingress and is reachable only by this service's
// identity in deployment.
import "server-only";

const API_BASE_URL = process.env.PAA_API_BASE_URL ?? "http://localhost:8080";

// Cloud Run's internal-ingress API requires an authenticated invocation, not just
// network reachability. When deployed, the web service's own identity must present
// a Google-signed OIDC token scoped to the API's URL; the Cloud Run/GCE metadata
// server issues that token for the service's own runtime identity. Local dev talks
// to a plain uvicorn process and skips this entirely.
const METADATA_IDENTITY_URL =
  "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchIdentityToken(audience: string): Promise<string | null> {
  if (process.env.PAA_USE_METADATA_IDENTITY_TOKEN !== "true") {
    return null;
  }
  const url = `${METADATA_IDENTITY_URL}?audience=${encodeURIComponent(audience)}`;
  const response = await fetch(url, { headers: { "Metadata-Flavor": "Google" } });
  if (!response.ok) {
    throw new Error(`Could not obtain an identity token for the API (${response.status})`);
  }
  return response.text();
}

async function apiGet<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(path, API_BASE_URL);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value) url.searchParams.set(key, value);
  }
  const token = await fetchIdentityToken(API_BASE_URL);
  const response = await fetch(url, {
    cache: "no-store",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!response.ok) {
    throw new ApiError(response.status, `${path} returned ${response.status}`);
  }
  return (await response.json()) as T;
}

export interface CoveredPeriod {
  team_ids: string[];
  covered_date_start: string;
  covered_date_end: string;
  default_as_at_date: string;
}

export interface OperatingPointInForce {
  review_rate: number;
  probability_threshold: number;
  development_false_alerts_per_captured_onset: number | null;
  held_out_realised_alert_rate: number | null;
  held_out_false_alerts_per_captured_onset: number | null;
  held_out_represented_onsets: number | null;
}

export interface PlayerRiskRow {
  player_id: string;
  predicted_probability: number;
  rank_within_team_day: number;
  alert: boolean;
  data_completeness: number;
}

export interface SquadOverview {
  team_id: string;
  as_at_date: string;
  operating_point: OperatingPointInForce;
  players: PlayerRiskRow[];
}

export interface DriverContribution {
  predictor: string;
  contribution: number;
}

export interface RiskSeriesPoint {
  prediction_date: string;
  predicted_probability: number;
  alert: boolean;
}

export interface PlayerDetail {
  player_id: string;
  team_id: string;
  as_at_date: string;
  operating_point: OperatingPointInForce;
  risk_series: RiskSeriesPoint[];
  onset_dates: string[];
  driver_contributions: DriverContribution[];
  data_completeness: number;
}

export interface TeamDataQualityPoint {
  prediction_date: string;
  mean_data_completeness: number;
}

export interface PlayerCoverage {
  player_id: string;
  mean_data_completeness: number;
}

export interface OnsetsByYear {
  year: number;
  represented_onsets: number;
  player_days: number;
}

export interface DataQuality {
  team_id: string;
  as_at_date: string;
  coverage_over_time: TeamDataQualityPoint[];
  player_coverage_range: PlayerCoverage[];
  onsets_by_year: OnsetsByYear[];
  onset_decline_note: string;
  onset_reconciliation_note: string;
}

export interface CalibrationReference {
  mean_prediction: number;
  observed_rate: number;
  calibration_intercept: number | null;
  calibration_slope: number | null;
  brier_score: number;
  log_loss: number;
}

export interface ReliabilityBin {
  reliability_bin: number;
  player_days: number;
  positive_days: number;
  mean_prediction: number;
  observed_rate: number;
  bin_supported: boolean;
}

export interface OperatingPointBurden {
  review_rate: number;
  alerts_per_100_player_days: number;
  recall: number | null;
  false_alerts_per_captured_onset: number | null;
}

export interface FinalTestClaim {
  claim_id: string;
  statement: string;
  supported: boolean;
  evidence: string;
}

export interface FinalTestResult {
  player_days: number;
  positive_days: number;
  roc_auc: number | null;
  claims: FinalTestClaim[];
  interpretation: string;
  c3_explanation: string;
}

export interface ModelHealth {
  as_at_date: string;
  calibration: CalibrationReference;
  reliability_bins: ReliabilityBin[];
  operating_points: OperatingPointBurden[];
  held_out_operating_points: OperatingPointBurden[];
  final_test_result: FinalTestResult;
}

export function getCoveredPeriod(): Promise<CoveredPeriod> {
  return apiGet<CoveredPeriod>("/covered-period");
}

export function getSquadOverview(
  teamId: string,
  date?: string,
  reviewRate?: string,
): Promise<SquadOverview> {
  return apiGet<SquadOverview>("/squad-overview", {
    team_id: teamId,
    date: date ?? "",
    review_rate: reviewRate ?? "",
  });
}

export function getPlayerDetail(
  playerId: string,
  date?: string,
  reviewRate?: string,
): Promise<PlayerDetail> {
  return apiGet<PlayerDetail>("/player-detail", {
    player_id: playerId,
    date: date ?? "",
    review_rate: reviewRate ?? "",
  });
}

export function getDataQuality(teamId: string, date?: string): Promise<DataQuality> {
  return apiGet<DataQuality>("/data-quality", { team_id: teamId, date: date ?? "" });
}

export function getModelHealth(): Promise<ModelHealth> {
  return apiGet<ModelHealth>("/model-health");
}
