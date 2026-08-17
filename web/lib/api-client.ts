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
