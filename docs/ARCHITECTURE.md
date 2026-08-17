# Architecture

Two views. The first is the data and serving path: where a byte enters the
system and how it becomes a number on the dashboard. The second is the
evidence chain: how a stage-gated analysis programme became a champion
model, a set of governing decisions, and a deployed artefact.

## Data and serving path

```mermaid
flowchart LR
    subgraph Source
        Z["SoccerMon archive\n(Zenodo, ~99 GB compressed)"]
    end

    subgraph GCS["Cloud Storage: paa-data / paa-source-archives"]
        RAW["raw/"]
        BRONZE["bronze/\n(deterministic parsing)"]
        SILVER["silver/\n(registry, wellness, load,\nsessions, injury episodes)"]
        GOLD["gold/\n(player_day_features.parquet,\nplayer_day_labels.parquet)"]
    end

    BQPROV[("BigQuery paa_core\ningestion_runs, source_files")]

    subgraph Product["V1-P6 batch inference (jobs/product/run_batch_inference.py)"]
        FIT["Fit frozen F1 champion\non development partition"]
        SCORE["Score every eligible\nplayer-day"]
        RECON["Reconcile BQ-bound and\nartefact-bound rows"]
    end

    BQPRODUCT[("BigQuery paa_product\ntable of record")]
    ARTEFACT["GCS serving artefact\nparquet + manifest +\nonset calendar"]

    API["paa-api (Cloud Run)\nFastAPI, reads artefact only,\nnever queries BigQuery per request"]
    WEB["paa-web (Cloud Run)\nNext.js, four views,\nBasic-Auth gated"]
    REVIEWER(["Reviewer"])

    Z --> RAW --> BRONZE --> SILVER --> GOLD
    BRONZE -.provenance.-> BQPROV
    GOLD --> FIT --> SCORE --> RECON
    RECON --> BQPRODUCT
    RECON --> ARTEFACT
    ARTEFACT --> API
    API -->|"IAM-authenticated,\nsame-project identity"| WEB
    WEB --> REVIEWER
```

The API never queries BigQuery per request; `paa_product` is the table of
record and reconciliation target, not the serving path. The two Cloud Run
services communicate over IAM identity (`run.invoker` restricted to the web
service's own service account), not network-level ingress restriction —
this project provisions no Direct VPC egress, so IAM authentication is what
actually enforces "reachable only by this identity" (`DEC-064`).

## Evidence chain: analysis to deployed artefact

```mermaid
flowchart TD
    subgraph Stages["Stage-gated analysis (owner-approved gate before each)"]
        S0["Stage 0\nData audit"] --> S1["Stage 1\nOutcome EDA"]
        S1 --> S2["Stage 2\nMissingness EDA"]
        S2 --> S3["Stage 3\nFeature distribution"]
        S3 --> S4["Stage 4\nFeature redundancy"]
        S4 --> S5["Stage 5\nOutcome context"]
        S5 --> S6["Stage 6\nCohort/outcome sensitivity"]
        S6 --> S7["Stage 7\nProspective protocol\n(frozen partitions,\npredictor contract)"]
        S7 --> S8["Stage 8\nReadiness gate\nREADY (narrow scope)"]
    end

    S8 --> E002["EXP-002\nM0 baseline"]
    E002 --> E003["EXP-003\nM1 F1/F2/F3 ladder\nF3 promoted (DEC-043)"]
    E003 --> E016["EXP-016\nAblation:\nF3's edge is an\navailability artefact"]
    E016 -->|"DEC-054"| CHAMPION{{"F1 selected\nas champion"}}

    CHAMPION --> E007["EXP-007\nCox survival\nunseen-player lead was\ngap-time leakage"]
    E007 -->|"DEC-055: rejected"| CHAMPION
    CHAMPION --> E008["EXP-008\nGradient boosting\nBrier wins, calibration\nand ROC-AUC lose"]
    E008 -->|"DEC-056: rejected"| CHAMPION

    CHAMPION --> E009["EXP-009\nCalibration:\nraw beats Platt and isotonic"]
    E009 -->|"DEC-058 / DEC-059"| RAWPROB{{"Raw probabilities,\nno calibrator,\nfrozen"}}

    RAWPROB --> E018["EXP-018\nExplanation stability:\n8 of 9 predictors\nsign-stable"]
    RAWPROB --> E019["EXP-019\nAlert-budget simulation:\npercentile beats top-N"]
    E018 --> GATE4{{"DEC-060 / DEC-061\nV1-P4 closed"}}
    E019 --> GATE4

    GATE4 --> P5["V1-P5 governance gate\nPre-registered, spent once\nDEC-062"]
    P5 -->|"C1 yes, C2 yes,\nC3 no"| P5DIAG["DEC-063\nC3 diagnosed from\ncommitted evidence,\nno second access"]

    P5DIAG --> P6["V1-P6\nBatch inference +\nfour-view dashboard\nDEC-064"]
    P6 --> DEPLOY[("Deployed artefact\npaa-api + paa-web\nCloud Run")]

    DEPLOY --> P7["V1-P7\nPublic repository + CI\nDEC-065 / DEC-066"]
    P7 --> P8["V1-P8\nModel card, this diagram,\nclaim traceability audit"]
```

Every arrow into a decision node (`DEC-###`) is backed by a committed
evidence table under `outputs/`; see
[`CLAIM_TRACEABILITY.md`](CLAIM_TRACEABILITY.md) for the claim-by-claim
mapping and [`DECISION_LOG.md`](DECISION_LOG.md) for the full record.
