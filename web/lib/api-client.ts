// Server-only client for the internal V1-P6 API (DEC-064). Never imported by
// client components: the browser must never call the API directly, since the
// API runs with internal ingress and is reachable only by this service's
// identity in deployment.
import "server-only";

const API_BASE_URL = process.env.PAA_API_BASE_URL ?? "http://localhost:8080";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiGet<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(path, API_BASE_URL);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value) url.searchParams.set(key, value);
  }
  const response = await fetch(url, { cache: "no-store" });
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
  false_alerts_per_captured_onset: number | null;
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
