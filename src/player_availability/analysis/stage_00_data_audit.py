"""Stage 0 inventory, key, schema, temporal and reconciliation audit."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import polars as pl
from google.cloud import bigquery
from google.cloud.storage import Bucket, Client  # type: ignore[import-untyped]
from matplotlib.colors import ListedColormap
from matplotlib.figure import Figure

SOURCE_PREFIX = "subjective/soccermon/zenodo-10033832"
ARCHIVE_PREFIX = "soccermon/zenodo-10033832/"
QUALITY_PREFIX = f"metadata/data_quality_reports/{SOURCE_PREFIX}"


@dataclass(frozen=True, slots=True)
class RelationContract:
    name: str
    layer: str
    grain: str
    primary_key: tuple[str, ...]
    date_column: str
    columns: tuple[tuple[str, str], ...]

    @property
    def object_name(self) -> str:
        return f"{self.layer}/{SOURCE_PREFIX}/{self.name}.parquet"


@dataclass(frozen=True, slots=True)
class Stage00AuditResult:
    """All retained tables and summary values from one Stage 0 run."""

    tables: dict[str, pl.DataFrame]
    summary: dict[str, Any]


COMMON_EVENT_COLUMNS = (
    ("player_id", "String"),
    ("team_id", "String"),
    ("event_date", "Date"),
    ("event_type", "String"),
    ("source_file", "String"),
    ("source_row_number", "Int64"),
    ("source_payload_json", "String"),
)
SILVER_EVENT_COLUMNS = (("event_id", "String"), *COMMON_EVENT_COLUMNS)
RELATION_CONTRACTS = (
    RelationContract(
        "daily_metrics",
        "bronze",
        "player x observation date x metric",
        ("player_id", "observation_date", "metric_name"),
        "observation_date",
        (
            ("player_id", "String"),
            ("team_id", "String"),
            ("observation_date", "Date"),
            ("metric_name", "String"),
            ("value", "Float64"),
            ("source_file", "String"),
            ("source_row_number", "Int64"),
        ),
    ),
    RelationContract(
        "training_sessions",
        "bronze",
        "source player session",
        ("player_id", "source_file", "source_record_index"),
        "session_date",
        (
            ("player_id", "String"),
            ("team_id", "String"),
            ("session_date", "Date"),
            ("duration_minutes", "Float64"),
            ("rpe", "Float64"),
            ("srpe", "Float64"),
            ("source_file", "String"),
            ("source_record_index", "Int64"),
        ),
    ),
    *(
        RelationContract(
            name,
            "bronze",
            "source event report",
            ("source_file", "source_row_number"),
            "event_date",
            COMMON_EVENT_COLUMNS,
        )
        for name in ("injury_reports", "illness_reports", "game_performance_reports")
    ),
    RelationContract(
        "player_registry",
        "silver",
        "player",
        ("player_id",),
        "observation_start",
        (
            ("player_id", "String"),
            ("team_id", "String"),
            ("observation_start", "Date"),
            ("observation_end", "Date"),
            ("observed_day_count", "UInt32"),
            ("first_session_date", "Date"),
            ("last_session_date", "Date"),
            ("session_count", "UInt32"),
            ("first_event_date", "Date"),
            ("last_event_date", "Date"),
            ("event_count", "UInt32"),
        ),
    ),
    RelationContract(
        "training_load_daily",
        "silver",
        "player x report date",
        ("player_id", "report_date"),
        "report_date",
        (
            ("player_id", "String"),
            ("team_id", "String"),
            ("report_date", "Date"),
            ("acwr", "Float64"),
            ("atl", "Float64"),
            ("ctl28", "Float64"),
            ("ctl42", "Float64"),
            ("daily_load", "Float64"),
            ("monotony", "Float64"),
            ("strain", "Float64"),
            ("weekly_load", "Float64"),
        ),
    ),
    RelationContract(
        "wellness_daily",
        "silver",
        "player x report date",
        ("player_id", "report_date"),
        "report_date",
        (
            ("player_id", "String"),
            ("team_id", "String"),
            ("report_date", "Date"),
            ("fatigue", "Float64"),
            ("mood", "Float64"),
            ("readiness", "Float64"),
            ("sleep_duration", "Float64"),
            ("sleep_quality", "Float64"),
            ("soreness", "Float64"),
            ("stress", "Float64"),
            ("wellness_metric_count", "Int8"),
            ("wellness_report_present", "Boolean"),
        ),
    ),
    RelationContract(
        "training_sessions",
        "silver",
        "canonical player session",
        ("session_id",),
        "session_date",
        (
            ("session_id", "String"),
            ("player_id", "String"),
            ("team_id", "String"),
            ("session_date", "Date"),
            ("duration_minutes", "Float64"),
            ("rpe", "Float64"),
            ("srpe", "Float64"),
            ("source_file", "String"),
            ("source_record_index", "Int64"),
        ),
    ),
    *(
        RelationContract(
            name,
            "silver",
            "canonical event report",
            ("event_id",),
            "event_date",
            SILVER_EVENT_COLUMNS,
        )
        for name in ("injury_reports", "illness_reports", "game_performance_reports")
    ),
    RelationContract(
        "injury_episodes",
        "silver",
        "self-reported injury episode",
        ("episode_id",),
        "episode_start",
        (
            ("episode_id", "String"),
            ("player_id", "String"),
            ("team_id", "String"),
            ("raw_location", "String"),
            ("episode_start", "Date"),
            ("episode_end", "Date"),
            ("component_report_count", "Int64"),
            ("max_severity", "String"),
            ("episode_gap_days", "Int64"),
        ),
    ),
    RelationContract(
        "player_day_labels",
        "gold",
        "player x prediction date",
        ("player_id", "prediction_date"),
        "prediction_date",
        (
            ("player_id", "String"),
            ("team_id", "String"),
            ("prediction_date", "Date"),
            ("prediction_cutoff", "String"),
            ("observation_end", "Date"),
            ("active_injury_episode", "Boolean"),
            ("label_complete_3d", "Boolean"),
            ("injury_next_3d", "Boolean"),
            ("eligible_new_onset_3d", "Boolean"),
            ("label_complete_7d", "Boolean"),
            ("injury_next_7d", "Boolean"),
            ("eligible_new_onset_7d", "Boolean"),
            ("label_complete_14d", "Boolean"),
            ("injury_next_14d", "Boolean"),
            ("eligible_new_onset_14d", "Boolean"),
        ),
    ),
    RelationContract(
        "player_day_features",
        "gold",
        "player x prediction date",
        ("player_id", "prediction_date"),
        "prediction_date",
        (
            ("player_id", "String"),
            ("team_id", "String"),
            ("prediction_date", "Date"),
            ("prediction_cutoff", "String"),
            ("observation_end", "Date"),
            ("active_injury_episode", "Boolean"),
            ("label_complete_3d", "Boolean"),
            ("injury_next_3d", "Boolean"),
            ("eligible_new_onset_3d", "Boolean"),
            ("label_complete_7d", "Boolean"),
            ("injury_next_7d", "Boolean"),
            ("eligible_new_onset_7d", "Boolean"),
            ("label_complete_14d", "Boolean"),
            ("injury_next_14d", "Boolean"),
            ("eligible_new_onset_14d", "Boolean"),
            ("feature_version", "String"),
            ("feature_timestamp", "Date"),
            ("daily_load", "Float64"),
            ("fatigue", "Float64"),
            ("readiness", "Float64"),
            ("wellness_report_present", "Boolean"),
            ("wellness_metric_count", "Int64"),
            ("session_count", "Int64"),
            ("session_duration_minutes", "Float64"),
            ("session_srpe", "Float64"),
            *((f"daily_load_sum_{window}d", "Float64") for window in (3, 7, 14, 28)),
            *((f"session_duration_sum_{window}d", "Float64") for window in (3, 7, 14, 28)),
            *((f"session_srpe_sum_{window}d", "Float64") for window in (3, 7, 14, 28)),
            *((f"fatigue_mean_{window}d", "Float64") for window in (3, 7, 14, 28)),
            *((f"readiness_mean_{window}d", "Float64") for window in (3, 7, 14, 28)),
            ("daily_load_baseline_mean_prior", "Float64"),
            ("daily_load_zscore_prior", "Float64"),
            ("fatigue_baseline_mean_prior", "Float64"),
            ("fatigue_zscore_prior", "Float64"),
            ("readiness_baseline_mean_prior", "Float64"),
            ("readiness_zscore_prior", "Float64"),
        ),
    ),
)


def load_stage_00_from_gcp(
    *,
    project_id: str,
    data_bucket: str,
    archive_bucket: str,
    core_dataset: str,
) -> Stage00AuditResult:
    """Read compact project products and execute the shared Stage 0 audit."""
    storage_client = Client(project=project_id)
    frames: dict[str, pl.DataFrame] = {}
    object_rows: list[dict[str, Any]] = []
    data_bucket_ref = storage_client.bucket(data_bucket)
    archive_bucket_ref = storage_client.bucket(archive_bucket)
    for contract in RELATION_CONTRACTS:
        blob = data_bucket_ref.blob(contract.object_name)
        blob.reload()
        frames[_relation_key(contract)] = pl.read_parquet(BytesIO(blob.download_as_bytes()))
    prefixes = (
        f"raw/{SOURCE_PREFIX}/",
        f"bronze/{SOURCE_PREFIX}/",
        f"silver/{SOURCE_PREFIX}/",
        f"gold/{SOURCE_PREFIX}/",
        f"{QUALITY_PREFIX}/",
    )
    for prefix in prefixes:
        object_rows.extend(
            _object_rows(data_bucket, storage_client.list_blobs(data_bucket_ref, prefix=prefix))
        )
    object_rows.extend(
        _object_rows(
            archive_bucket,
            storage_client.list_blobs(archive_bucket_ref, prefix=ARCHIVE_PREFIX),
        )
    )
    quality_reports = _load_quality_reports(data_bucket_ref)
    provenance = _load_provenance(project_id, core_dataset)
    return run_stage_00_audit(
        frames=frames,
        object_inventory=pl.DataFrame(object_rows, infer_schema_length=None),
        quality_reports=quality_reports,
        provenance=provenance,
    )


def run_stage_00_audit(
    *,
    frames: dict[str, pl.DataFrame],
    object_inventory: pl.DataFrame,
    quality_reports: dict[str, Any],
    provenance: dict[str, Any],
) -> Stage00AuditResult:
    """Audit supplied relations without performing outcome or feature EDA."""
    missing_relations = {_relation_key(contract) for contract in RELATION_CONTRACTS} - set(frames)
    if missing_relations:
        raise ValueError(f"Missing Stage 0 relations: {sorted(missing_relations)}")
    relation_inventory = _relation_inventory(frames, object_inventory)
    schema_inventory = _schema_inventory(frames)
    key_integrity = _key_integrity(frames)
    temporal_coverage = _temporal_coverage(frames)
    layer_reconciliation = _layer_reconciliation(
        frames, quality_reports, provenance, object_inventory
    )
    audit_findings = _audit_findings(
        frames,
        schema_inventory,
        key_integrity,
        temporal_coverage,
        layer_reconciliation,
    )
    failures = audit_findings.filter(pl.col("status") == "FAIL").height
    warnings = audit_findings.filter(pl.col("status") == "WARNING").height
    tables = {
        "object_inventory": object_inventory.sort("bucket", "object_name"),
        "relation_inventory": relation_inventory,
        "schema_inventory": schema_inventory,
        "key_integrity": key_integrity,
        "temporal_coverage": temporal_coverage,
        "layer_reconciliation": layer_reconciliation,
        "audit_findings": audit_findings,
        "player_registry_coverage": frames["silver.player_registry"].select(
            "player_id", "team_id", "observation_start", "observation_end", "observed_day_count"
        ),
        "gold_player_date_coverage": frames["gold.player_day_labels"].select(
            "player_id", "prediction_date"
        ),
    }
    return Stage00AuditResult(
        tables=tables,
        summary={
            "stage": "00_data_audit",
            "status": "PASS" if failures == 0 else "FAIL",
            "relation_count": len(RELATION_CONTRACTS),
            "object_count": object_inventory.height,
            "finding_count": audit_findings.height,
            "warning_count": warnings,
            "failure_count": failures,
            "generated_at_utc": datetime.now(UTC).isoformat(),
        },
    )


def build_stage_00_figures(result: Stage00AuditResult) -> dict[str, Figure]:
    """Build Stage 0 figures from audited tables without writing files."""
    figures: dict[str, Figure] = {}
    inventory = result.tables["relation_inventory"].sort("row_count")
    fig, axis = plt.subplots(figsize=(10, 6))
    labels = [
        f"{layer}/{name}" for layer, name in inventory.select("layer", "relation").iter_rows()
    ]
    axis.barh(labels, inventory.get_column("row_count"), color="#287271")
    axis.set_xscale("log")
    axis.set_xlabel("Rows (log scale)")
    axis.set_title("Compact relation row counts")
    fig.tight_layout()
    figures["relation_row_counts"] = fig

    registry = result.tables["player_registry_coverage"]
    fig, axis = plt.subplots(figsize=(9, 5))
    observed_days = registry.get_column("observed_day_count")
    minimum_days = observed_days.min()
    maximum_days = observed_days.max()
    assert isinstance(minimum_days, int)
    assert isinstance(maximum_days, int)
    axis.hist(
        observed_days,
        bins=[value - 0.5 for value in range(minimum_days, maximum_days + 2)],
        color="#E76F51",
        edgecolor="white",
    )
    axis.set_xlim(minimum_days - 0.5, maximum_days + 0.5)
    axis.set_xlabel("Observed player-days")
    axis.set_ylabel("Players")
    axis.set_title("Player observation lengths")
    fig.tight_layout()
    figures["player_observation_lengths"] = fig

    coverage = result.tables["gold_player_date_coverage"]
    players = coverage.get_column("player_id").unique(maintain_order=True).to_list()
    dates = coverage.get_column("prediction_date").unique().sort().to_list()
    player_index = {player: index for index, player in enumerate(players)}
    date_index = {day: index for index, day in enumerate(dates)}
    matrix = [[0 for _ in dates] for _ in players]
    for row in coverage.iter_rows(named=True):
        matrix[player_index[row["player_id"]]][date_index[row["prediction_date"]]] = 1
    fig, axis = plt.subplots(figsize=(12, 6))
    coverage_cmap = ListedColormap(["#F4F1DE", "#287271"])
    axis.imshow(
        matrix,
        aspect="auto",
        interpolation="nearest",
        cmap=coverage_cmap,
        vmin=0,
        vmax=1,
    )
    axis.set_xlabel("Calendar day index")
    axis.set_ylabel("Player index")
    axis.set_title("Gold player-date coverage")
    fig.tight_layout()
    figures["player_date_coverage"] = fig
    return figures


def write_stage_00_outputs(result: Stage00AuditResult, output_root: Path) -> None:
    """Persist the canonical Stage 0 script outputs."""
    directories = {
        name: output_root / name for name in ("figures", "tables", "reports", "metadata")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    for name, table in result.tables.items():
        if name in {"player_registry_coverage", "gold_player_date_coverage"}:
            continue
        table.write_csv(directories["tables"] / f"{name}.csv")
    for name, figure in build_stage_00_figures(result).items():
        figure.savefig(directories["figures"] / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(figure)
    (directories["metadata"] / "stage_00_run_manifest.json").write_text(
        json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (directories["reports"] / "STAGE_00_DATA_AUDIT.md").write_text(
        _render_report(result), encoding="utf-8"
    )


def _relation_inventory(
    frames: dict[str, pl.DataFrame], object_inventory: pl.DataFrame
) -> pl.DataFrame:
    object_lookup = {str(row["object_name"]): row for row in object_inventory.iter_rows(named=True)}
    rows: list[dict[str, Any]] = []
    for contract in RELATION_CONTRACTS:
        frame = frames[_relation_key(contract)]
        metadata = object_lookup.get(contract.object_name, {})
        rows.append(
            {
                "layer": contract.layer,
                "relation": contract.name,
                "grain": contract.grain,
                "primary_key": ", ".join(contract.primary_key),
                "row_count": frame.height,
                "column_count": frame.width,
                "player_count": _n_unique(frame, "player_id"),
                "team_count": _n_unique(frame, "team_id"),
                "min_date": _date_value(frame, contract.date_column, "min"),
                "max_date": _date_value(
                    frame,
                    "observation_end"
                    if contract.name == "player_registry"
                    else contract.date_column,
                    "max",
                ),
                "size_bytes": metadata.get("size_bytes"),
                "generation": metadata.get("generation"),
                "gcs_uri": metadata.get("gcs_uri"),
            }
        )
    return pl.DataFrame(rows, infer_schema_length=None).sort("layer", "relation")


def _schema_inventory(frames: dict[str, pl.DataFrame]) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for contract in RELATION_CONTRACTS:
        frame = frames[_relation_key(contract)]
        actual = {name: str(dtype) for name, dtype in frame.schema.items()}
        expected = dict(contract.columns)
        for column in sorted(set(actual) | set(expected)):
            expected_dtype = expected.get(column)
            actual_dtype = actual.get(column)
            rows.append(
                {
                    "layer": contract.layer,
                    "relation": contract.name,
                    "column": column,
                    "expected_dtype": expected_dtype,
                    "actual_dtype": actual_dtype,
                    "status": "PASS" if expected_dtype == actual_dtype else "FAIL",
                }
            )
    return pl.DataFrame(rows, infer_schema_length=None).sort("layer", "relation", "column")


def _key_integrity(frames: dict[str, pl.DataFrame]) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for contract in RELATION_CONTRACTS:
        frame = frames[_relation_key(contract)]
        null_key_rows = frame.filter(
            pl.any_horizontal([pl.col(key).is_null() for key in contract.primary_key])
        ).height
        duplicate_groups = (
            frame.group_by(contract.primary_key).len().filter(pl.col("len") > 1).height
        )
        rows.append(
            {
                "layer": contract.layer,
                "relation": contract.name,
                "primary_key": ", ".join(contract.primary_key),
                "null_key_rows": null_key_rows,
                "duplicate_key_groups": duplicate_groups,
                "status": "PASS" if null_key_rows == 0 and duplicate_groups == 0 else "FAIL",
            }
        )
    return pl.DataFrame(rows).sort("layer", "relation")


def _temporal_coverage(frames: dict[str, pl.DataFrame]) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for contract in RELATION_CONTRACTS:
        frame = frames[_relation_key(contract)]
        if "player_id" not in frame.columns or contract.date_column not in frame.columns:
            continue
        if contract.name == "player_registry":
            grouped = frame.select(
                "player_id",
                pl.col("observation_start").alias("start_date"),
                pl.col("observation_end").alias("end_date"),
                pl.col("observed_day_count").alias("unique_dates"),
            )
        else:
            grouped = frame.group_by("player_id").agg(
                pl.min(contract.date_column).alias("start_date"),
                pl.max(contract.date_column).alias("end_date"),
                pl.n_unique(contract.date_column).alias("unique_dates"),
            )
        for item in grouped.iter_rows(named=True):
            start = item["start_date"]
            end = item["end_date"]
            assert isinstance(start, date)
            assert isinstance(end, date)
            span_days = (end - start).days + 1
            rows.append(
                {
                    "layer": contract.layer,
                    "relation": contract.name,
                    "player_id": item["player_id"],
                    "start_date": start,
                    "end_date": end,
                    "unique_dates": item["unique_dates"],
                    "span_days": span_days,
                    "unobserved_span_days": span_days - int(item["unique_dates"]),
                }
            )
    return pl.DataFrame(rows, infer_schema_length=None).sort("layer", "relation", "player_id")


def _layer_reconciliation(
    frames: dict[str, pl.DataFrame],
    quality_reports: dict[str, Any],
    provenance: dict[str, Any],
    objects: pl.DataFrame,
) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []

    def compare(check_id: str, description: str, observed: object, expected: object) -> None:
        rows.append(
            {
                "check_id": check_id,
                "description": description,
                "observed": str(observed),
                "expected": str(expected),
                "status": "PASS" if observed == expected else "FAIL",
            }
        )

    bronze = quality_reports["bronze_ingestion"]
    for name, expected in bronze["row_counts"].items():
        compare(
            f"quality_bronze_{name}",
            f"Bronze {name} row count matches its quality report",
            frames[f"bronze.{name}"].height,
            int(expected),
        )
    silver = quality_reports["silver_transformation"]
    for name, expected in silver["row_counts"].items():
        compare(
            f"quality_silver_{name}",
            f"Silver {name} row count matches its quality report",
            frames[f"silver.{name}"].height,
            int(expected),
        )
    compare(
        "quality_injury_episodes",
        "Injury episode count matches its quality report",
        frames["silver.injury_episodes"].height,
        int(quality_reports["injury_episodes"]["episode_count"]),
    )
    compare(
        "quality_player_day_labels",
        "Gold label row count matches its quality report",
        frames["gold.player_day_labels"].height,
        int(quality_reports["player_day_labels"]["player_day_rows"]),
    )
    compare(
        "quality_player_day_features",
        "Gold feature row count matches its quality report",
        frames["gold.player_day_features"].height,
        int(quality_reports["player_day_features"]["row_count"]),
    )
    label_keys = frames["gold.player_day_labels"].select("player_id", "prediction_date")
    feature_keys = frames["gold.player_day_features"].select("player_id", "prediction_date")
    compare(
        "gold_key_identity",
        "Gold labels and features have identical ordered keys",
        feature_keys.equals(label_keys),
        True,
    )
    labels = frames["gold.player_day_labels"]
    compare(
        "gold_label_identity",
        "Gold feature product preserves all label columns exactly",
        frames["gold.player_day_features"].select(labels.columns).equals(labels),
        True,
    )
    registry_players = set(frames["silver.player_registry"].get_column("player_id").to_list())
    for key, frame in sorted(frames.items()):
        if "player_id" in frame.columns:
            unknown = set(frame.get_column("player_id").unique().to_list()) - registry_players
            compare(
                f"registry_{key}",
                f"{key} players are present in the silver registry",
                len(unknown),
                0,
            )
    raw_object_count = objects.filter(
        pl.col("object_name").str.starts_with(f"raw/{SOURCE_PREFIX}/")
    ).height
    compare(
        "raw_object_count",
        "Raw staging has 19 source members plus one manifest",
        raw_object_count,
        20,
    )
    compare(
        "bq_run_status",
        "Latest SoccerMon ingestion run succeeded",
        provenance.get("status"),
        "SUCCESS",
    )
    compare(
        "bq_error_count",
        "Latest SoccerMon ingestion run has no errors",
        int(provenance.get("error_count", -1)),
        0,
    )
    compare(
        "bq_source_file_count",
        "BigQuery provenance has one row per source member",
        int(provenance.get("source_file_count", -1)),
        19,
    )
    bronze_written = sum(frames[f"bronze.{name}"].height for name in bronze["row_counts"])
    compare(
        "bq_records_written",
        "BigQuery records_written reconciles to bronze outputs",
        int(provenance.get("records_written", -1)),
        bronze_written,
    )
    return pl.DataFrame(rows).sort("check_id")


def _audit_findings(
    frames: dict[str, pl.DataFrame],
    schema: pl.DataFrame,
    keys: pl.DataFrame,
    temporal: pl.DataFrame,
    reconciliation: pl.DataFrame,
) -> pl.DataFrame:
    rows: list[dict[str, str]] = []

    def finding(check_id: str, scope: str, status: str, message: str) -> None:
        rows.append({"check_id": check_id, "scope": scope, "status": status, "message": message})

    schema_failures = schema.filter(pl.col("status") == "FAIL").height
    finding(
        "schema_contracts",
        "all relations",
        "PASS" if schema_failures == 0 else "FAIL",
        f"{schema_failures} schema mismatches",
    )
    key_failures = keys.filter(pl.col("status") == "FAIL").height
    finding(
        "primary_keys",
        "all relations",
        "PASS" if key_failures == 0 else "FAIL",
        f"{key_failures} relation key failures",
    )
    reconciliation_failures = reconciliation.filter(pl.col("status") == "FAIL").height
    finding(
        "layer_reconciliation",
        "all layers",
        "PASS" if reconciliation_failures == 0 else "FAIL",
        f"{reconciliation_failures} reconciliation failures",
    )
    registry = frames["silver.player_registry"]
    invalid_registry = registry.filter(
        pl.col("observation_end") < pl.col("observation_start")
    ).height
    finding(
        "registry_date_order",
        "silver.player_registry",
        "PASS" if invalid_registry == 0 else "FAIL",
        f"{invalid_registry} players end before they start",
    )
    episodes = frames["silver.injury_episodes"]
    invalid_episodes = episodes.filter(pl.col("episode_end") < pl.col("episode_start")).height
    finding(
        "episode_date_order",
        "silver.injury_episodes",
        "PASS" if invalid_episodes == 0 else "FAIL",
        f"{invalid_episodes} episodes end before they start",
    )
    gold_temporal = temporal.filter(pl.col("relation") == "player_day_labels")
    gold_gaps = int(gold_temporal.get_column("unobserved_span_days").sum())
    finding(
        "gold_calendar_continuity",
        "gold.player_day_labels",
        "PASS" if gold_gaps == 0 else "FAIL",
        f"{gold_gaps} missing player-days inside observed spans",
    )
    session_gaps = (
        temporal.filter(pl.col("relation") == "training_sessions")
        .get_column("unobserved_span_days")
        .sum()
    )
    finding(
        "session_dates_are_sparse",
        "bronze/silver training sessions",
        "WARNING",
        "Session relations are event-grain and naturally have sparse dates; "
        f"aggregate span gap count is {int(session_gaps)}",
    )
    return pl.DataFrame(rows).sort("status", "check_id")


def _render_report(result: Stage00AuditResult) -> str:
    summary = result.summary
    findings = result.tables["audit_findings"]
    lines = [
        "# Stage 0 - Data Inventory and Audit",
        "",
        "## Decision Status",
        "",
        f"Automated audit result: **{summary['status']}**. "
        "This is a data-foundation gate, not EDA or model evidence.",
        "",
        "## Scope",
        "",
        f"- Compact relations audited: `{summary['relation_count']}`.",
        f"- GCS objects inventoried: `{summary['object_count']}`.",
        f"- Failures: `{summary['failure_count']}`; warnings: `{summary['warning_count']}`.",
        "- No outcome prevalence, feature distribution, correlation, split or model "
        "analysis was performed.",
        "",
        "## Findings",
        "",
        "| Check | Scope | Status | Message |",
        "|---|---|---|---|",
    ]
    lines.extend(
        f"| {row['check_id']} | {row['scope']} | {row['status']} | {row['message']} |"
        for row in findings.iter_rows(named=True)
    )
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "![Relation row counts](../figures/relation_row_counts.png)",
            "",
            "![Player observation lengths](../figures/player_observation_lengths.png)",
            "",
            "![Gold player-date coverage](../figures/player_date_coverage.png)",
            "",
            "## Gate",
            "",
            "A project-owner review is required even when automated checks pass. "
            "Stage 1 must not begin until this report and its tables are discussed and approved.",
        ]
    )
    return "\n".join(lines) + "\n"


def _load_quality_reports(bucket: Bucket) -> dict[str, Any]:
    names = (
        "bronze_ingestion",
        "silver_transformation",
        "injury_episodes",
        "player_day_labels",
        "player_day_features",
    )
    return {
        name: json.loads(bucket.blob(f"{QUALITY_PREFIX}/{name}.json").download_as_text())
        for name in names
    }


def _load_provenance(project_id: str, core_dataset: str) -> dict[str, Any]:
    client = bigquery.Client(project=project_id)
    run_table = f"{project_id}.{core_dataset}.ingestion_runs"
    source_table = f"{project_id}.{core_dataset}.source_files"
    query = f"""
        SELECT
          run_id, status, records_read, records_written, error_count,
          (SELECT COUNT(*) FROM `{source_table}` s WHERE s.run_id = r.run_id) AS source_file_count
        FROM `{run_table}` r
        WHERE source_name = 'soccermon' AND source_version = 'zenodo-10033832'
        ORDER BY completed_at DESC
        LIMIT 1
    """
    rows = [dict(row.items()) for row in client.query(query).result()]
    if len(rows) != 1:
        raise ValueError(f"Expected one latest SoccerMon provenance run, found {len(rows)}")
    return rows[0]


def _object_rows(bucket_name: str, blobs: Any) -> list[dict[str, Any]]:
    return [
        {
            "bucket": bucket_name,
            "object_name": blob.name,
            "gcs_uri": f"gs://{bucket_name}/{blob.name}",
            "size_bytes": blob.size,
            "generation": str(blob.generation),
            "md5_hash": blob.md5_hash,
            "crc32c": blob.crc32c,
            "updated": blob.updated.isoformat() if blob.updated else None,
        }
        for blob in blobs
    ]


def _relation_key(contract: RelationContract) -> str:
    return f"{contract.layer}.{contract.name}"


def _n_unique(frame: pl.DataFrame, column: str) -> int | None:
    return frame.get_column(column).n_unique() if column in frame.columns else None


def _date_value(frame: pl.DataFrame, column: str, operation: str) -> date | None:
    if column not in frame.columns:
        return None
    value = frame.get_column(column).min() if operation == "min" else frame.get_column(column).max()
    return value if isinstance(value, date) else None
