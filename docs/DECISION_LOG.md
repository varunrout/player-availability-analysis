# Player Availability Analysis - Decision Log

Append-only record of material project decisions.

Scope: package and repository architecture, dependency management, cloud architecture, storage location, analytical grain, label definitions, cohort rules, censoring, leakage controls, validation methodology, model-family choices, serving architecture, IAM architecture, and material scope changes. Ordinary code fixes are not recorded here unless they alter project design.

Valid statuses: `PROPOSED`, `ACCEPTED`, `REJECTED`, `SUPERSEDED`.

Historical decisions are never deleted. A decision that changes is superseded by a new entry, linked in both directions.

---

## DEC-001

**Decision ID:** DEC-001
**Date:** 2026-08-12
**Status:** ACCEPTED

**Context:**
Athlete monitoring data arrives at multiple grains: individual sessions, daily wellness reports, and irregular injury reports. A single canonical prediction unit is required before features, labels or validation can be defined coherently.

**Decision:**
Use `player x date` (player-day) as the primary prediction unit.

**Rationale:**
Matches the operational cadence of first-team athlete monitoring, where practitioners review squad status daily. Supports longitudinal feature construction with rolling windows and player-relative baselines. Gives a well-defined prediction cutoff for leakage control.

**Alternatives Considered:**
Player-session grain, rejected because sessions are irregular and absent on rest days, which fragments the longitudinal signal. Player-week grain, rejected as too coarse for actionable review.

**Consequences:**
All features must be computable from information available at a defined daily cutoff. Labels are defined over forward windows from that cutoff. Days inside an active injury episode require an explicit inclusion or exclusion rule.

**Affected Components:** data model, feature engineering, label construction, validation, product

**Supersedes:** none
**Superseded By:** none

---

## DEC-002

**Decision ID:** DEC-002
**Date:** 2026-08-12
**Status:** ACCEPTED

**Context:**
The public source dataset contains repeated self-reported injury observations rather than medically verified clinical episodes. Framing the target as clinical prediction would misrepresent the evidence base.

**Decision:**
Treat injury as a risk-stratification target for practitioner review, not a diagnostic or clinical prediction target.

**Rationale:**
Labels are subjective and clinical ground truth is unavailable. Overstating the target would make every downstream claim indefensible under scrutiny.

**Alternatives Considered:**
Framing as injury prediction, rejected because it implies a clinical certainty the data cannot support.

**Consequences:**
Output language is constrained: "estimated availability risk", "elevated relative to player baseline", "practitioner review". Prohibited: "will get injured", "safe to play", "medically cleared". Applies to model cards, dashboard copy, reports and portfolio material.

**Affected Components:** modelling, explainability, product, governance, portfolio material

**Supersedes:** none
**Superseded By:** none

---

## DEC-003

**Decision ID:** DEC-003
**Date:** 2026-08-12
**Status:** ACCEPTED

**Context:**
Longitudinal athlete data contains strong temporal autocorrelation. Random row-level splitting places future information in the training set.

**Decision:**
Chronological validation is mandatory. Random row-level train/test splitting is not acceptable as a primary evaluation approach.

**Rationale:**
Random splits create temporal leakage and produce metrics that will not survive deployment conditions. The validation design must resemble how the system would actually be used.

**Alternatives Considered:**
Stratified random k-fold, rejected as temporally invalid. Grouped k-fold by player alone, rejected because it controls player leakage but not temporal leakage.

**Consequences:**
Required evaluation layers: temporal holdout, rolling or expanding-window validation. Season transfer and team transfer evaluated where sample size supports it. Any result produced under a random split is not reportable.

**Affected Components:** validation, evaluation, experiment design, reporting

**Supersedes:** none
**Superseded By:** none

---

## DEC-004

**Decision ID:** DEC-004
**Date:** 2026-08-12
**Status:** ACCEPTED

**Context:**
Player identity is a powerful confounder. A model can achieve strong apparent performance by memorising individual players rather than learning transferable physiological patterns.

**Decision:**
Leave-one-player-out evaluation is mandatory alongside chronological validation.

**Rationale:**
Tests whether the system generalises to athletes it has never seen, which is the realistic condition for squad turnover, loans and new signings.

**Alternatives Considered:**
Temporal validation only, rejected because it does not detect player-identity leakage.

**Consequences:**
Performance degradation between within-player and unseen-player evaluation must be measured and reported honestly. A model that only performs well within known players must be described as such.

**Affected Components:** validation, evaluation, reporting, model cards

**Supersedes:** none
**Superseded By:** none

---

## DEC-005

**Decision ID:** DEC-005
**Date:** 2026-08-12
**Status:** ACCEPTED

**Context:**
The SoccerMon objective GNSS archive is approximately 99 GB compressed with billions of measurements. The subjective archive is small. Starting with the large archive would make a 99 GB ingestion event the first debugging environment.

**Decision:**
Build the subjective-data vertical slice first. Full objective GPS ingestion is deferred until the subjective slice is complete and trusted.

**Rationale:**
Provides a fast path to validated outcome definitions, leakage controls and validation design before incurring significant compute and storage cost. Reduces project risk and cost concurrently.

**Alternatives Considered:**
Parallel subjective and objective ingestion, rejected on cost, complexity and debugging-surface grounds. Objective-first, rejected outright.

**Consequences:**
Staged ingestion: Phase A subjective, Phase B one team-season GPS pilot with measured runtime and cost, Phase C full objective expansion. No GPS work begins until event definitions and leakage tests are trusted.

**Affected Components:** ingestion, storage, compute, cost control, delivery plan

**Supersedes:** none
**Superseded By:** none

---

## DEC-006

**Decision ID:** DEC-006
**Date:** 2026-08-12
**Status:** ACCEPTED

**Context:**
Complex models are easy to reach for and hard to justify. Without a discipline, model selection degenerates into unstructured search.

**Decision:**
Model development follows a fixed ladder: M0 operational baseline, M1 logistic regression, M2 gradient boosting, M3 Cox proportional hazards, M4 random survival forest, M5 boosted survival, M6 neural survival. Each rung must demonstrate incremental value over the previous one before the next is attempted.

**Rationale:**
Complexity is not a success criterion. A simpler model that matches a complex one on calibration and alert burden is the better deliverable and the more defensible interview narrative.

**Alternatives Considered:**
Starting with gradient boosting for speed, rejected because it removes the interpretable benchmark that makes later results meaningful.

**Consequences:**
M6 is implemented only if evidence justifies it. Every model comparison must report the simpler baseline alongside. Champion selection is made on more than a single ranking metric.

**Affected Components:** modelling, experiment backlog, evaluation, reporting

**Supersedes:** none
**Superseded By:** none

---

## DEC-007

**Decision ID:** DEC-007
**Date:** 2026-08-12
**Status:** ACCEPTED

**Context:**
Practitioners act on the magnitude of a risk estimate, not only its rank. A well-ranked but poorly calibrated model misleads its users.

**Decision:**
Calibration is a first-class metric, evaluated and reported for every headline model.

**Rationale:**
A stated 20% risk must mean approximately 20%. Ranking quality alone does not support the operational decisions this system is designed to inform.

**Alternatives Considered:**
Discrimination-only evaluation, rejected as insufficient for a decision-support product.

**Consequences:**
Mandatory: Brier score, calibration slope, calibration intercept, expected calibration error, reliability curves. Survival models additionally require time-dependent calibration and integrated Brier score. Calibration methods (raw, Platt, isotonic) are compared. Final models are either calibrated or explicitly shown to be poorly calibrated.

**Affected Components:** evaluation, modelling, product, model cards

**Supersedes:** none
**Superseded By:** none

---

## DEC-008

**Decision ID:** DEC-008
**Date:** 2026-08-12
**Status:** ACCEPTED

**Context:**
Injury onset is a rare event. Accuracy is trivially maximised by predicting the negative class everywhere.

**Decision:**
Accuracy is not used as a headline metric.

**Rationale:**
Class imbalance makes accuracy uninformative and actively misleading in reporting.

**Alternatives Considered:**
Reporting accuracy alongside other metrics, rejected because its presence in headline material invites misinterpretation.

**Consequences:**
Primary classification metrics: PR-AUC, ROC-AUC, Brier score, log loss, recall at fixed review capacity, calibration slope and intercept. Operational metrics include alert burden and week-to-week ranking stability.

**Affected Components:** evaluation, reporting, portfolio material

**Supersedes:** none
**Superseded By:** none

---

## DEC-009

**Decision ID:** DEC-009
**Date:** 2026-08-12
**Status:** ACCEPTED

**Context:**
Eight planning-level decisions were recorded in `13_EXPERIMENT_BACKLOG_AND_DECISION_LOG.md` in the Drive planning corpus, using the `DEC-00n` identifier scheme but an abbreviated format. A separate canonical decision log is now required, mirrored between the repository and Drive. Two documents claiming the same identifier space would produce ambiguous references.

**Decision:**
`docs/DECISION_LOG.md` is the canonical decision record, mirrored to the Drive project folder. The eight planning decisions are carried forward with their original identifiers `DEC-001` to `DEC-008` and expanded to the full record format. `13_EXPERIMENT_BACKLOG_AND_DECISION_LOG.md` remains the authoritative experiment backlog (`EXP-nnn`), but its decision-log section is superseded as a decision record. New decisions continue from `DEC-010`.

**Rationale:**
Preserves existing identifiers so prior references remain valid, avoids a duplicated and diverging identifier space, and keeps the experiment backlog where it is useful without making it a second source of truth for decisions.

**Alternatives Considered:**
Renumbering the planning decisions from `DEC-010`, rejected because it invalidates existing references for no benefit. Maintaining decisions in doc 13, rejected because the shared-state protocol requires a mirrored pair of control documents in the repository and Drive.

**Consequences:**
All future material decisions are appended here and mirrored to Drive. Doc 13 should not be edited to add new decisions. `PROJECT_STATE.md` references this file as the decision record.

**Affected Components:** project control, documentation, decision history

**Supersedes:** decision-log section of `13_EXPERIMENT_BACKLOG_AND_DECISION_LOG.md`
**Superseded By:** none

---

## DEC-010

**Decision ID:** DEC-010
**Date:** 2026-08-13
**Status:** ACCEPTED

**Context:**
The repository scaffold used the import package `src/player_availability_analysis/`, while architecture documents 04 and 18 specify `src/player_availability/`. Both names were in circulation. Every module path, import statement and the `mypy` `packages` setting depends on which is correct.

**Decision:**
The import package is `player_availability`, matching the architecture baseline. The distribution name remains `player-availability-analysis`.

**Rationale:**
Architecture documents 04 and 18 are the declared baseline; the scaffold was the deviation. Resolving it now cost almost nothing because the package contained a single empty `__init__.py` and the repository had no commits. The cost of changing it rises with every module added. A distribution name differing from its import package is normal and explicitly configured, so nothing is ambiguous.

**Alternatives Considered:**
Keeping `player_availability_analysis` and amending docs 04 and 18. Rejected: it treats the architecture baseline as the thing to bend, and `player_availability_analysis.ingestion.soccermon` is needlessly long at every call site.

**Consequences:**
`src/player_availability_analysis/` and its stale `egg-info` metadata were removed. `pyproject.toml` declares `packages = [{ include = "player_availability", from = "src" }]` and `mypy` checks `player_availability`. All imports use the short form.

**Affected Components:** package layout, build configuration, type checking, every future module

**Supersedes:** none
**Superseded By:** none

---

## DEC-011

**Decision ID:** DEC-011
**Date:** 2026-08-13
**Status:** ACCEPTED

**Context:**
Dependencies were declared without version constraints and no lockfile existed, so no two installations were guaranteed to produce the same environment. Reproducibility is a stated project requirement and CI and container builds both depend on it.

**Decision:**
Use Poetry for dependency management and packaging, with a committed `poetry.lock`. Build backend is `poetry-core`. Dependency constraints are bounded on both sides.

**Rationale:**
A committed lockfile pins the exact resolved environment; the ranges in `pyproject.toml` define what an upgrade is permitted to move to. Bounded constraints matter more than they appear: with unbounded lower bounds the resolver backtracked through hundreds of releases and did not converge in over twelve minutes. Tightening the lower bounds to current releases reduced resolution to under a minute. Upper bounds prevent a major release from silently breaking the build.

**Alternatives Considered:**
`uv` with `uv.lock`, faster and would have kept the existing setuptools backend. Not selected. `pip-tools`, rejected because it produces platform-specific output and manages the environment separately, which fits containerised cloud jobs poorly.

**Consequences:**
Build backend changed from setuptools to `poetry-core`. `poetry.lock` is committed and pins 50 packages. `poetry check --lock` verifies the lockfile matches `pyproject.toml` and belongs in CI. Dependency upgrades are deliberate acts that change `pyproject.toml` and regenerate the lockfile.

**Affected Components:** build system, dependency management, CI, container builds, reproducibility

**Supersedes:** none
**Superseded By:** none

---

## DEC-012

**Decision ID:** DEC-012
**Date:** 2026-08-13
**Status:** ACCEPTED

**Context:**
Architecture doc 18 specifies a full repository tree including `jobs/`, `pipelines/`, `app/`, `sql/` and nested subdirectories under `docs/`, `configs/`, `src/`, `tests/` and `infra/`. None of it existed. Creating all of it immediately would produce roughly twenty empty placeholder directories.

**Decision:**
Create only the structure the subjective ingestion vertical slice requires: `src/player_availability/{config,ingestion,schemas,quality,utils}`, `tests/{unit,data_contracts,leakage,smoke}`, `jobs/`, and `docs/{architecture,decisions}`. Remaining directories from doc 18 are created when real content exists for them.

**Rationale:**
An empty directory tree signals more capability than has been built, which is the opposite of what this project's evidence standard requires. The chosen subset is not arbitrary: the four test subdirectories encode the validation obligations from DEC-003 and DEC-004 as structure, so leakage testing has a home before the first feature is written.

**Alternatives Considered:**
Creating the full doc 18 tree immediately, rejected as premature scaffolding. Growing directories purely ad hoc, rejected because it drifts from the architecture baseline without a deliberate decision.

**Consequences:**
The repository does not currently match doc 18's tree in full. This is deliberate, not drift. `pipelines/`, `app/` and `sql/` are added when the corresponding work begins.

**Affected Components:** repository structure, test organisation

**Supersedes:** none
**Superseded By:** none

---

## DEC-013

**Decision ID:** DEC-013
**Date:** 2026-08-13
**Status:** ACCEPTED

**Context:**
Doc 18 specifies layered YAML configuration; the scaffold declared `pydantic-settings` with a `.env.example`. Both mechanisms were present with no defined relationship, which would have produced two competing sources of truth.

**Decision:**
Use both, split by responsibility, with a defined precedence.

Versioned YAML (`configs/base.yaml`, `configs/<PAA_ENV>.yaml`) holds analytical behaviour: rolling windows, label horizons, episode-gap rules, minimum history. Environment variables hold deployment identity and secrets: project ID, region, buckets, dataset names. Layers merge in order `base -> <environment> -> environment variables`, and environment variables always win. All values are validated at process start.

**Rationale:**
The split follows what each value does. Analytical parameters change experiment results, so they must be reproducible from a commit hash alone and therefore belong in Git. Deployment identity differs per environment and must never be committed. Making the environment the highest-priority source means a deployed job can be retuned without a rebuild, which matters for Cloud Run.

Validating at start means a misconfigured job fails immediately rather than part-way through a run that has already written data.

**Alternatives Considered:**
`pydantic-settings` alone, rejected because it pushes analytical parameters out of version control and weakens experiment reproducibility. YAML alone, rejected because it forces secrets into files and fits Cloud Run's environment injection model poorly.

**Consequences:**
Implemented as a custom `pydantic-settings` source registered below the environment sources, so precedence is enforced by the type system rather than by convention. `PAA_ENV` selects the layer and defaults to `local`. `PAA_CONFIG_DIR` overrides the configuration directory for containers. Any analytical value is overridable via the `PAA_ANALYSIS_` prefix. Twenty-three tests assert the precedence and validation contract.

Provisional analytical values are marked in `configs/base.yaml`. `injury_episode_gap_days` is set to 3 pending EXP-001 and must not be used for a headline result until that sensitivity experiment has been run.

**Affected Components:** configuration, all jobs and pipelines, reproducibility, deployment

**Supersedes:** none
**Superseded By:** none

---

## DEC-014

**Decision ID:** DEC-014
**Date:** 2026-08-13
**Status:** ACCEPTED

**Context:**
The subjective ingestion vertical slice could run locally or as a Cloud Run Job from the outset. The choice affects iteration speed, cost during development, and how quickly the deployment path is proven.

**Decision:**
Run the subjective vertical slice local-first: parse and transform locally with Polars and PyArrow, writing bronze Parquet and provenance records to Cloud Storage and BigQuery as sinks.

**Rationale:**
The subjective archive is small, so distributed or containerised compute buys nothing at this stage. Every debugging cycle under a cloud-first approach becomes a container build and deploy, which is slow and costs money while the parsing logic is still unstable. Containerising a working local job for Cloud Run later is mechanical; debugging unstable parsing logic through a deploy cycle is not.

This is consistent with DEC-005 and with the cost-control principle of not paying for infrastructure before the workload justifies it.

**Alternatives Considered:**
Cloud-first from day one, rejected on iteration speed and development cost. It proves the deployment path earlier, but that path is not the risky part of this stage.

**Consequences:**
Ingestion code must remain free of assumptions about its execution environment so that containerisation is a packaging step, not a rewrite. Configuration is already environment-driven per DEC-013, which supports this. The GPS pilot in Phase B is expected to require cloud execution and will be assessed separately against measured runtime.

**Affected Components:** ingestion, compute strategy, cost control, delivery sequencing

**Supersedes:** none
**Superseded By:** none

---

## DEC-015

**Decision ID:** DEC-015
**Date:** 2026-08-13
**Status:** ACCEPTED

**Context:**
The repository had zero commits and no remote. There was no recovery point, no reviewable history, and no protection against losing work.

**Decision:**
Commit the foundation locally now. Remote hosting is deferred to a separate decision.

**Rationale:**
Establishing a recovery point is urgent and independent of where the repository is eventually hosted. Deferring the hosting choice avoids rushing a decision about public visibility that is hard to reverse once history exists.

**Alternatives Considered:**
Pushing immediately to a private remote, which would also give off-machine backup but requires repository creation and credentials. Pushing to a public remote, deferred because a public history makes every future mistake permanent and visible, and that choice deserves its own consideration.

**Consequences:**
Work exists only on this machine until a remote is added. This is an accepted, time-limited risk and remains an open item. Branch and review policy is decided alongside remote hosting.

**Affected Components:** version control, backup, review process

**Supersedes:** none
**Superseded By:** none

---

## DEC-016

**Decision ID:** DEC-016
**Date:** 2026-08-13
**Status:** SUPERSEDED

**Context:**
The Drive mirror of the control documents was maintained through a connector that can create files but cannot update or delete them. Each state update therefore produced a duplicate under the same title, which the desktop client resolved by appending "(1)" and which required manual cleanup. This is unsustainable for documents that change every session.

**Decision:**
Maintain the Drive mirror by writing the files in place at the mounted Google Drive path (`G:\My Drive\Projects\PlayerAvailabilityAnalysis`), letting Google Drive Desktop sync them. The create-only connector is no longer used for mirroring.

**Rationale:**
In-place writes overwrite the existing files, so no duplicate is ever created and no manual cleanup is needed. The repository copy under `docs/` remains canonical; the Drive copy is a synced mirror of identical content.

**Alternatives Considered:**
Continuing with the create-only connector and cleaning up duplicates each time, rejected as error-prone busywork. Mirroring only at major checkpoints, rejected because it leaves the Drive copy stale between checkpoints, which defeats the purpose of a mirror.

**Consequences:**
The mounted Drive folder must remain accessible to the session for mirroring to work. If it is ever unmounted, mirroring is reported as `STATE SYNC INCOMPLETE` rather than silently skipped. Both copies are byte-identical after each update.

**Affected Components:** project control, state synchronisation, documentation

**Supersedes:** none
**Superseded By:** DEC-020

---

## DEC-017

**Decision ID:** DEC-017
**Date:** 2026-08-13
**Status:** ACCEPTED

**Context:**
The repository has a local foundation commit but no remote. The project owner has explicitly set the version-control policy for the present phase.

**Decision:**
Keep Git local-only. Do not create, configure, push to or otherwise use a remote unless the project owner explicitly requests it.

**Rationale:**
The work is currently being developed on a single machine and no external hosting policy is needed to make progress. This keeps visibility, review and backup choices in the project owner's control.

**Alternatives Considered:**
Creating a private remote now, rejected because it would change the agreed local-only operating model. Creating a public remote, rejected because it would make project history externally visible without an explicit request.

**Consequences:**
The repository has no off-machine version-control backup and no remote CI trigger. Local commits remain appropriate. `OD-08` is resolved as a policy decision and can be revisited only through a new material decision.

**Affected Components:** version control, backup, review process, CI delivery

**Supersedes:** none
**Superseded By:** none

---

## DEC-018

**Decision ID:** DEC-018
**Date:** 2026-08-13
**Status:** SUPERSEDED

**Context:**
The complete SoccerMon archive is approximately 100 GB compressed and was not yet present in the project Google Drive folder. The archive must be preserved and provenance-established before any downstream work can rely on it.

**Decision:**
The first active delivery objective is to acquire the complete SoccerMon archive from its Zenodo record into the project Google Drive folder. Acquisition runs directly to the mounted Drive location, supports resume after interruption, and produces a SHA-256 provenance manifest. It does not stage the archive in GCP.

**Rationale:**
Google Drive is the project's permanent raw-archive location. Direct-to-Drive acquisition avoids an unnecessary local duplicate and avoids cloud storage and compute cost for a source archive that is not yet being processed. Resumability and recorded checksums make a long transfer practical and auditable.

**Alternatives Considered:**
Downloading the archive to local disk first, rejected because it requires a second 100 GB copy before the Drive upload. Staging the complete archive in GCS, rejected because the architecture intentionally keeps permanent raw archives in Drive and does not require cloud processing at this stage. Beginning full GPS ingestion after download, rejected by DEC-005; the subjective ingestion vertical slice remains first.

**Consequences:**
`scripts/acquire_soccermon_archive.py` is the acquisition entry point. The script must be run against an existing mounted Drive archive directory and its resulting manifest retained alongside the downloaded files. `OD-07` remains open until the transfer completes and the location, licence and SHA-256 values are recorded.

**Affected Components:** source acquisition, data provenance, Drive storage, cost control, delivery sequencing

**Supersedes:** none
**Superseded By:** DEC-019

---

## DEC-019

**Decision ID:** DEC-019
**Date:** 2026-08-13
**Status:** ACCEPTED

**Context:**
The mounted Google Drive path is not available to the execution environment. GCP project access and the existing data bucket have now been verified, while Storage Transfer Service is currently disabled.

**Decision:**
Acquire the complete SoccerMon archive directly from Zenodo into `gs://paa-data-979927072833/raw/source_archives/soccermon/zenodo-10033832/` through a one-time Storage Transfer Service URL-list job. The URL list records Zenodo's published object sizes and MD5 checksums. It is stored in `metadata/transfer_manifests/` and is the only small staging object written before the transfer.

**Rationale:**
Storage Transfer Service is agentless, managed and appropriate for a 99 GB public archive. It avoids local disk capacity, a fragile Drive mount and a workstation-dependent upload. The size and MD5 fields make the service reject incomplete or corrupted source objects. This follows the existing GCS zoning model while keeping the source archive outside BigQuery and avoiding raw GPS ingestion.

**Alternatives Considered:**
Mounted Google Drive acquisition, superseded because the path is unavailable. Downloading to local disk then uploading to GCS, rejected because it requires a large local duplicate and is restart-prone. Streaming through a workstation process, rejected because it couples a long transfer to local process availability.

**Consequences:**
Enable `storagetransfer.googleapis.com` and grant its managed service agent least-privilege read access to the URL-list manifest. `scripts/acquire_soccermon_archive.py` prepares the list and creates the job only when run with `--submit`. The job is one-time and uses `--overwrite-when=never`. No objective/GPS processing begins after transfer; DEC-005 remains binding.

**Affected Components:** source acquisition, Cloud Storage, IAM, data provenance, cost control, delivery sequencing

**Supersedes:** DEC-018
**Superseded By:** none

---

## DEC-020

**Decision ID:** DEC-020
**Date:** 2026-08-13
**Status:** ACCEPTED

**Context:**
The project-control documents must remain mirrored between the local repository and Google Drive, but the mounted `G:` Drive path is unavailable from this environment. The Drive connector can update the existing raw Markdown files in place using stable file IDs.

**Decision:**
Maintain the Drive mirrors of `PROJECT_STATE.md` and `DECISION_LOG.md` through in-place Drive connector updates. Do not depend on a mounted Drive letter.

**Rationale:**
This preserves the required shared-state mirror without relying on workstation-specific filesystem integration. Updates retain the existing Drive file IDs and avoid duplicate files.

**Alternatives Considered:**
Mounted-path writes, superseded because the path is not accessible. Creating a new file for each update, rejected because it causes duplicate and ambiguous control documents.

**Consequences:**
Every material state update writes the local file and then replaces the contents of the corresponding stable Drive file. Synchronisation is verified by connector readback.

**Affected Components:** project control, state synchronisation, documentation

**Supersedes:** DEC-016
**Superseded By:** none

---

## DEC-021

**Decision ID:** DEC-021
**Date:** 2026-08-13
**Status:** ACCEPTED

**Context:**
Storage Transfer Service rejected the approved prefix-conditional bindings on `gs://paa-data-979927072833`. Its preflight requires bucket-level `storage.objects.list` and `storage.objects.create` permissions for the managed transfer identity. Granting those roles without conditions would let the identity access all object names and create objects throughout the shared analytical data bucket.

**Decision:**
Create a dedicated, archive-only Cloud Storage bucket for the complete SoccerMon source ZIPs and the associated transfer manifest. Grant Storage Transfer Service the required bucket-level roles only on that dedicated bucket. Do not broaden its access to the shared `paa-data` bucket.

**Rationale:**
An isolated bucket gives the managed transfer service the permissions it requires without exposing bronze, silver, gold, metadata, temporary outputs or future project data. It is a clearer security boundary and keeps raw-archive lifecycle policy separate from analytical datasets.

**Alternatives Considered:**
Granting Storage Transfer Service unconditional object list/create roles on `paa-data`, not recommended because it broadens access across the shared data lake. Replacing Storage Transfer Service with a workstation-dependent download, rejected because it abandons the managed cloud transfer design. Using a Cloud Run download job, deferred because it introduces compute and restart responsibility where a managed transfer is more suitable.

**Consequences:**
Created `gs://paa-source-archives-979927072833` in `europe-west2` with uniform bucket-level access. The Storage Transfer managed identity has bucket metadata read, object viewer and object creator roles on that bucket only; all attempted conditional transfer bindings were removed from `paa-data`. The acquisition script now targets the dedicated bucket and one transfer job has been started. `paa-data` remains the analytical lake for bronze, silver, gold, metadata and temporary processing. After successful transfer, the raw ZIPs can be selectively staged into `paa-data` only when a workload needs them.

**Affected Components:** source acquisition, Cloud Storage, IAM, lifecycle policy, cost control

**Supersedes:** none
**Superseded By:** none

---

## DEC-022

**Decision ID:** DEC-022
**Date:** 2026-08-13
**Status:** ACCEPTED

**Context:**
The verified SoccerMon subjective archive does not use one uniform tabular layout. Daily training-load and wellness files are wide matrices containing 731 dates and 50 player columns. Training sessions are stored as a JSON object keyed by player identifier, each value a list of records with `date`, `duration`, `rpe` and `srpe`. Injury, illness and game-performance files are timestamped event-style CSVs.

**Decision:**
Normalise subjective sources according to their observed native grain. Convert daily wide matrices to long bronze records keyed by player identifier, observation date, metric name and value. Convert JSON session lists to player-session records. Preserve injury, illness and game-performance entries as source events with their source payloads and parsed timestamps. Do not infer injury episodes, availability status or modelling labels during bronze ingestion.

**Rationale:**
Long-form daily records create a stable, auditable layer for joining metrics, profiling missingness and later building the player-day table. Preserving session and event grain retains source meaning and prevents premature aggregation. Separating normalisation from episode and label logic reduces leakage and makes each transformation independently testable.

**Alternatives Considered:**
Keeping the wide matrices as the analytical representation, rejected because player-level joins, quality checks and incremental feature engineering would be brittle. Collapsing sessions directly to daily totals, rejected because it discards the observed session grain before its duplicate and timing behaviour are audited. Building injury episodes during ingestion, rejected because the raw event semantics require a dedicated, evidence-led decision.

**Consequences:**
The first subjective ingestion implementation consists of source-specific contracts, normalisers, bronze Parquet outputs and quality reports. Canonical domain tables, injury episodes, labels and player-day features remain later stages. `DEC-005` remains binding: no objective GPS processing begins.

**Affected Components:** subjective ingestion, bronze storage, data contracts, provenance, quality reporting

**Supersedes:** none
**Superseded By:** none

## DEC-023

**Decision ID:** DEC-023
**Date:** 2026-08-13
**Status:** ACCEPTED

**Context:**
The bronze subjective layer contains normalised long daily metrics, player-session rows and source-preserved events. The next analytical layer requires stable relations for profiling and later player-day construction, but injury reports have not yet been profiled sufficiently to infer episodes or labels.

**Decision:**
Create separate silver relations for the player registry, training-load daily values, wellness daily values, training sessions, injury reports, illness reports and game-performance reports. Pivot daily metrics only within their training-load and wellness domains. Retain all session rows, make wellness report presence explicit, and preserve event payloads. Do not create injury episodes, availability states or modelling labels.

**Rationale:**
This establishes clean daily and session relations without erasing native source grain or making premature outcome assumptions. Explicit wellness completeness makes missingness analysable rather than silently imputed. Deferring episode logic protects subsequent labels from unsupported grouping rules and leakage.

**Alternatives Considered:**
Create a combined player-day feature table now, rejected because it would conflate source curation with feature engineering and injury semantics. Aggregate sessions to a daily total, rejected because valid same-day multiple sessions exist. Treat injury reports as episodes, rejected pending duplicate and timestamp profiling.

**Consequences:**
Seven compact silver Parquet relations are staged in GCS. The next substantive task is evidence-led injury-report profiling and an explicit episode-definition decision. `DEC-022` remains the governing bronze normalisation decision.

**Affected Components:** subjective silver storage, data contracts, player-day preparation, outcome construction

**Supersedes:** none
**Superseded By:** none

---

## DEC-024

**Decision ID:** DEC-024
**Date:** 2026-08-13
**Status:** ACCEPTED

**Context:**
SoccerMon injury reports are repeated self-reports. Inspection found 162 raw reports, 68 multi-location reports and six exact duplicate rows. After parsing and exact component-level deduplication, 299 player-date-location-severity components remain. Candidate gap rules yield 232, 147 and 101 episodes at 1, 3 and 7 days respectively.

**Decision:**
Use a three-day event-free gap as the primary self-reported injury-episode rule. Parse all raw location/severity components, remove exact same-player/same-date/same-component duplicates, and merge reports by player and raw location when the next report is no more than three days after the prior one. Retain the maximum reported severity. Treat one- and seven-day rules as required sensitivity analyses.

**Rationale:**
Three days matches the existing provisional configuration, removes the observed repeated-report runs without the much stronger compression caused by seven days, and remains explicitly sensitivity-tested. Raw locations are retained because broader anatomical grouping would introduce a separate, unsupported mapping decision.

**Alternatives Considered:**
One-day gap, which fragments repeated reporting into 232 episodes. Seven-day gap, which compresses to 101 episodes and risks merging distinct events. Severity-specific episodes, rejected because severity can change within one continuing location-specific report sequence.

**Consequences:**
The primary silver episode table contains 147 self-reported injury episodes. It is suitable for subsequent cohort and label construction, but not medical diagnosis, clearance or causal claims.

**Affected Components:** injury episodes, cohorts, labels, leakage controls, sensitivity analysis

**Supersedes:** none
**Superseded By:** none

---

## DEC-025

**Decision ID:** DEC-025
**Date:** 2026-08-13
**Status:** ACCEPTED

**Context:**
The subjective sources have calendar dates but no reliable intraday timestamps for wellness, training-load or injury reports. A player-day cohort therefore needs an explicit prediction-time convention and censoring rules before 3/7/14-day labels can be used safely.

**Decision:**
Use end-of-calendar-day as the prediction cutoff. Treat data dated on the prediction day as available at cutoff. Define `injury_next_horizon` only from episode starts strictly after the prediction date and through the horizon end. Set labels to null when the horizon passes the player observation end, retain explicit horizon-completeness flags, and mark active-episode days ineligible for primary new-onset modelling.

**Rationale:**
This is the most defensible convention supported by the available timestamps. Strictly post-cutoff episode starts avoid same-day target leakage, and explicit null censoring avoids falsely labelling unknown future periods as negative.

**Alternatives Considered:**
Morning cutoff, rejected because no dependable intraday ordering exists. Treating incomplete horizons as negative, rejected because it creates right-censoring bias. Removing active episodes from the table, rejected because they should remain auditable even though excluded from new-onset eligibility.

**Consequences:**
The gold cohort has 36,550 observed player-days. Positive labels are 213, 448 and 755 for the complete 3/7/14-day horizons. Feature construction must use only data dated on or before the prediction date and must be tested for future-append invariance.

**Affected Components:** player-day cohort, labels, right censoring, leakage tests, modelling eligibility

**Supersedes:** none
**Superseded By:** none

---

## DEC-026

**Decision ID:** DEC-026
**Date:** 2026-08-13
**Status:** ACCEPTED

**Context:**
The end-of-day player-day cohort now has complete 3/7/14-day labels. The first feature set must demonstrate longitudinal player monitoring while preventing future information, current-value self-normalisation and accidental label inclusion.

**Decision:**
Create `subjective_v1` features from daily load, fatigue, readiness, wellness-report completeness and player-session exposure. Include current end-of-day values, trailing 3/7/14/28-day summaries, and player expanding means and z-scores calculated from prior observations only. Keep label, eligibility and metadata columns in the output for cohort handling, but require future modelling code to use an explicit predictor list that excludes them.

**Rationale:**
The source timestamps support same-day values under `DEC-025`; trailing windows and prior-only player baselines reflect recent state and individual context without future leakage. An explicit predictor allow-list is more reliable than assuming labels will be excluded by column position or naming convention.

**Alternatives Considered:**
Full broad feature catalogue before a baseline, deferred until validation shows incremental value. Whole-season player normalisation, rejected because it uses future observations. Separate label and feature files only, rejected because a joined analytical product is useful when predictor selection is enforced.

**Consequences:**
The gold feature product has 36,550 rows and 51 columns. Automated future-append and prior-baseline tests are mandatory and passing. No model has been fitted; chronological split and predictor-selection controls are the next gate.

**Affected Components:** feature engineering, leakage tests, training datasets, model validation

**Supersedes:** none
**Superseded By:** none

---

## DEC-027

**Decision ID:** DEC-027
**Date:** 2026-08-13
**Status:** SUPERSEDED

**Context:**
The subjective v1 player-day product is ready for model development, but fixed-horizon labels overlap in time and a random split would leak future outcome context. A single audit-ready partition and an explicit predictor contract are needed before any baseline is fitted.

**Decision:**
For the primary 14-day new-onset outcome, freeze a shared chronological split after 28 days of player history and complete 14-day labels: train from 2020-01-28 to 2021-03-16, a 14-day embargo, validation from 2021-03-31 to 2021-08-15, a 14-day embargo, and test from 2021-08-30 to 2021-12-17. Use the explicit 34-column subjective v1 predictor allow-list. Labels, eligibility flags, identifiers, dates, episode-state fields and provenance fields are excluded from predictors.

**Rationale:**
The embargo matches the maximum headline horizon, so observations near a boundary cannot have outcomes reaching into the next partition. One shared manifest makes baseline comparisons, ablations and later models comparable. An allow-list is more robust than attempting to remove disallowed columns by naming convention.

**Alternatives Considered:**
Random player-day splitting, rejected because it violates the chronological validation requirement. No boundary embargo, rejected because a 14-day label can cross a partition boundary. Separate date splits per horizon, deferred because it would complicate initial model comparisons; later horizon analysis uses the same conservative shared period.

**Consequences:**
The split-assigned gold product contains 20,505 primary-eligible train rows, 6,900 validation rows and 5,495 test rows, with the test partition held untouched until development is complete. The next permitted experiment is EXP-002 naive operational baselines. Preprocessing, model selection and calibration must respect this partition protocol.

**Affected Components:** modelling datasets, leakage controls, experiment tracking, baseline evaluation, calibration

**Supersedes:** none
**Superseded By:** DEC-028

---

## DEC-028

**Decision ID:** DEC-028
**Date:** 2026-08-14
**Status:** ACCEPTED

**Context:**
The initial Phase A report combined selected cohort, outcome and feature checks, and Phase B froze a chronological split before the project owner had reviewed and approved a complete stepwise pre-model EDA programme. The underlying data engineering remains valid, but the active analysis workflow and outputs no longer match the required review process.

**Decision:**
Withdraw the former Phase A and Phase B analysis implementations and outputs from the active local repository, Google Drive and GCS analytical locations. Preserve the trusted data engineering through the unsplit `player_day_features.parquet`, preserve Git history, and restart pre-model analysis at Stage 0 under explicit specification, implementation, results-discussion and approval gates. Supersede the split decision in `DEC-027`; no chronological split is currently frozen for modelling.

**Rationale:**
Starting from a reviewed analytical sequence makes the reasoning, evidence and owner approvals visible before modelling choices are locked. Removing active outputs prevents obsolete reports or split assignments from being mistaken for approved evidence, while preserving append-only decision and Git history keeps the project honest and auditable.

**Alternatives Considered:**
Keep the old report and split as approved work, rejected because their bundled workflow bypassed the required stage-by-stage review. Rewrite Git or erase historical decisions, rejected because that would destroy provenance. Delete the data-engineering layers, rejected because no evidence invalidates their source-grounded transformations.

**Consequences:**
The active project has no retained EDA report, analysis figures, split manifest or split-assigned gold dataset. Pre-model analysis restarts at Stage 0. A future split must be approved after Stages 0 through 6 and recorded under a new decision if it differs from the superseded protocol.

**Affected Components:** analysis workflow, reports, charts, modelling datasets, GCS metadata, Drive artifacts, project state

**Supersedes:** DEC-027
**Superseded By:** none

---

## DEC-029

**Decision ID:** DEC-029
**Date:** 2026-08-14
**Status:** ACCEPTED

**Context:**
Pre-model analysis needs both reproducible retained artifacts and a fast, readable interactive form for review. Independently implementing the same calculations in scripts and notebooks would create drift, while allowing notebooks to write outputs would create ambiguous artifact provenance.

**Decision:**
Implement each approved analysis stage once as shared reusable functions under `src/player_availability/analysis/`. Provide a command-line runner under `jobs/analysis/` that writes retained artifacts to `outputs/analysis/<stage>/`, with nested figures, tables, reports and metadata folders as applicable. Provide a matching notebook under `notebooks/analysis/` that imports the same shared functions, renders results inline and does not persist generated outputs. Commit notebooks with cell outputs and execution counts cleared.

**Rationale:**
The script provides deterministic, testable and automatable output generation. The notebook improves understanding and discussion. Sharing implementation keeps figures and statistics consistent across both interfaces, and making scripts the only output writers gives every retained artifact a clear provenance path.

**Alternatives Considered:**
Script-only analysis, rejected because it weakens interactive review. Notebook-only analysis, rejected because it is harder to automate and audit. Duplicate script and notebook calculations, rejected because they can diverge. Persist notebook-generated outputs, rejected because it creates two competing output-generation paths.

**Consequences:**
Every analysis stage requires shared functions, a script runner, a cleared notebook and focused tests. Only script runs populate `outputs/analysis/`. No analysis implementation begins until the project owner approves that stage's specification, and no subsequent stage begins until the current results are discussed and approved.

**Affected Components:** analysis package, jobs, notebooks, output filesystem, testing, review workflow

**Supersedes:** none
**Superseded By:** none

---

## DEC-030

**Decision ID:** DEC-030
**Date:** 2026-08-14
**Status:** ACCEPTED

**Context:**
Stage 1 independently reproduced the accepted three-day location-specific episodes and all gold labels, while clarifying the effective outcome support. The 147 location episodes correspond to 73 distinct player-date onset events because 33 onset dates contain multiple simultaneous location episodes. Outcomes are also highly concentrated: 35 of 50 players have no episode, the top five players contribute 75.3% of onset days, and the leading team contributes 90.4%. One-, three- and seven-day rules produce 108, 73 and 55 onset days respectively.

**Decision:**
Retain the three-day, player-plus-raw-location episode construction accepted in `DEC-024`. For fixed-horizon binary labels and effective event-support calculations, define the outcome event unit as a player-date on which one or more location episodes starts; simultaneous location episodes on that date are not independent modelling events. Accept the current labels as internally credible for continued pre-model EDA, not as evidence of modelling readiness or medical ground truth. Require one- and seven-day episode-gap sensitivities in Stage 6 and require player, team and calendar concentration to constrain validation design and claims. Any later model must include unseen-player stress testing and must not claim team transfer without supporting evidence.

**Rationale:**
The three-day rule is an evidence-led intermediate between one-day fragmentation and seven-day over-merging; the latter creates report spans as long as 103 days. The binary label answers whether any future onset occurs, so counting simultaneous body-location starts as independent events would overstate effective sample size and uncertainty precision. Exact episode and label reproduction supports internal credibility, while the observed concentration requires conservative validation and interpretation.

**Alternatives Considered:**
Switch to the one-day rule, rejected as the primary rule because it fragments repeated reporting. Switch to the seven-day rule, rejected because it strongly compresses events and can create implausibly long report clusters. Collapse locations before episode construction, rejected because the source does not provide a supported anatomical aggregation rule. Treat all 147 location episodes as independent modelling events, rejected because the binary target collapses simultaneous starts to one player-date event. Stop analysis entirely, rejected because the labels are internally valid and the remaining staged analyses can determine whether a defensible modelling protocol exists.

**Consequences:**
Stage 2 missingness and reporting-process EDA may proceed. Reports and later model documentation must distinguish 147 location episodes from 73 player-date onset events. Effective event support, uncertainty and concentration must use onset days where appropriate. Stage 6 must retain gap-rule sensitivity, and Stages 7 and 8 must explicitly address unseen-player, team and temporal generalisation before modelling can be approved.

**Affected Components:** episode interpretation, outcome labels, cohort sensitivity, validation, uncertainty, modelling claims, product language

**Supersedes:** none
**Superseded By:** none

---

## DEC-031

**Decision ID:** DEC-031
**Date:** 2026-08-14
**Status:** ACCEPTED

**Context:**
Stage 2 found wellness reports on 17,008 of 36,550 player-days (46.5%). Reporting is almost all-or-none, with 16,931 complete seven-metric reports, 77 partial reports and 19,542 no-report days. Coverage varies from 3.1% to 88.4% by player, differs materially by team and calendar period, and includes a 607-day no-report run. Wellness reporting reaches 97.3% on injury-onset days versus 62.9% averaged over the preceding 28 days. Training-load calendar fields are fully populated but contain many derived zeros, while absence of a session record cannot distinguish rest from unrecorded exposure.

**Decision:**
Preserve source nulls and observed zeros as distinct states; do not convert missing wellness values to zero or apply blanket whole-dataset imputation. Exclude same-day wellness values, wellness-report presence and wellness completeness fields from the primary fixed-horizon predictor contract because the sources lack reliable intraday ordering and reporting is strongly associated with onset-day recording. Permit prior-day and longer-lag wellness values and reporting indicators as candidate features, subject to later leakage audit, train-only preprocessing and sensitivity analysis. Treat no recorded session as an unknown recording/exposure state, never as confirmed rest or automatically missing exposure. Do not exclude low-reporting players at this stage; defer any history, coverage or player exclusions to Stage 6 cohort sensitivity analysis.

**Rationale:**
The scale, duration and player/team/calendar structure of wellness absence are incompatible with a simple random-missingness assumption. The onset-day reporting spike shows that reporting behavior is entangled with the outcome-recording process. A conservative lagged-only primary contract protects prospective interpretation while retaining reporting history as a potentially useful operational signal. Deferring exclusions prevents Stage 2 from selecting a convenient cohort without quantifying the effect on sample size, event support and representation.

**Alternatives Considered:**
Zero-fill missing wellness, rejected because zero is an observed source value and has a different meaning. Global mean or player-mean imputation before splitting, rejected because it can erase process information and leak future distributional information. Include same-day wellness and completeness in the primary contract, rejected because intraday ordering is unavailable and reporting is outcome-entangled. Exclude low-coverage players immediately, deferred because the effect on event support and generalisability belongs in Stage 6. Interpret absent sessions as rest, rejected because the source semantics do not support that claim.

**Consequences:**
Stage 3 may analyse current-day fields descriptively but must distinguish them from primary-model eligibility. Later predictor contracts must use lagged wellness/reporting features for the primary analysis, fit any model-specific imputation on training data only, and retain missingness sensitivity checks. Stage 6 must quantify candidate coverage/history exclusions. Product language must not interpret missing wellness or absent sessions as physiology, non-compliance, rest or medical status.

**Affected Components:** missing-value handling, feature eligibility, leakage controls, cohort sensitivity, preprocessing, interpretation, product language

**Supersedes:** none
**Superseded By:** none

---

## DEC-032

**Decision ID:** DEC-032
**Date:** 2026-08-14
**Status:** ACCEPTED

**Context:**
Stage 3 profiled 33 numeric features across 36,550 player-days. Load, session-duration and sRPE fields are strongly zero-inflated and right-skewed: 22,353 player-days have no recorded session and zero daily load, 14,191 have a recorded session and positive load, and six have a recorded session with zero load. Within-player variation dominates the five core features, but between-player variation remains material, especially for fatigue and readiness. Team and calendar means shift materially. Existing prior-baseline z-scores can become extreme under near-zero historical variance, reaching absolute maxima of 80.6 for daily load, 12.9 for fatigue and 21.0 for readiness. Three-IQR outer fences flag 979 rows across 14 features, without evidence that those observations are erroneous.

**Decision:**
Preserve canonical raw feature values and all statistically extreme observations; do not delete, winsorise or correct values solely because they cross a distributional fence. Carry deterministic `log1p` candidates for non-negative load, session-duration, session-sRPE and rolling-sum magnitudes, paired with an explicit zero/session-recording indicator so magnitude and recording state remain distinguishable. Do not automatically transform the discrete wellness scales. Exclude the existing prior-baseline z-score fields from the primary operational predictor contract because their tails are unstable under near-zero historical variance. Permit later robust player-relative candidates only with explicit minimum-history and positive-variance requirements. Carry a 28-calendar-day burn-in and at least seven prior observed wellness reports as Stage 6 sensitivity candidates, not frozen cohort requirements. Current-day and current-inclusive wellness features remain descriptive-only under `DEC-031`.

**Rationale:**
The load/session distributions contain two different signals: whether a session was recorded and the magnitude when exposure was recorded. A monotonic `log1p` transform can reduce leverage from long right tails while preserving zero, but the paired indicator is needed because zero does not mean confirmed rest. Discrete wellness scores have bounded source semantics and do not warrant an automatic skewness transform. The current z-score construction is mathematically fragile when prior variance is tiny; allowing it into the primary contract would let denominator instability dominate the signal. Statistical extremeness is insufficient evidence of a source error.

**Alternatives Considered:**
Use raw magnitudes only, retained as a comparison but rejected as the sole operational representation because extreme right tails may dominate scale-sensitive models. Replace or remove all zero-load days, rejected because they encode the observed recording process and cannot be classified as confirmed rest or missing exposure. Winsorise or delete outer-fence observations, rejected because no source-level error was established. Keep the existing z-scores unchanged, rejected for the primary contract because of unstable denominators. Freeze a 28-day burn-in and seven-report threshold immediately, deferred because Stage 6 must quantify their effects on sample size, events and representation.

**Consequences:**
Stage 4 may evaluate redundancy and structural coupling among raw magnitudes, candidate transforms, recording indicators, rolling summaries and eligible lagged/player-relative families without using outcome performance. Predictor contracts must preserve the distinction between recording state and magnitude. Stage 6 must quantify candidate history requirements before any cohort restriction is accepted. Stage 7 must specify any robust relative-feature denominator floor and train-only preprocessing. Team and calendar shifts must constrain the later validation protocol.

**Affected Components:** feature engineering, predictor contracts, preprocessing, cohort sensitivity, leakage controls, validation, interpretation

**Supersedes:** none
**Superseded By:** none

---

## DEC-033

**Decision ID:** DEC-033
**Date:** 2026-08-14
**Status:** ACCEPTED

**Context:**
Stage 4 measured target-blind structural relationships across 33 source numeric features and 16 derived representations for 36,550 player-days. The 35-feature full candidate contract contains raw and `log1p` alternatives rather than 35 independent signals. There are 221 feature pairs with absolute Spearman correlation at least 0.90 and 36 near-deterministic pairs at least 0.995; 15 of the latter are expected raw/`log1p` alternatives. Daily load and session sRPE are near duplicates at the current and rolling levels: current all-day Spearman is 0.999 and positive-recorded-day Spearman is 0.989. Daily load versus session duration falls to 0.828 on positive recorded days. Every adjacent 3/7, 7/14 and 14/28-day rolling-sum pair exceeds 0.92 Spearman. Wellness report presence and wellness metric count are near-deterministic at 0.999 and remain outcome-entangled same-day reporting fields.

**Decision:**
Accept the Stage 4 target-blind full candidate contract as a research catalogue of alternative representations, not a list to enter simultaneously into one model. Carry a smaller provisional operational family policy into later pre-model stages: retain explicit session-recording state and session-count context; use `log1p` magnitude representations for the skewed load/session fields; treat daily load as the primary internal-load family and retain session sRPE only as an alternative sensitivity family rather than an independent simultaneous signal; retain session duration as distinct exposure-duration context; use 7-day and 28-day accumulated windows as the provisional recent and longer-term operational anchors; retain 3-day and 14-day windows in the full contract but defer them from the compact operational contract. Defer prior-player-baseline inclusion until Stage 6 history/cohort sensitivity and Stage 7 leakage/preprocessing review. Require lagged wellness/reporting reconstruction before those families can become primary candidates. Continue to exclude same-day/current-inclusive wellness and the existing unstable z-scores. The exact predictor allow-list remains unfrozen until Stage 7.

**Rationale:**
The compact policy preserves interpretable recording state, current magnitude, recent accumulation and longer accumulation without treating transformations, adjacent windows or duplicate load constructs as independent evidence. Daily load is the canonical daily internal-load field, while session duration adds information not fully explained by load magnitude. Keeping session sRPE and intermediate windows in the full catalogue preserves sensitivity options without burdening the primary operational representation. Deferring baselines and wellness prevents structural analysis from silently deciding history eligibility or prediction-time ordering.

**Alternatives Considered:**
Enter all 35 candidates simultaneously, rejected because the catalogue intentionally contains highly redundant alternatives. Carry daily load and session sRPE together as independent primary signals, rejected because their current and rolling relationships are near deterministic. Use all four rolling windows in the compact contract, rejected because adjacent windows are uniformly highly correlated. Drop session duration, rejected because its positive-recorded-day relationship with daily load is materially less redundant. Freeze prior baselines and lagged wellness now, deferred because their history, coverage, leakage and cohort effects belong to Stages 6 and 7. Select features from outcome association or model performance in Stage 4, rejected because the stage is explicitly target-blind.

**Consequences:**
Stage 5 descriptive outcome-context analysis may compare approved descriptive feature families around episode onset without using that retrospective evidence to silently expand the primary operational contract. Stage 6 must quantify horizon, episode-gap, burn-in, wellness-history and baseline-history sensitivities. Stage 7 must construct the final predictor allow-list, lagged wellness features, train-only preprocessing and leakage controls. Later model comparisons may test deferred full-contract alternatives as labelled sensitivities, but headline models must not present redundant daily-load/session-sRPE or adjacent-window variants as independent evidence.

**Affected Components:** feature contracts, descriptive analysis, feature engineering, cohort sensitivity, preprocessing, leakage controls, modelling experiments, interpretation

**Supersedes:** none
**Superseded By:** none

---

## DEC-034

**Decision ID:** DEC-034
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
Stage 5 compared 68 complete-history player-date onsets with clean same-player calendar and reporting-matched reference periods. The matched events come from 13 players; the top five contribute 80.9%, 53 events overlap another onset within plus or minus 28 days, and only 15 are isolated. Event windows generally show lower recorded-session frequency, daily load and session duration than calendar references. Observed fatigue is directionally higher and readiness lower over some windows, but player-cluster intervals are wide, wellness reporting differs between event and reference periods, and isolated-onset sensitivities commonly include zero. Day 0 shows strong recording changes but was excluded from primary pre-onset summaries.

**Decision:**
Accept Stage 5 as a valid retrospective descriptive outcome-context analysis with constrained interpretation. Treat reduced observed exposure, lower session-recording frequency and weak wellness differences before recorded onset as hypotheses for later prospective testing, not as predictive, causal or medical evidence. Do not promote, remove or rank predictors from these retrospective associations. Keep day-0 values descriptive-only and preserve the `DEC-031` prohibition on same-day wellness and reporting fields in the primary predictor contract. Retain player-equal summaries, player-cluster uncertainty, overlapping-window disclosure and isolated-onset sensitivity as required interpretation controls. Authorise Stage 6 specification review, but not Stage 6 implementation, to quantify episode-gap, prediction-horizon, burn-in, history and missingness-aware cohort choices.

**Rationale:**
The directional exposure patterns are not stable enough to support feature selection or operational claims. Most events are clustered, evidence is concentrated in a small number of players, and the recording process changes around onset. Preserving the patterns as explicit hypotheses allows later prospective evaluation without overstating what retrospective EDA establishes. Freezing cohort and outcome choices only after Stage 6 sensitivity analysis keeps sample-support and representation trade-offs visible.

**Alternatives Considered:**
Interpret lower load as protective or harmful, rejected because Stage 5 is non-causal and recording/exposure semantics are unresolved. Select features from the strongest matched differences, rejected because this would use outcome association before the prospective protocol is frozen. Exclude overlapping events or high-contribution players immediately, deferred because Stage 6 must quantify the effect on sample size, positive support and representation. Include day-0 wellness or reporting signals, rejected because timing and outcome-entanglement risks remain. Begin modelling after Stage 5, rejected because Stages 6 through 8 remain mandatory gates.

**Consequences:**
Stage 6 must report the sample-size, event-support, player/team representation and concentration consequences of every candidate cohort and outcome rule. Stage 7 may freeze predictors and validation only after the Stage 6 primary and secondary specifications are approved. Stage 5 findings may motivate pre-specified later comparisons but cannot silently alter the provisional feature-family policy in `DEC-033`.

**Affected Components:** outcome interpretation, cohort sensitivity, feature selection, leakage controls, validation, modelling claims, practitioner communication

**Supersedes:** none
**Superseded By:** none

---

## DEC-035

**Decision ID:** DEC-035
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
Stage 6 rebuilt all nine combinations of 1/3/7-day episode-gap rules and 3/7/14-day horizons through production outcome functions. Under the accepted three-day gap, the broad seven-day cohort contains 35,992 eligible player-days, 370 positive player-days and 71 represented onsets across 15 event-bearing players. A 28-day burn-in retains 34,600 eligible days, 66 represented onsets and 13 event-bearing players. Requiring seven prior wellness reports retains 60 onsets; requiring robust load-baseline eligibility retains 55. The combined history subset retains 70.5% of broad eligible days and 54 onsets. The top five players contribute 74.6% of broad represented onsets.

**Decision:**
Freeze the three-day episode-gap rule as the primary outcome construction and seven-day future player-date onset as the primary fixed-horizon target. Freeze a 28 strictly prior calendar-day burn-in in addition to horizon completeness and active-episode exclusion for the primary cohort. Do not require wellness-report history or player-baseline availability for primary cohort entry. Pre-specify three- and fourteen-day horizons as secondary targets; one- and seven-day episode-gap rules as outcome-definition sensitivities; and the broad no-burn-in cohort as a mandatory cohort sensitivity. Retain wellness-rich, robust-baseline, 56-day and 90-day history subsets as labelled secondary analyses rather than primary exclusions. Never use isolated-onset status as a prospective eligibility filter. Require later evaluation to disclose player/team/time concentration and represented-onset support.

**Rationale:**
The three-day episode rule remains the evidence-led intermediate between fragmentation and over-merging. Seven days preserves nearly all represented onset support while offering a more useful review horizon than three days and less temporal dilution than fourteen days. A 28-day burn-in aligns with the longest compact operational accumulation window and removes relatively few player-days, although its event-support cost must remain visible through the mandatory broad-cohort sensitivity. Wellness and robust-baseline gates would select materially narrower reporting-rich cohorts and reduce already limited event support.

**Alternatives Considered:**
Use a one-day episode gap, rejected as primary because it fragments repeated reports into 108 onset dates. Use a seven-day gap, rejected because it over-merges reports and leaves only 47 represented seven-day-horizon onsets. Use a three-day horizon, retained as secondary but rejected as primary because it represents only 68 onsets with shorter practitioner lead time. Use a fourteen-day horizon, retained as secondary but rejected as primary because it increases positive-row dependence around the same 71 onsets. Use no burn-in, retained as mandatory sensitivity but rejected as primary because 28-day operational features would have incomplete early history. Require wellness or robust-baseline eligibility, rejected as primary because these restrictions materially reduce event and event-player support.

**Consequences:**
Stage 7 must encode the primary and secondary cohort/outcome contracts, freeze the predictor allow-list and prediction-time feature construction, define train-only preprocessing, construct chronological boundaries with appropriate embargo controls, and pre-specify rolling-origin and unseen-player stress tests. Stage 8 must judge readiness using this frozen protocol. No modelling is authorised until Stage 8 returns `READY`.

**Affected Components:** outcome labels, cohort eligibility, feature history, sensitivity analysis, validation, leakage controls, modelling protocol, claims

**Supersedes:** none
**Superseded By:** none

---

## DEC-036

**Decision ID:** DEC-036
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
After Stage 6 froze the primary outcome and cohort, the project required a complete prospective protocol before the pre-model readiness gate. Same-day wellness remains outcome-entangled and its intraday ordering is unavailable. Existing prior z-scores are unstable, daily load and session sRPE are near duplicates, and effective outcomes are concentrated across a small number of players and periods. The project owner approved the Stage 7 specification before implementation.

**Decision:**
Freeze the Stage 7 prospective protocol as follows. Use a model ladder in which F0 is global training prevalence with no predictors; F1 contains current/7-day/28-day `log1p` daily-load representations plus strictly lagged fatigue/readiness and prior 7-day/28-day wellness means; F2 adds session-recording state, session count, current/7-day/28-day `log1p` duration and strictly prior reporting indicators/counts; F3 adds nullable strictly prior robust player-relative load, fatigue and readiness features with explicit availability indicators. Test session sRPE only as a replacement for the daily-load family, never alongside it. Prohibit identities, raw dates, same-day wellness/reporting, outcomes, active-episode/follow-up fields, source identifiers and existing unstable z-scores.

Freeze the primary chronological partitions at training `2020-01-29` through `2020-12-24`, validation `2021-01-01` through `2021-06-23`, and locked final test `2021-07-01` through `2021-12-24`, with seven-day embargo periods between partitions. Use matching horizon-length embargoes for 3-day and 14-day sensitivities. Use expanding rolling-origin development folds and leave-one-player-out development stress tests; prohibit random row-level headline splitting. Fit imputation, scaling, feature selection, weighting and calibration only within the appropriate training/development scope. Pre-specify Brier score and average precision as primary later metrics; calibration, log loss, ROC-AUC and practitioner-facing alert/event-capture measures as secondary or operational metrics; 1%, 2.5% and 5% review-rate budgets; and player-cluster plus temporal-block uncertainty.

**Rationale:**
This contract preserves legitimate end-of-day exposure information while rebuilding wellness and personalisation features from strictly earlier observations. The feature ladder tests added information in interpretable stages and prevents redundant load representations from masquerading as independent evidence. Calendar partitions and embargoes preserve temporal order and prevent target windows from crossing evaluation boundaries. Pre-specifying evaluation, uncertainty and alert-capacity rules reduces opportunistic model selection and keeps outputs aligned with practitioner review rather than diagnosis.

**Alternatives Considered:**
Use same-day wellness, rejected because prediction-time ordering is unresolved and reporting changes around onset. Include all candidate rolling windows and both load/sRPE families, rejected because Stage 4 demonstrated severe redundancy. Use player/team identifiers, rejected because memorisation would undermine transfer claims. Use random row splits, rejected because repeated player-days and temporal dependence would leak context. Choose split dates after model performance inspection, rejected; boundaries are frozen before modelling. Require robust-feature availability for cohort entry, rejected because Stage 6 showed material support loss. Use a single unconstrained threshold, rejected because practitioner capacity must be explicit.

**Consequences:**
Stage 7 may inspect only cohort, predictor coverage, partition support and leakage evidence; it may not fit models or inspect final-test performance. The completed audit records sparse validation/test onset support, one zero-positive rolling validation window, 38 zero-positive player holdouts and very low robust-fatigue coverage. Stage 8 must determine whether these limitations are compatible with a narrow baseline experiment and must return `READY` before any model is fitted. Final-test performance remains locked until model selection and calibration choices are complete.

**Affected Components:** feature engineering, predictor contracts, cohort assignment, chronological validation, leakage controls, preprocessing, metrics, uncertainty, alert policy, modelling gate

**Supersedes:** none
**Superseded By:** `DEC-047`, in respect of headline-evaluation designation only. All other frozen elements of this decision, including partition boundaries, embargoes, predictor contracts, prohibited fields, preprocessing scope and the final-test lock, remain in force unchanged.

---

## DEC-037

**Decision ID:** DEC-037
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
The Stage 7 prospective protocol and leakage audit completed with zero failures, one warning and three review findings. All prediction-time, embargo, future-append, preprocessing-scope and final-test-lock checks passed. Validation and test each contain five represented onsets; one late rolling-origin window contains no positive player-days; 38 of 50 held-out players contain no positive development days; and the robust fatigue feature is available on only 8.4% of primary-cohort days.

**Decision:**
Accept the Stage 7 results interpretation as `PASS WITH LIMITATIONS` and authorise Stage 8 specification review. Preserve the frozen chronological partitions, embargoes, predictor/prohibition contract, final-test lock and support-aware evaluation rules from `DEC-036`. Treat the zero-positive rolling window as a temporal stress window rather than a discrimination or calibration fold. Treat leave-one-player-out results as support-aware stress evidence rather than 50 independently estimable performance folds. Keep F3 player-relative features incremental and secondary, with robust-fatigue availability disclosed explicitly. Do not interpret sparse validation/test support as evidence against all modelling, but require Stage 8 to decide whether a narrow, exploratory baseline programme is defensible and to constrain claims accordingly.

**Rationale:**
The protocol is internally leak-safe and reproducible, so the identified limitations concern inferential support rather than a correctable integrity failure. Rejecting all modelling would discard the value of a carefully bounded baseline experiment, while ignoring the limitations would produce unjustified precision and generalisation claims. A final readiness gate can distinguish a narrow portfolio-grade experiment from operational or medical validation.

**Alternatives Considered:**
Reject Stage 7 and redesign the split to manufacture more balanced event counts, rejected because changing frozen calendar boundaries after support inspection would introduce outcome-driven selection. Treat every rolling and player holdout as a conventional estimable fold, rejected because many lack positive support. Promote F3 to the primary feature set despite sparse robust-fatigue coverage, rejected. Begin modelling immediately, rejected because Stage 8 remains the mandatory readiness gate.

**Consequences:**
Stage 8 must consolidate Stages 0-7 into one evidence register, map every limitation to a mandatory modelling control, freeze the final hypotheses and launch checklist, and return exactly one recommendation: `READY`, `REVISE` or `DO NOT MODEL`. No model, prediction, threshold selection or final-test performance access is authorised by this decision.

**Affected Components:** readiness assessment, validation interpretation, feature-set hierarchy, generalisation claims, modelling launch gate, final-test governance

**Supersedes:** none
**Superseded By:** none

---

## DEC-038

**Decision ID:** DEC-038
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
The project owner approved the Stage 8 pre-model readiness specification after Stage 7 was accepted as `PASS WITH LIMITATIONS`. The final gate needed to consolidate approved Stage 0-7 evidence without averaging away hard failures, convert material limitations into enforceable modelling controls, freeze hypotheses and launch sequencing, and protect the uninspected final test.

**Decision:**
Use a binary hard-gate readiness method rather than a numeric score. Consolidate each Stage 0-7 manifest, findings register and report with content hashes. Require hard gates for evidence completeness, stage integrity, outcome reproduction, missingness semantics, feature integrity, cohort/split integrity, leakage prevention, final-test governance, pre-model isolation, minimum exploratory outcome support, protocol completeness and notebook/lockfile reproducibility. Any failed gate returns `REVISE` unless its declared disposition is `DO NOT MODEL`; only zero failed gates may return `READY`.

Require every material limitation to have a mandatory modelling or claim control. Freeze the final hypothesis register, M0/M1-first launch sequence, M2+ complexity deferral and ten-item final-test access checklist. Stage 8 must return exactly one provisional recommendation from `READY`, `REVISE` or `DO NOT MODEL`; that recommendation never authorises modelling by itself and requires separate project-owner approval. Stage 8 may not fit a model, generate predictions, select thresholds, compute performance metrics or inspect final-test performance.

**Rationale:**
Hard-gate logic prevents numerous routine passes from masking an outcome, leakage or governance failure. Explicit limitation-to-control mapping preserves sparse temporal/player support, reporting-process risks and validity constraints as obligations rather than footnotes. Separating the generated recommendation from owner authorisation preserves the agreed stage-gated control process.

**Alternatives Considered:**
Use a weighted readiness score, rejected because a fatal leakage or outcome failure could be averaged away. Treat sparse support as an automatic prohibition, rejected because all partitions retain positive onset support and a narrow exploratory baseline remains potentially informative under strict controls. Treat `READY` as deployment readiness, rejected because no prospective club, external-team or medical validation exists. Begin M2 tree or survival modelling immediately after readiness, rejected because complexity must be earned through M0/M1 evidence.

**Consequences:**
The completed Stage 8 report provisionally recommends `READY` for a narrow exploratory M0/M1 subjective-data baseline programme because all 12 hard gates pass. Twelve mandatory constraints remain binding. Modelling is still prohibited until the project owner separately approves the Stage 8 `READY` recommendation and that approval is recorded as a new decision. Final-test performance remains locked.

**Affected Components:** readiness methodology, evidence provenance, hypothesis register, modelling sequence, limitation controls, final-test governance, owner approval gate

**Supersedes:** none
**Superseded By:** none

---

## DEC-039

**Decision ID:** DEC-039
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
Stage 8 passed all 12 binary hard gates and provisionally recommended `READY` for a narrow exploratory M0/M1 subjective-data baseline programme subject to 12 mandatory modelling and claim controls. The project owner reviewed the modelling plan, explicitly approved `READY`, and approved the staged M0/M1 workflow. A concrete first experiment specification was required before any model-derived validation result could be produced.

**Decision:**
Accept the Stage 8 `READY` recommendation and authorise the narrow exploratory subjective-data baseline programme. Implement and run EXP-002 M0 on training and validation data only before M1. M0 comprises the global training-period prevalence baseline and one pre-specified recent-load heuristic based on the frozen `daily_load_sum_7d_log1p` predictor, with all heuristic thresholds and probability mappings learned from training only. Report probability quality where defined, rare-event ranking, fixed-capacity alerts, represented-onset capture, lead time, alert burden, support counts and player-cluster plus temporal-block uncertainty.

Use shared modelling code, a canonical job, a matching output-free notebook, versioned configuration and retained outputs under `outputs/modelling/exp_002_m0_baselines/`. Do not evaluate or persist final-test predictions. M1 implementation remains blocked until the project owner reviews and accepts or revises the M0 benchmark. A later one-time final-test job requires a separate explicit authorisation after model, preprocessing, calibration, alert policy and sensitivities are frozen.

**Rationale:**
The readiness evidence supports a bounded baseline experiment but not broad predictive, medical or deployment claims. Running M0 first establishes an honest minimum benchmark and exposes prevalence shift, calibration and practitioner workload before fitting a learned multivariable model. Separating development jobs from the future final-test job reduces accidental test access and preserves the prospective protocol.

**Alternatives Considered:**
Begin M0 and M1 together, rejected because M0 results must establish and validate the benchmark before the learned model is interpreted. Evaluate the final test during baseline development, rejected because model and policy choices are not frozen. Add a past-injury recency heuristic now, rejected because no such feature is present in the frozen predictor contract. Treat the recent-load heuristic as a causal workload threshold, rejected because the data supports only a descriptive comparator.

**Consequences:**
The modelling process block is lifted only for EXP-002 M0 development. All Stage 8 limitations remain binding. The final test stays locked, M1 remains pending M0 review, M2+ remains deferred, and retained outputs must clearly describe self-reported injury-related onset risk and practitioner review rather than diagnosis or clearance.

**Affected Components:** modelling authorisation, M0 baseline, development validation, alert simulation, uncertainty, output contract, final-test governance

**Supersedes:** none
**Superseded By:** none

---

## DEC-040

**Decision ID:** DEC-040
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
EXP-002 M0 completed on the frozen training and validation partitions with no final-test performance access. The global training-prevalence baseline produced validation Brier 0.003405, average precision 0.003222 and ROC-AUC 0.500000. The pre-specified recent-load heuristic produced worse Brier 0.003544, average precision 0.002934 and ROC-AUC 0.477210, and captured zero of five represented validation onsets at the frozen 1%, 2.5% and 5% review budgets. Training prevalence was 1.711% versus 0.322% in validation, and the training 95th-percentile load threshold flagged 10.8% of validation rows, evidencing temporal outcome and feature-distribution shift. The project owner reviewed and accepted the benchmark evidence.

**Decision:**
Accept EXP-002 as the official M0 benchmark. Retain global training-period prevalence as the minimum probability benchmark for M1. Retain the recent-load result as a failed descriptive comparator demonstrating that seven-day load alone did not transfer prospectively in this validation period. Do not promote either M0 baseline as an operational model, do not infer a protective or causal load effect, and do not alter the frozen validation or final-test periods in response to the result. Authorise EXP-003 M1 specification review; model fitting still requires approval of the exact M1 implementation specification.

**Rationale:**
The M0 implementation passed partition, training-scope, prediction-validity, uncertainty and final-test-isolation controls. Its poor predictive utility is valid benchmark evidence rather than an implementation failure. Freezing the result preserves an honest comparison for learned models and prevents redesigning the benchmark after seeing validation outcomes.

**Alternatives Considered:**
Revise the load threshold to improve validation capture, rejected because that would tune the heuristic after inspecting validation outcomes. Reject M0 because it performs poorly, rejected because M0 exists to establish a minimum benchmark rather than to qualify as a useful model. Interpret below-chance recent-load ranking as biological protection, rejected because sparse outcomes, temporal shift and observational data do not support causal interpretation. Begin final-test evaluation, rejected because M1, calibration and alert-policy choices are not frozen.

**Consequences:**
M1 must be compared against the frozen global-prevalence benchmark on the same development dates and must demonstrate meaningful calibration or operational-capture value rather than merely a higher in-sample score. The recent-load comparator remains visible in reports. M1 specification review is open; final-test performance remains locked and M2+ remains deferred.

**Affected Components:** M0 benchmark, M1 comparison criteria, temporal validation, alert simulation, claims, final-test governance

**Supersedes:** none
**Superseded By:** none

---

## DEC-041

**Decision ID:** DEC-041
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
After accepting M0 under `DEC-040`, the project required an exact first learned-model specification before fitting. The approved specification limits EXP-003 initially to F1 absolute load and strictly prior wellness predictors, preserves the frozen chronological development partitions, and separates raw-model comparison from later post-hoc calibration selection.

**Decision:**
Authorise development-only EXP-003 M1-F1 regularised logistic regression. Use the nine frozen F1 predictors: current/7-day/28-day `log1p` daily load; lag-one fatigue/readiness; and strictly prior 7-day/28-day fatigue/readiness means. Fit training-only median imputation with explicit missing indicators and standard scaling. Use L2 logistic regression with `lbfgs`, maximum 5,000 iterations and finite `C` grid `[0.001, 0.01, 0.1, 1.0, 10.0]`; keep the primary model unweighted. Select by validation Brier, then average precision, then stronger regularisation for ties.

Compare the selected raw F1 model with the frozen M0 global-prevalence benchmark using Brier, log loss, average precision, ROC-AUC, calibration diagnostics, 1%/2.5%/5% capacity-bounded alert simulation, onset capture and lead time. Run expanding rolling-origin and support-aware leave-one-player-out development stress tests plus player-cluster and temporal-week uncertainty. Persist shared code, versioned configuration, canonical job, matching output-free notebook, validation-only predictions, candidate model and reports under `outputs/modelling/exp_003_m1_logistic/f1/`. Do not select Platt or isotonic calibration yet. Do not fit F2/F3 or access final-test performance before F1 owner review.

**Rationale:**
F1 is the smallest interpretable learned model that tests whether absolute load and legitimate prior wellness add prospective value beyond prevalence. A finite, strongly regularised grid constrains search under limited events. Delaying post-hoc calibration until feature-family comparison avoids separately tuning every feature set to the sparse validation outcome, while raw calibration diagnostics keep probability quality visible.

**Alternatives Considered:**
Fit F1/F2/F3 together, rejected because incremental feature-family value should be reviewed sequentially. Use same-day wellness, rejected under the prediction-time and outcome-entanglement controls. Make balanced class weighting primary, rejected because it can distort probability calibration; it remains a later labelled sensitivity if required. Select by AUROC, rejected because rare-event probability quality and operational capture are primary. Tune on final test, rejected outright.

**Consequences:**
M1-F1 code and development evaluation are authorised. M1-F2, M1-F3, post-hoc calibration selection, horizon sensitivities, M2+ and final-test performance remain blocked. The resulting F1 candidate requires a separate owner `PROMOTE`, `REVISE` or `REJECT` decision.

**Affected Components:** modelling dependencies, preprocessing, logistic regression, development validation, calibration diagnostics, alert simulation, uncertainty, model artifacts, final-test governance

**Supersedes:** none
**Superseded By:** none

---

## DEC-042

**Decision ID:** DEC-042
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
EXP-003 M1-F1 completed development-only evaluation with validation Brier 0.003700, log loss 0.031272, average precision 0.016640 and ROC-AUC 0.807802. Relative to M0, F1 materially improves rare-event ranking and captures four of five represented onsets at the 5% review budget, but worsens probability accuracy and overestimates mean risk at 2.005% versus 0.322% observed. The project owner reviewed this trade-off and selected `PROMOTE` so that the frozen incremental feature ladder can be evaluated.

**Decision:**
Promote M1-F1 as the active development reference for further feature-family ablation. This promotion does not make F1 an operational or deployed model, does not accept its raw probabilities as calibrated risk, and does not authorise final-test access.

Authorise the development-only EXP-003 extension for both M1-F2 and M1-F3. F2 is cumulative F1 plus the eight frozen session-exposure and strictly prior reporting-process predictors. F3 is cumulative F2 plus the six frozen strictly prior robust player-relative values and availability indicators. Fit each feature set independently using the same primary cohort, target, chronological train/validation partitions, embargoes, training-only median imputation with indicators, scaling, unweighted L2 logistic regression, `lbfgs`, 5,000-iteration limit and `C` grid `[0.001, 0.01, 0.1, 1.0, 10.0]` used for F1. Select `C` within each feature set by lowest validation Brier, then higher average precision, then stronger regularisation.

Compare F1, F2 and F3 using raw Brier, log loss, average precision, ROC-AUC, calibration intercept/slope, reliability, fixed 1%/2.5%/5% review budgets, represented-onset capture, false alerts per captured onset, rolling-origin evidence, support-aware leave-one-player-out evidence and player/week bootstrap uncertainty. Report incremental feature-family effects and predictor availability explicitly. Do not select a post-hoc calibrator, run horizon alternatives or access final-test predictions/performance. Stop after the F2/F3 development report for owner selection of the raw feature-set candidate and calibration-experiment scope.

**Rationale:**
F1 demonstrates enough prospective ranking signal to justify testing whether operational session context and player-relative state add stable value. Keeping model class, splits, tuning grid and evaluation constant makes F2 and F3 controlled feature-family ablations rather than new modelling searches. Running the already frozen F2 and F3 contracts in one extension avoids another validation-dependent redesign while preserving a decision gate before calibration and final test.

**Alternatives Considered:**
Reject F1 because raw Brier is worse than M0, rejected because ranking and capacity-bounded onset capture provide sufficient exploratory value for controlled ablation. Treat F1 as deployment-ready, rejected because calibration and sparse-support limitations are material. Add F2 only and defer F3, rejected because both contracts were frozen before F1 fitting and the owner explicitly authorised moving through F2/F3. Tune new hyperparameters or class weights per feature set, rejected because that would confound feature-family comparison. Select calibration now, rejected because the raw feature set must be chosen first. Access final-test performance, rejected because model and calibration choices remain open.

**Consequences:**
M1-F2 and M1-F3 implementation and development evaluation are authorised under the existing script/notebook/output contract. F1 remains the comparison reference, not an operational model. Calibration selection, horizon sensitivities, M2+, product serving and final-test performance remain blocked. The completed extension requires a new owner decision before any calibrator is fitted or final-test access is considered.

**Affected Components:** M1 feature ladder, preprocessing, regularised logistic regression, development validation, feature ablation, calibration diagnostics, alert simulation, uncertainty, model artifacts, final-test governance

**Supersedes:** none
**Superseded By:** none

---

## DEC-043

**Decision ID:** DEC-043
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
The EXP-003 feature ladder completed development-only evaluation of three cumulative predictor sets: F1 with 9 predictors, F2 with 17 and F3 with 23. Automated status was `PASS WITH REVIEW`, with `LADDER-04` raw feature-set selection and `LADDER-06` calibration scope left explicitly to the project owner. No calibrator was fitted and no final-test prediction or performance was produced.

**Decision:**
Reject F2. Promote **F3** as the raw M1 candidate feature set, carried forward into calibration under `DEC-044`.

F3 is promoted as a *development candidate only*. This decision does not establish deployment readiness, does not authorise any final-test access, and does not license any performance claim outside the constraints recorded below.

**Rationale:**
F3 leads every held-period metric: Brier 0.003613 against 0.003700 for F1, log loss 0.030367 against 0.031272, average precision 0.019432 against 0.016640, and ROC-AUC 0.851053 against 0.807802. It is the only feature set to capture an onset at the tight 1% review budget, and it records the lowest false-alerts-per-capture at the 5% budget. Under temporal week-block resampling the F2-to-F3 Brier interval is [-0.000151, -0.000044], excluding zero in the candidate's favour. Since `DEC-007` makes calibration a first-class metric, the probability-quality gain in Brier and log loss is the most directly relevant evidence for the calibration experiment that follows.

F2 is rejected on clean evidence: its Brier intervals exclude zero in the *wrong* direction under both resampling schemes, [0.000000, 0.000029] and [0.000007, 0.000017], while average precision is no better. Eight additional predictors delivered no measurable gain, which is exactly the outcome `DEC-006` requires to be acted on.

**Alternatives Considered:**
Retaining F1 as the reference and rejecting F3. This was the analytically recommended option and the counter-evidence for it is material, recorded below rather than omitted. Carrying both F1 and F3 into calibration, rejected as deferring a selection the owner elected to settle now.

**Counter-evidence accepted with this decision.**
This decision is taken with the following limitations understood and on record. They are binding on all downstream reporting.

1. **Support is critically thin.** The validation period contains five onsets. The entire alert-budget comparison rests on those five events, and F3's tight-budget advantage is a single event, 1/5 against 0/5. No operational claim may be made from this comparison.
2. **The advantage reverses on unseen players.** F1 records unseen-player AP 0.023316 and ROC-AUC 0.642578; F3 records 0.022308 and 0.630928. Under `DEC-004` unseen-player generalisation is mandatory evidence, and on that axis F3 is the weaker set. Only 12 of 50 players are estimable.
3. **Temporal stability is poor.** Rolling-origin average precision for F3 is 0.232634, 0.016345, 0.047624 across the three folds. The second fold is roughly half the F1 value of 0.030987.
4. **Only one of four paired intervals excludes zero.** Under player-cluster resampling, the more conservative and more deployment-relevant scheme, neither the Brier nor the average-precision interval excludes zero.
5. **The distinguishing predictor is sparse and entangled.** The robust fatigue z-score is observed on 8.4% of primary-cohort days, triggering `LADDER-05`. Its coefficient is confounded with availability and reporting structure, the precise risk `DEC-031` was written to control. Any apparent contribution from this predictor must be treated as potentially a reporting-process artefact rather than a physiological signal.

**Consequences:**
- F3 becomes the raw candidate entering `EXP-009`. F1 is retained as the comparison reference and is not deleted.
- Every model card, report, dashboard surface and portfolio or interview artefact that cites F3 must also carry limitations 1 through 5. Reporting F3's held-period metrics without the unseen-player reversal and the five-onset support is prohibited.
- The unseen-player reversal must be re-examined once support improves. If F3 does not recover on unseen-player evidence at a later gate, this decision is revisited through a new superseding record.
- The 8.4%-coverage robust fatigue predictor is placed under explicit audit in `EXP-009`. If calibration behaviour proves sensitive to its availability pattern, it is a candidate for removal.
- Final-test predictions and performance remain locked.

**Affected Components:** M1 feature-set selection, calibration experiment scope, model card, reporting constraints, portfolio and interview claims, final-test governance

**Supersedes:** none
**Superseded By:** none

---

## DEC-044

**Decision ID:** DEC-044
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
M1 raw probabilities are materially overestimated on validation and record worse Brier and log loss than the M0 operational baseline despite better ranking. `DEC-007` makes calibration a first-class metric, so a ranking improvement that degrades probability quality cannot be promoted as-is. `LADDER-06` left calibration scope open pending an explicit specification.

**Decision:**
Authorise `EXP-009`: a separate calibration experiment comparing raw, Platt and isotonic calibration on the F3 candidate, using development data only.

**Rationale:**
Practitioners act on the magnitude of a risk estimate, not only its order. A model that ranks well but states probabilities that are systematically too high would misdirect review effort and cannot be defended. Isolating calibration into its own experiment keeps the method choice separable from feature-set selection and prevents calibration decisions being made implicitly inside a modelling run.

**Alternatives Considered:**
Deferring calibration until the five-onset support problem is addressed through a cohort or horizon change. This has real force, since calibration curves estimated on five events will be close to uninformative, and it is recorded here as a live methodological risk rather than dismissed. Not selected: the overestimation is already measured and characterising it now is cheap and reversible.

**Consequences:**
- Scope is raw against Platt against isotonic on F3. F1 is retained as a reference comparison.
- Development data only. No final-test prediction or performance may be produced, read or reported.
- Required outputs: reliability curves, calibration slope and intercept, expected calibration error, Brier and log loss, each reported with the five-onset support caveat stated inline rather than in a footnote.
- Calibration must be assessed for sensitivity to the 8.4%-coverage robust fatigue predictor, per `DEC-043`.
- **Power limitation is binding.** With five validation onsets, calibration estimates carry very wide uncertainty. Any conclusion that one calibration method beats another must state this explicitly. "No method is distinguishable at this support" is an acceptable and expected result, and must be reported as such rather than resolved by picking the best point estimate.
- A specification must be approved before implementation, consistent with the stage-gated model used since Stage 0.

**Affected Components:** calibration methodology, M1 promotion path, model card, evaluation reporting, final-test governance

**Supersedes:** none
**Superseded By:** none

---

## DEC-045

**Decision ID:** DEC-045
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
Twenty-seven committed analysis reports, run manifests and configuration files persistently showed as fully modified with no content change: 1051 insertions against 1051 deletions, with an end-of-line-insensitive diff returning empty. The repository held LF, `core.autocrlf` was unset and no `.gitattributes` existed, so Windows-side tooling rewrote endings on every write.

**Decision:**
Adopt an explicit line-ending policy. `.gitattributes` fixes LF in both the repository and the working tree via `* text=auto eol=lf`, with explicit binary rules for Parquet, model artefacts, archives and images. The repository was renormalised in a single isolated commit.

**Rationale:**
The affected files are analysis reports and run manifests carrying experimental evidence. Whole-file phantom diffs make it impossible to see what genuinely changed between experiment runs, which directly undermines review. Fixing the working tree to LF rather than native endings additionally keeps local files byte-identical to what executes inside the Linux containers used for cloud execution, removing a class of CRLF failure in shell scripts and Docker builds before it can occur.

**Alternatives Considered:**
Setting `core.autocrlf` locally, rejected because it is per-machine configuration rather than a property of the repository and would not travel with a clone. Leaving the churn in place, rejected because it recurs on every write and degrades reviewability of the evidence trail.

**Consequences:**
Renormalisation settled all twenty-seven files with no content change; only the new `.gitattributes` and an end-of-line-only update to `.gitignore` were recorded, at commit `df735d5`. Binary artefacts are explicitly protected from transformation. Future contributors inherit the policy automatically on clone.

**Affected Components:** repository architecture, version control hygiene, review process, container build reliability

**Supersedes:** none
**Superseded By:** none

---

## DEC-046

**Decision ID:** DEC-046
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
The project needed an explicit definition of a shippable V1 before further development. Partition support was quantified as 56 onsets in train, five in validation and five in final test, against 66 represented onsets in the frozen cohort and 71 in the broad candidate cohort. Reported onsets fall roughly tenfold from 2020 to 2021 while player-days remain flat, which combined with the Stage 2 reporting-engagement evidence indicates decaying self-report participation rather than reduced injury incidence. Five players contribute 74.6% of onsets, so the effective sample is closer to a dozen athletes than fifty.

**Decision:**
V1 is defined as a complete subjective-data decision-support system whose primary evidence is methodological rigour and product completeness, not discrimination performance.

V1 scope:
1. `EXP-009` calibration of the F3 candidate.
2. A Cox proportional-hazards survival model, providing the charter-required conclusion on whether time-to-event framing adds value.
3. M2 gradient boosting executed as a deliberate complexity test under `DEC-006`.
4. Explainability and uncertainty surfaces.
5. Batch inference into `paa_product`.
6. A practitioner dashboard on Cloud Run covering squad, player, data-quality and model-health views.
7. A model card leading with limitations.
8. Containerisation, CI and reproducibility.
9. Exactly one pre-registered final-test evaluation, spent once on the single champion at the end of the programme.
10. Portfolio artefacts: README, architecture diagram, case study and interview narrative.

Explicitly deferred to V2: objective GPS ingestion and processing, neural survival models, online serving.

**Rationale:**
The available outcome support cannot sustain a claim of the form "this system predicts injuries". Pursuing a headline discrimination figure would produce a number that collapses under scrutiny, and the concentration and reporting-decay findings mean it would not transfer. Defining V1 around a leak-safe pipeline, calibrated risk with visible uncertainty, quantified support limits and an operable practitioner product converts the dataset's weakness into demonstrated judgement.

This is consistent with the charter, which states that success is not defined by a single AUROC and lists methodological judgement, responsible predictive modelling and stakeholder communication as the success criteria.

Including Cox is not optional dressing. Time-to-event framing uses censoring and the full event set rather than a five-event fixed window, so it is the modelling response most appropriate to sparse support, and the charter requires an explicit conclusion on whether it adds value.

Including M2 is expected to yield a negative result at this sample size. That is a deliberate and reportable outcome demonstrating the `DEC-006` ladder discipline in practice.

**Alternatives Considered:**
A lean V1 taking calibrated M1-F3 straight to product, rejected because it drops the survival conclusion the charter requires and discards the strongest available response to sparse events. An extended V1 including a GPS pilot, rejected because it adds material time and cost while being unable to relieve the outcome-support limit that constrains every model claim; it remains the natural V2 opening.

**Consequences:**
- Delivery is governed by section 5A of `19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md`, with owner approval gates preserved as used since Stage 0. Phases map onto experiment identifiers already registered there: V1-P1 is EXP-009, V1-P2 is EXP-007, V1-P3 is EXP-008, and V1-P4 draws on EXP-018 and EXP-019. No new experiment identifiers are allocated.
- No V1 artefact may present discrimination performance as the headline result.
- The final-test partition is spent exactly once, on a pre-registered champion and pre-registered claims. Any second access requires a new superseding decision.
- GPS work remains prohibited for the duration of V1.

**Affected Components:** delivery scope, modelling programme, product, documentation, portfolio material, final-test governance

**Supersedes:** none
**Superseded By:** none

---

## DEC-047

**Decision ID:** DEC-047
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
`DEC-036` froze a single chronological validation window as the headline evaluation. That window contains five represented onsets across three players. Every comparison made against it is therefore underpowered, and the EXP-003 feature ladder demonstrated the consequence directly: only one of four paired intervals excluded zero, and a single event separated the feature sets at the tight review budget.

**Decision:**
Pooled rolling-origin evaluation across the full development period becomes the **headline** evaluation. The fixed chronological validation window is retained as a secondary temporal stress result.

This supersedes `DEC-036` in respect of headline designation only. Partition boundaries, embargoes, predictor contracts, prohibited fields, preprocessing scope, leakage controls and the final-test lock are unchanged and remain in force.

**Rationale:**
Rolling-origin evaluation respects chronology exactly as the fixed window does, since every fold trains only on the past and tests on the future. It aggregates across substantially more events, which is the only way to obtain usable inferential precision from this dataset without weakening any leakage control. Changing which chronologically valid view is primary does not relax rigour; retaining a five-event window as the headline would knowingly report conclusions the data cannot support.

**Alternatives Considered:**
Retaining the single window as headline, rejected because it guarantees that most comparisons resolve to "not distinguishable" while still inviting readers to over-read point estimates. Reporting both with equal weight and no designated primary, rejected because it leaves a reviewer without an answer and creates room for post-hoc selection between two views.

**Consequences:**
- Pooled rolling-origin metrics are the primary reported result for all V1 model comparisons.
- Folds with zero positive held-out days must be reported as such and excluded from discrimination aggregation rather than silently dropped, with the count of estimable folds stated alongside every pooled figure.
- Per-fold results accompany every pooled figure so that instability, such as the F3 second-fold degradation, remains visible rather than averaged away.
- The fixed-window result continues to be reported as a temporal stress test.
- Existing EXP-002 and EXP-003 conclusions were reached under the previous designation and are not retrospectively restated; V1 reporting uses the new primary.
- The final-test evaluation remains a single fixed chronological assessment and is unaffected.

**Affected Components:** evaluation protocol, model comparison, reporting, model card, uncertainty quantification

**Supersedes:** `DEC-036`, in respect of headline-evaluation designation only
**Superseded By:** none

---

## DEC-048

**Decision ID:** DEC-048
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
The three-day episode gap accepted under `DEC-030` yields 73 distinct onsets. A one-day gap yields 108, roughly 48% more events, which would materially help every model given the sparse support documented in `DEC-046`.

**Decision:**
Retain the three-day episode gap as the primary rule. Report the one-day gap as a pre-registered mandatory sensitivity for every V1 headline result. The seven-day gap remains a secondary sensitivity.

**Rationale:**
`DEC-030` selected the three-day rule after inspecting reporting patterns and before any model was fitted. Loosening it now, after model results are known and specifically because it would increase event counts, is selection on the outcome. The gain would be real but the resulting figures would be indefensible under the most obvious question a reviewer would ask.

Pre-registering the one-day variant as a mandatory sensitivity captures the same information honestly: if conclusions hold under both rules they are stronger, and if they do not, that instability is itself a finding worth reporting.

**Alternatives Considered:**
Switching the primary rule to the one-day gap, rejected on the outcome-selection grounds above despite the genuine statistical benefit.

**Consequences:**
- Every V1 headline result carries a one-day-gap sensitivity.
- Divergence between rules must be reported explicitly rather than resolved by preferring the more favourable rule.
- `DEC-030` remains in force and is not superseded.

**Affected Components:** outcome definition, sensitivity analysis, reporting, model card

**Supersedes:** none
**Superseded By:** none

---

## DEC-049

**Decision ID:** DEC-049
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
Section 5 D1 of `19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md` specified that calibrators be fitted on validation predictions only. That rule was written before `DEC-047` made pooled rolling-origin the headline evaluation, and before partition support was quantified at five onsets in the validation window.

Two problems follow. Fitting a calibrator on five onsets produces an extremely unstable mapping, and isotonic regression in particular would essentially memorise those events. Separately, fitting on the validation window while reporting calibrated performance under a rolling-origin headline is internally inconsistent, since the calibrator would have been fitted on data included in the pooled evaluation.

**Decision:**
Calibrators are fitted fold-wise within the pooled rolling-origin structure. In each fold the calibrator is fitted on that fold's training portion and applied to its held-out portion; metrics are then pooled across folds. Calibrator fitting partitions must always be disjoint from evaluation partitions.

This supersedes `DEC-036` in respect of the calibrator-fitting rule only, and revises section 5 D1 of doc 19 accordingly.

**Rationale:**
Fitting a calibrator on the same rows used to report its performance manufactures apparent improvement, which is the specific failure this change prevents. Fold-wise fitting keeps every calibrator strictly out of sample relative to the data it is scored on, matches the structure already established as headline, and gives the calibrator materially more events to fit against than a single five-onset window.

This tightens the leakage position rather than relaxing it, and adds an automated check, `CAL-02`, to enforce disjointness in every fold.

**Alternatives Considered:**
Retaining validation-only fitting, rejected as internally inconsistent with `DEC-047` and statistically unusable at five onsets. Fitting on the training partition and evaluating on validation, rejected because the model itself was fitted on that partition, so its in-sample probabilities are not representative of the held-out probabilities the calibrator must map.

**Consequences:**
- Doc 19 section 5 D1 is revised and now records fold-wise fitting.
- `CAL-02` enforces disjoint fitting and evaluation partitions in every fold.
- Calibrated results are reported pooled with per-fold values shown, per `DEC-047`.
- The final-test lock is unaffected.

**Affected Components:** calibration methodology, EXP-009 specification, leakage controls, evaluation reporting

**Supersedes:** `DEC-036`, in respect of the calibrator-fitting rule only
**Superseded By:** none

---

## DEC-050

**Decision ID:** DEC-050
**Date:** 2026-08-15
**Status:** ACCEPTED

**Context:**
The V1 delivery plan and the EXP-009 specification were initially written as two new files, `docs/V1_DELIVERY_PLAN.md` and `docs/specifications/EXP_009_CALIBRATION_SPECIFICATION.md`, and mirrored to Drive as non-numbered documents. This broke the established convention without a decision record.

The repository's `docs/` directory had only ever held `19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md`, `DECISION_LOG.md` and `PROJECT_STATE.md`. Every prior specification, Stages 0 to 8, EXP-002 and EXP-003, lived inside doc 19, which is why the state document describes it as a stage-gated revision. Drive held the numbered planning corpus plus the two control documents.

Two concrete faults resulted. Doc 19 section 5 D1 already specified EXP-009 with the same three calibration arms, so the new file created a second source of truth for one experiment. The new phase plan also allocated experiment identifiers EXP-010 through EXP-013, all four of which were already assigned: leave-one-player-out, GPS pilot, objective-data ablation and team transfer respectively.

**Decision:**
Specifications and delivery sequencing live in `19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md`. The EXP-009 specification is folded into section 5 D1 and the V1 delivery programme into a new section 5A. The two files created outside the convention are deleted from both the repository and Drive. V1 phases map onto existing experiment identifiers; no new identifiers are allocated.

**Rationale:**
One source of truth per subject is a standing property of this project, established for decisions in `DEC-009` and for state in `DEC-016`. A separate specification directory would have produced exactly the divergence those decisions exist to prevent, and the identifier collisions would have caused real confusion within a few sessions.

**Alternatives Considered:**
Adopting `docs/specifications/` as a deliberate new convention and moving the EXP-009 section out of doc 19, rejected because it would require restructuring a document that has governed nine approved stages and two completed experiments, for no benefit beyond file separation. Keeping both copies temporarily, rejected because duplicated specification text diverges quickly.

**Consequences:**
- `docs/V1_DELIVERY_PLAN.md` and `docs/specifications/` are removed from the repository; `V1_DELIVERY_PLAN.md` and `EXP_009_CALIBRATION_SPECIFICATION.md` are removed from the Drive folder.
- Doc 19 is now mirrored to Drive alongside the two control documents whenever it changes.
- Future specifications are written into doc 19, not as separate files.
- `DEC-046` is amended to reference section 5A rather than the deleted file.

**Affected Components:** documentation architecture, specification process, experiment identifier registry, state synchronisation

**Supersedes:** none
**Superseded By:** none

---

## DEC-051

**Decision ID:** DEC-051
**Date:** 2026-08-16
**Status:** ACCEPTED

**Context:**
State v48 recorded a single open decision: project-owner approval of the V1
delivery programme in section 5A of `19_ANALYSIS_AND_EXPERIMENT_EXECUTION_PLAN.md`
and the `EXP-009` calibration specification in section 5 D1 of the same document.
Both were drafted under the stage-gate model used since Stage 0, which requires an
approved specification before any implementation. The scope of `EXP-009` was
authorised by `DEC-044`; V1 scope and the mapping of phases onto existing
experiment identifiers were fixed by `DEC-046`; the headline evaluation protocol,
outcome sensitivity and calibrator-fitting rule were fixed by `DEC-047`, `DEC-048`
and `DEC-049` respectively. Implementation of phase V1-P1 was blocked pending this
approval.

**Decision:**
As project owner, approve both documents as drafted, with no amendments:
- the V1 delivery programme, section 5A;
- the `EXP-009` calibration specification, section 5 D1.

This closes the single open decision recorded in state v48 and authorises
implementation of phase V1-P1 (`EXP-009`) against development data only.

This approval does not authorise any access to the final-test partition, which
remains locked until phase V1-P5 and is then spent exactly once, per `DEC-046`;
nor does it authorise any V1-P2 (`EXP-007` Cox survival) or V1-P3 (`EXP-008`
boosted classification) work, each of which remains blocked pending its own
specification approval.

**Rationale:**
The specifications are complete and internally consistent with the decisions that
authorised their scope. The outcome-support limitation is a quantified, accepted
property of the dataset that `EXP-009` is designed around rather than expected to
resolve, so there is no reason to defer approval pending a cohort or horizon
change. Approving as drafted preserves the stage-gate discipline: the method
choice is settled before implementation, not implicitly during a run.

**Alternatives Considered:**
Amending the specification before approval, for example altering the calibration
arms or the metric set. Not selected; the drafts are complete and no amendment was
identified. Deferring approval until the five-onset support problem is addressed
through a cohort or horizon change. This was considered and rejected under
`DEC-044`, on the grounds that characterising the measured overestimation now is
cheap and reversible; nothing has changed to reopen it.

**Consequences:**
- Phase V1-P1 implementation is authorised against development data only, under the
  output contract of `DEC-029` and the integrity checks `CAL-01` to `CAL-08`.
- The gate-table rows "V1 delivery plan" and "EXP-009 specification" move from
  PENDING APPROVAL to APPROVED, citing `DEC-051`.
- The Open Decisions section is cleared; Immediate Next Actions reflect that
  V1-P1 implementation is now authorised.
- The final-test lock is unaffected. V1-P2 and V1-P3 remain unauthorised.
- Implementation is bound by the specification as written: fold-wise calibrator
  fitting on partitions disjoint from evaluation (`DEC-049`), pooled rolling-origin
  as the headline with estimable-fold counts and per-fold values (`DEC-047`), the
  one-day-gap sensitivity on every headline figure (`DEC-048`), the mandatory
  sparse-predictor audit of the 8.4%-coverage robust fatigue z-score (`DEC-043`),
  and the binding power limitation under which "no calibration method is
  distinguishable at this support" is a valid and expected result.
- Known ordering conflict, not resolved by this decision: section 5 "Model ladder
  advancement" places `EXP-007` and `EXP-008` only after operational-utility
  analysis, while section 5A places them at V1-P2 and V1-P3, ahead of the V1-P4
  operational-utility work. This must be settled by a superseding decision before
  V1-P2 begins. It does not affect V1-P1.

**Affected Components:** V1 delivery authorisation, EXP-009 implementation, phase
sequencing, final-test governance, project state

**Supersedes:** none
**Superseded By:** none

---

## DEC-052

**Decision ID:** DEC-052
**Date:** 2026-08-16
**Status:** ACCEPTED

**Context:**
`EXP-009` compared raw, Platt and isotonic calibration on the F3 candidate under
`DEC-044`, fitted fold-wise per `DEC-049`. Pooled rolling-origin support was 104
positive player-days across three estimable folds, with one zero-positive fold
excluded per `DEC-047`/`CAL-08`. The mandatory sparse-predictor audit under
`DEC-043` compared calibration by availability of the robust fatigue z-score.

**Decision:**
Select **raw** probabilities for the M1 candidate. No post-hoc calibrator is
adopted. The finding "no calibration method is distinguishable, and both tested
methods degrade probability quality at this support" is recorded as complete and
final for this phase.

Separately, authorise `EXP-016` as specified in doc 19 section 5 E3, to run
before phase V1-P2 begins. `EXP-016` tests whether F3's held-period advantage is
carried by the availability pattern of the robust fatigue z-score rather than its
value.

**This decision does not reopen `DEC-043`.** Whether F3 remains champion depends
on the `EXP-016` result and requires its own decision record.

**Rationale:**
Raw leads every pooled metric: Brier 0.006287 against 0.007246 (Platt) and
0.007402 (isotonic); log loss 0.041467 against 0.043001 and 0.052597. Paired
Brier intervals exclude zero against both calibrated arms under both
player-cluster and temporal week-block resampling, in the direction unfavourable
to calibration: raw-to-Platt cluster [0.000037, 0.002358], week-block
[0.000553, 0.001306]; raw-to-isotonic cluster [0.000061, 0.002854], week-block
[0.000606, 0.001778]. Platt materially improves the calibration slope, 2.222 to
1.200 against a target of 1.0, but this does not offset the measured Brier and
log loss cost. Average-precision differences straddle zero under player-cluster
resampling for both calibrated arms, and under week-block resampling for Platt.
One exception is recorded: isotonic shows a week-block average-precision
advantage over raw whose interval excludes zero, [0.005116, 0.046580]. It is not
corroborated under player-cluster resampling, [-0.038437, 0.060924], and the
standard applied throughout `EXP-009` requires a difference to hold under both
schemes before it is claimed. It is therefore recorded as an uncorroborated
single-scheme signal rather than a ranking advantage, and it does not offset
isotonic's measured Brier and log-loss cost, both of which exclude zero under
both schemes. Under `DEC-007`, calibration is a first-class metric and a slope
improvement bought at a measured, interval-confirmed probability-accuracy cost is
not a basis for adopting a calibrator.

The sparse-predictor audit found that the robust fatigue z-score's observed
subgroup (2,475 player-days, 61 positives, 2.46% prevalence) and absent subgroup
(14,340 player-days, 43 positives, 0.30% prevalence) diverge sharply on
discrimination: ROC-AUC 0.732 where observed against 0.908 where absent. A
predictor carrying physiological signal would be expected to discriminate at
least as well where it is present. This pattern, combined with the Stage 2
finding that wellness reporting itself rises from 62.9% to 97.3% around onset
days, is consistent with availability acting as a proxy for reporting activity
rather than the predictor's value carrying signal. `DEC-043` already placed this
predictor under explicit audit and flagged it as a V1-P4 removal candidate; this
audit result is judged serious enough to resolve before any further phase is
built on F3, rather than carried forward as a deferred item.

**Alternatives Considered:**
Adopting Platt for its slope correction despite the Brier cost, rejected because
`DEC-007` treats calibration as a first-class metric and the paired intervals
confirm a real, not merely point-estimate, degradation. Deferring the
sparse-predictor question to V1-P4 as originally scoped by `DEC-043`, rejected
because every V1 phase from V1-P2 onward is built on F3, and an availability
artefact discovered now would invalidate work built on top of it before the
programme reaches V1-P4.

**Consequences:**
- The M1 candidate reports raw probabilities. No calibrator is fitted, selected
  or applied downstream unless a future decision revisits this.
- `EXP-016` is authorised under the specification in doc 19 section 5 E3 and must
  complete, with its result reviewed, before phase V1-P2 begins.
- If `EXP-016` shows an arm without the predictor value, or with the indicator
  only, matching or beating F3 on calibrated probability quality and improving
  unseen-player generalisation, `DEC-043` is reopened and the champion is
  re-selected through a new decision before V1-P2.
- If F3 remains best on both axes, it stands and the availability entanglement is
  documented as a binding limitation on every downstream citation, alongside the
  five limitations already bound by `DEC-043`.
- The final-test lock is unaffected.

**Affected Components:** calibration selection, M1 candidate probability output,
sparse-predictor governance, champion selection path, final-test governance

**Supersedes:** none
**Superseded By:** none

---

## DEC-053

**Decision ID:** DEC-053
**Date:** 2026-08-16
**Status:** ACCEPTED

**Context:**
Doc 19 section 5 "Model ladder advancement" states that `EXP-007` and `EXP-008`
begin only after the baseline, calibration, operational-utility and required
robustness analyses are complete. Section 5A, added under `DEC-050` to sequence
V1 under `DEC-046`, places `EXP-007` at phase V1-P2 and `EXP-008` at V1-P3,
ahead of the V1-P4 operational-utility work (champion selection, explanation
stability, alert-budget simulation). The two sections conflict on ordering. This
was identified during `EXP-009` implementation and deliberately deferred rather
than resolved mid-phase, since it did not affect V1-P1.

**Decision:**
Section 5A governs V1 sequencing. The section 5 "Model ladder advancement" intro
is superseded to the extent it conflicts with section 5A's phase ordering:
`EXP-007` (V1-P2) and `EXP-008` (V1-P3) proceed ahead of the V1-P4
operational-utility work, not after it.

**Rationale:**
`DEC-046` defined V1 scope and its phase mapping was fixed with owner approval
under `DEC-051`. Section 5A is the more specific and more recently authorised
sequencing authority for V1; section 5's ordering predates the V1 definition and
was written for the general experiment backlog, not for the V1 programme
specifically. Resolving in favour of section 5A avoids relitigating the V1
phase order that was just approved, and avoids blocking `EXP-007` on
operational-utility work that section 5A explicitly places later.

**Alternatives Considered:**
Resolving in favour of section 5's ordering and renumbering V1 phases so
operational-utility work precedes survival and boosted-classification modelling,
rejected because it would reopen and delay the just-approved V1-P1 through V1-P4
sequence for a documentation inconsistency rather than a substantive concern,
and no reason has been identified why calibration, explanation stability or
alert-budget work must precede a survival-framing conclusion the charter
requires. Leaving both sections standing as an acknowledged inconsistency,
rejected because it invites exactly the ambiguity a stage-gated project cannot
carry into V1-P2.

**Consequences:**
- Doc 19 section 5 "Model ladder advancement" intro is revised to note that its
  general ordering is superseded for the V1 programme by section 5A, which
  remains the sequencing authority for `EXP-007`, `EXP-008` and the phases
  around them.
- No V1 phase is renumbered or delayed by this decision.
- Robustness experiments already registered in section 5 (`EXP-004`, `EXP-005`,
  `EXP-010`, `EXP-016`) continue to execute within the phase whose conclusion
  depends on them, per section 5A, rather than as a separate blocking stage.
- This decision does not itself authorise V1-P2; that remains gated on the
  `EXP-016` result under `DEC-052`.

**Affected Components:** doc 19 sequencing, V1 phase ordering, experiment
backlog documentation

**Supersedes:** doc 19 section 5 "Model ladder advancement" intro, in respect of
ordering relative to section 5A only
**Superseded By:** none

---

## DEC-054

**Decision ID:** DEC-054
**Date:** 2026-08-16
**Status:** ACCEPTED

**Context:**
`DEC-043` promoted F3 as the raw M1 development candidate on fixed
chronological window evidence, where F3 led F1 on average precision, 0.019432
against 0.016640. `DEC-047` subsequently made pooled rolling-origin the
headline evaluation protocol, superseding `DEC-036` in respect of headline
designation. The champion comparison was not re-run under the new protocol at
that time.

`EXP-016`, authorised by `DEC-052`, tested whether F3's advantage was carried
by the availability pattern of `fatigue_lag1_robust_z_prior` rather than its
value. It ran four arms under the frozen engine: A as F3, B with the value and
its `fatigue_robust_available` indicator both removed, C with the value
removed and the indicator retained, and D as F1. Arms A and D reproduced the
unseen-player figures cited in `DEC-043` exactly, confirming the
implementation.

**Decision:**
Reopen `DEC-043` in respect of candidate selection. F1 becomes the V1 champion
candidate, comprising nine predictors: `daily_load_log1p`,
`daily_load_sum_7d_log1p`, `daily_load_sum_28d_log1p`, `fatigue_lag1`,
`fatigue_mean_prior_7d`, `fatigue_mean_prior_28d`, `readiness_lag1`,
`readiness_mean_prior_7d`, `readiness_mean_prior_28d`.

F3 is not carried forward. Arm C is not carried forward. Raw probabilities are
retained per `DEC-052`; no calibrator is applied.

This selection is not made on statistical superiority. Every paired bootstrap
interval between arms includes zero under both resampling schemes, so no arm is
distinguishable from another at this support. It is made because the basis for
the prior selection is superseded, because F1 leads the axis most relevant to
the product, and because F1 carries no reporting-derived predictor.

**Rationale:**
Three findings support this.

First, arm C dominates arm A. On the fixed window C records Brier 0.003607,
average precision 0.0203 and ROC-AUC 0.8550 against A's 0.003613, 0.0194 and
0.8511. Pooled, C records 0.006287, 0.0877 and 0.8584 against A's 0.006287,
0.0791 and 0.8524. On unseen players C records 0.022500 average precision and
0.631222 ROC-AUC against A's 0.022308 and 0.630928. C matches or beats A
everywhere while removing a predictor. Dominance does not require statistical
significance to be actionable; retaining a strictly more complex model that is
nowhere better is not defensible.

Second, the continuous robust fatigue z-score contributes nothing measurable.
C, which retains only the availability indicator, performs as well as A, which
retains both. This is the direct answer to the question `EXP-016` was
authorised to settle, and it is consistent with the `EXP-009` audit finding
that discrimination was materially worse where the predictor was observed
(ROC-AUC 0.732) than where it was absent (0.908), and with the Stage 2 finding
that wellness reporting rises from 62.9% to 97.3% around onset days.
Availability, not physiology, was carrying the contribution.

Third, F1 leads on the headline and product-relevant axes. Under pooled
rolling-origin, `DEC-047`'s headline, F1 records average precision 0.0967
against F3's 0.0791. On support-aware unseen-player aggregation F1 records
0.023316 average precision and 0.642578 ROC-AUC against F3's 0.022308 and
0.630928, restating the reversal already bound as a limitation by `DEC-043`.
Unseen-player generalisation is the axis a squad-facing product depends on,
since the dashboard will encounter players absent from development data.

F1's nine predictors contain no availability indicator, no prior-relative
z-score and no wellness-count feature. The reporting-entanglement risk
documented from Stage 2 onward is therefore absent from the champion's
predictor contract rather than managed within it. F1 is also directly
interpretable to a practitioner as load, fatigue and readiness over three time
windows, which materially serves the V1-P6 requirement that a reviewer
understand the output without reading code.

Against this, F1 records slightly worse pooled ROC-AUC, 0.8355 against 0.8524,
and slightly worse pooled Brier, 0.006325 against 0.006287. Both differences
fall inside intervals that include zero.

**Alternatives Considered:**
Retaining F3 unchanged, rejected because arm C dominates it and because the
fixed-window evidence that justified its promotion is no longer the headline
protocol. Adopting arm C, rejected despite its dominance over A: it retains
`fatigue_robust_available`, a reporting-engagement proxy that is difficult to
explain in a practitioner interface and responsive to a player's app usage
rather than their physiology, and it does not match F1 on unseen-player
generalisation. Deferring the selection to V1-P4 as originally scoped, rejected
because V1-P2 and V1-P3 build challengers against the champion and would
otherwise be constructed on a candidate whose selection basis had lapsed.

**Consequences:**
- F1 is the champion candidate for V1-P2 onward. `EXP-007` and `EXP-008` are
  specified and evaluated against F1, not F3.
- The `DEC-043` limitation that F3 generalises worse than F1 to unseen players
  is resolved by this selection and no longer binds downstream citations.
- The remaining `DEC-043` limitations concerning outcome support, event
  concentration and rolling-origin instability continue to bind, since they are
  properties of the dataset rather than of the feature set.
- The sparse-predictor entanglement is recorded as a completed investigation
  with an evidence-backed outcome rather than an open limitation, since the
  predictor is no longer in the champion contract.
- No arm difference may be reported as statistically distinguishable. Every
  comparison in `EXP-016` had paired intervals including zero under both
  resampling schemes, and this must accompany any citation of this decision.
- The final-test lock is unaffected.

**Affected Components:** champion selection, predictor contract, EXP-007 and
EXP-008 specifications, V1-P4 scope, model card content

**Supersedes:** `DEC-043`, in respect of candidate selection only
**Superseded By:** none

---

## DEC-055

**Decision ID:** DEC-055
**Date:** 2026-08-16
**Status:** ACCEPTED

**Context:**
`EXP-007` compared an Andersen-Gill Cox proportional-hazards fit against the
F1 champion selected under `DEC-054`, converted to seven-day probabilities
through the Breslow baseline cumulative hazard and evaluated under the
protocol used in `EXP-003`, `EXP-009` and `EXP-016`.

The initial result was mixed. Cox recorded a lower pooled Brier score,
0.005929 against 0.006325, but a materially worse log loss, 0.130100 against
0.042000, and lower pooled average precision and ROC-AUC, 0.0755 and 0.7113
against 0.0967 and 0.8355. On the fixed validation window Cox recorded
ROC-AUC 0.6112 against F1's 0.8078. Against this, Cox appeared to lead
support-aware unseen-player generalisation by a wide margin, average
precision 0.104533 and ROC-AUC 0.817861 against F1's 0.023316 and 0.642578.

That pattern was internally inconsistent. Leave-one-player-out is the most
demanding evaluation in the protocol, yet Cox scored higher there than on
either the pooled rolling-origin or fixed-window views, while F1 showed the
expected ordering. A pre-registered diagnostic was run to test whether the
apparent advantage was an artefact of the time scale.

**Decision:**
Reject the survival framing for V1. `EXP-007` is closed with an
evidence-backed negative conclusion. F1 remains the champion under
`DEC-054`. No survival model is carried into V1-P3, V1-P4 or the product.

Record the following as a methodological constraint on all future survival
work, including `EXP-014` deferred to V2: a gap-time origin derived from a
player's own onset history is legitimate under temporal evaluation, because
time since last injury is genuinely known at prediction time, but breaches
the premise of leave-one-player-out evaluation, where nothing about the
held-out player may be assumed known.

**Rationale:**
Three strands support rejection, and no axis survives on which the survival
framing beats F1.

First, the diagnostic. The leave-one-player-out Cox arm was re-run with the
gap-time clock reset for every held-out player, treating each as entering at
post-burn-in study origin with no prior onset. Everything else was held
fixed: the same fitted models, folds, cohort and predictors. Unseen-player
average precision fell from 0.104533 to 0.019293 and ROC-AUC from 0.817861
to 0.576890, both below F1's 0.023316 and 0.642578. Cox's ordering across
the three evaluation views returned to the expected pattern, with
leave-one-player-out lowest at 0.576890 against fixed window 0.6112 and
pooled 0.7113. The collapse was specified in advance as the criterion
confirming leakage.

The mechanism is that the baseline hazard is highest at short gap times, so
indexing a held-out player by their own time since previous onset supplies
outcome information about that player. F1 has no equivalent access, making
the original comparison structurally unequal rather than merely optimistic.
The effect would be concentrated in the twelve estimable players, who are by
definition event-bearing and among whom five carry 74.6% of onsets.

Second, the pooled Brier advantage is an underprediction artefact rather
than better probability quality. Cox mean prediction is 0.002600 against an
observed rate of 0.006185, under by roughly 2.4 times, while F1 over-predicts
at 0.023000. At this prevalence, systematically predicting near zero lowers
squared error mechanically. Log loss, which penalises confident error,
favours F1 by a factor of three. Under `DEC-007`, calibration and probability
quality are first-class metrics and the Brier figure cannot be read in
isolation.

Third, the pre-registered gate was not met on its own terms. It required
paired intervals excluding zero under both resampling schemes. The paired
Brier difference excludes zero under temporal week-block resampling,
[-0.000738, -0.000100], but not under player-cluster resampling,
[-0.000728, 0.000028]. Average precision and ROC-AUC intervals include zero
under both schemes.

The specification's own gate records that explicit rejection with evidence
is a successful outcome. That condition is met.

**Alternatives Considered:**
Adopting the survival framing on the unseen-player result, rejected because
that result is the artefact. Holding the question open pending further
evidence, rejected because the diagnostic is decisive and leaving an
unresolved framing question would block V1-P3 and V1-P4 sequencing without
prospect of new information at this support. Re-specifying `EXP-007` with a
calendar or age-based time scale and re-running, rejected for V1: the pooled
and fixed-window views already favour F1 and the underprediction problem is a
property of the Breslow conversion at this prevalence rather than of the time
scale, so a re-specification would be unlikely to change the conclusion while
consuming schedule that `DEC-046` allocates to product and operationalisation
work. It is recorded as available to V2 alongside `EXP-014`.

**Consequences:**
- The survival framing is rejected for V1 with recorded evidence. `EXP-007`
  is closed.
- F1 remains the champion. V1-P3 proceeds with `EXP-008` boosted
  classification specified against F1.
- The retained `EXP-007` evidence is regenerated so that the reset-clock
  figures are the reported leave-one-player-out result and the own-clock
  figures are retained and labelled as the leakage diagnostic contrast.
- Integrity check `COX-09` is added, requiring that leave-one-player-out
  evaluation not use held-out player outcome history in the time coordinate
  and that both clock variants be reported.
- The gap-time constraint binds all future survival work, including
  `EXP-014` in V2.
- This is the second pre-registered audit in the V1 programme to overturn an
  apparently favourable result, after the `EXP-016` finding that the
  contribution of `fatigue_lag1_robust_z_prior` was carried by its
  availability pattern. Both are release evidence under V1-P8 and are
  reported as findings rather than as corrections.
- The `lifelines` dependency added for `EXP-007` constrains numpy to 1.26 and
  scipy to 1.17. This must be recorded before V1-P7 containerisation and is
  a removal candidate now that the survival framing is rejected.
- The final-test lock is unaffected.

**Affected Components:** V1-P2 outcome, model ladder scope, leakage controls,
EXP-007 retained evidence, EXP-014 constraints, V1-P7 dependency envelope,
V1-P8 release evidence

**Supersedes:** none
**Superseded By:** none

---

## DEC-056

**Decision ID:** DEC-056
**Date:** 2026-08-16
**Status:** ACCEPTED

**Context:**
`EXP-008` tested whether nonlinearity and interaction structure earn their
place at this sample size, using `HistGradientBoostingClassifier` over F1's
nine predictors under the frozen cohort, partitions and evaluation protocol.

During gate review a defect was identified in the paired bootstrap for
average precision. The headline statistic was computed on the 12,615-row
discrimination subset, with the zero-positive rolling fold excluded per
`CAL-08`, while the bootstrap resampled a different population, producing
medians whose sign contradicted the corresponding point-estimate
differences. In `EXP-008` the point difference was -0.010602 against a
week-block median of +0.026475; in `EXP-009` the isotonic-against-raw point
difference was -0.000349 against a week-block median of +0.019740. Brier
intervals were unaffected and agreed with their point estimates throughout.

**Decision:**
Reject boosted classification for V1. F1 remains the champion under
`DEC-054`. No boosted model is carried into V1-P4, V1-P5 or the product.

Correct the defective bootstrap across all affected modules, add integrity
check `BOOT-01` requiring that every paired bootstrap median agree in sign
with its point-estimate difference, and regenerate the retained evidence
for `EXP-009`, `EXP-016`, `EXP-007` and `EXP-008`.

Supersede the average-precision claim recorded in `DEC-052`. That decision
stated that isotonic showed a week-block average-precision advantage over
raw whose interval excluded zero. That interval was produced by the
defective estimator. The corrected figure is [-0.036918, 0.017755]. The
calibration selection made in `DEC-052` is unaffected, since it rested on
Brier and log loss, both of which were sound.

**Rationale:**
Boosted classification is worse than F1 on every axis except Brier.
Calibration slope is 2.537922 against 2.019474, further from the target of
1.0. Pooled ROC-AUC is 0.788733 against 0.835537. Unseen-player ROC-AUC is
0.554957 against 0.642578. Corrected pooled average precision is
0.086066 against F1's 0.096668, with paired intervals player-cluster
[-0.052406, 0.019850] and temporal week-block [-0.105518, 0.029223], both
including zero.

Brier favours boosted, 0.006143 against 0.006325, with paired intervals
excluding zero under both player-cluster resampling, [-0.000365,
-0.000046], and temporal week-block resampling, [-0.000274, -0.000096].
This is a genuine interval-confirmed edge and is not the underprediction
artefact identified in `EXP-007`, since boosted's mean prediction of
0.020385 is closer to the observed rate of 0.006185 than F1's 0.023012.
It is nonetheless a single-metric advantage set against a worse calibration
slope and worse discrimination on three of four views, and the gate
requires calibrated performance to improve, not one component of it.

The training-to-validation average-precision gap is roughly twentyfold,
0.256 against 0.013. This is the overfitting signature the specification
pre-registered as the most likely finding at 56 training onsets, and it is
recorded as observed rather than as a surprise.

The specification states that a negative result is expected and is reported
as-is, without searching for a configuration that reverses it. That
condition is met and no further configuration was tried beyond the
pre-registered grid.

**Alternatives Considered:**
Adopting boosted on the Brier result, rejected because a single-metric edge
accompanied by worse calibration and worse discrimination does not satisfy
a gate worded as calibrated performance improving, and because deploying a
model with a twentyfold train-validation gap at this support would not be
defensible in the model card. Widening the hyperparameter grid to seek a
configuration that improves discrimination, rejected because the grid was
pre-registered precisely to prevent that search and because `DEC-046`
allocates remaining schedule to product and operationalisation work.
Retaining boosted as a secondary reference alongside F1, rejected as it
would carry a dependency and a maintenance surface into V1-P6 for a model
that is not used.

**Consequences:**
- Boosted classification is rejected with recorded evidence. `EXP-008` is
  closed and V1-P3 is complete.
- The omission of boosted modelling from the V1 champion is an
  evidence-backed choice, not a gap, and is reported as such in V1-P8.
- `BOOT-01` binds all future paired-bootstrap reporting.
- Retained evidence for `EXP-009`, `EXP-016`, `EXP-007` and `EXP-008` is
  regenerated with the corrected estimator. Interval conclusions that
  changed are listed in the `EXP-008` report.
- The average-precision claim in `DEC-052` is superseded. Its calibration
  selection stands.
- No conclusion in `DEC-054` or `DEC-055` depends on an average-precision
  interval, so both stand unchanged. `DEC-054` rested on point estimates
  and explicitly recorded that no arm was statistically distinguishable;
  `DEC-055` rested on the leakage diagnostic, Brier intervals and log loss.
- V1-P4 is authorised to begin: champion selection, `EXP-018` explanation
  stability and `EXP-019` alert-budget simulation, against F1.
- The `lifelines` dependency is now unused following the `DEC-055`
  rejection and constrains numpy to 1.26 and scipy to 1.17. It is a removal
  candidate before V1-P7 containerisation.
- The final-test lock is unaffected.

**Affected Components:** V1-P3 outcome, uncertainty estimation across all
experiments, EXP-009 and EXP-052 average-precision claims, retained
evidence for four experiments, V1-P4 authorisation, V1-P7 dependency
envelope

**Supersedes:** `DEC-052`, in respect of the average-precision claim only
**Superseded By:** none

---

## DEC-057

**Decision ID:** DEC-057
**Date:** 2026-08-16
**Status:** ACCEPTED

**Context:**
`BOOT-01`, introduced under `DEC-056`, required every paired-bootstrap
median to agree in sign with its point-estimate difference. Regenerated
`EXP-009` evidence returned `BOOT-01` FAIL on the raw-against-isotonic
average-precision comparison, where the point difference is -0.000349 and
the player-cluster median is +0.000994. The corresponding interval is
[-0.048312, 0.010887] and includes zero. The raw-against-Platt comparison,
whose point difference is -0.003499, agrees in sign under both schemes.
`EXP-016`, `EXP-007` and `EXP-008` all record `BOOT-01` PASS at the same
scale using identical code.

Separately, `DEC-054` replaced F3 with F1 as the V1 champion after
`EXP-009` had been run. All `EXP-009` arms carry model identifier
`M1-F3-CAL`, so no calibrated F1 variant has been measured.

**Decision:**
Reformulate `BOOT-01` so that sign agreement is required only where the
paired interval excludes zero. Where the interval includes zero, no
direction is claimed and the comparison is recorded as not distinguishable.

Record the `EXP-009` F3 conclusion as unchanged: no calibration method is
distinguishable from raw at this support, and both tested methods degrade
Brier and log loss with intervals excluding zero. The corrected
average-precision intervals now include zero for every arm pair under both
resampling schemes, which strengthens rather than alters that conclusion.

Extend `EXP-009` with F1 raw, Platt and isotonic arms under the existing
experiment identifier, retaining the F3 arms as historical reference. No
new identifier is allocated.

**Rationale:**
Sign agreement is a property of claimed directions. A difference whose
interval spans zero has no claimed direction, and the sign of a quantity
indistinguishable from zero is arbitrary, so requiring agreement there
tests nothing and produces false failures. The failing comparison has a
point difference an order of magnitude smaller than the passing one, which
is the signature of a threshold problem rather than an estimator problem.
An empirical dead-zone tolerance was considered during implementation and
correctly rejected in favour of escalation; the interval condition achieves
the same protection from a stated principle rather than a tuned constant.

The F1 calibration extension is required for evidence traceability, not
because the outcome is in doubt. The binding constraint identified in
`DEC-052` is 104 pooled positive player-days fitted fold-wise, which is a
property of the cohort and is identical for F1. F1's miscalibration profile
closely resembles F3's, slope 2.019474 against 2.222064, with both
overpredicting by roughly 3.7 times. The expected outcome is therefore that
no calibrator is adopted. That expectation is not evidence, and `DEC-046`
requires every V1 claim to rest on a measured result.

Running this now is the cheapest available point. V1-P4 has not begun, no
product code exists and the final test is locked, so nothing downstream
requires rework whatever the outcome.

**Alternatives Considered:**
Widening the `BOOT-01` tolerance until `EXP-009` passes, rejected as tuning
a constant to a result. Removing `BOOT-01`, rejected because it caught a
real population-mismatch defect. Carrying the F3 calibration result forward
to F1 by argument, rejected because the model card would then cite an
experiment run on a model that is not the champion. Allocating a new
experiment identifier for the F1 calibration arms, rejected under `DEC-050`
and on the `EXP-003` precedent of multiple feature sets under one
identifier.

**Consequences:**
- `BOOT-01` binds in its reformulated wording across all modules and the
  affected findings tables are regenerated.
- The `EXP-009` F3 conclusion and the `DEC-052` calibration selection both
  stand.
- `EXP-009` gains F1 raw, Platt and isotonic arms. The champion's
  calibration claim becomes traceable to a measured result.
- Champion selection cannot be reopened by this work. Platt is strictly
  monotone and `CAL-04` verifies per-fold rank preservation, so a post-hoc
  calibrator cannot reorder candidates. `DEC-054` rested on raw point
  estimates, unseen-player generalisation and predictor-contract
  cleanliness, none of which a monotone transform affects.
- `EXP-008`'s rejection is unaffected in either direction. If calibration
  improves F1, the boosted Brier edge narrows and the rejection
  strengthens; if it degrades F1, no calibrator is adopted and the
  comparison stands as run.
- V1-P4 remains authorised and begins after the F1 calibration outcome is
  recorded.
- The final-test lock is unaffected.

**Affected Components:** BOOT-01 definition, EXP-009 scope and evidence,
champion calibration traceability, V1-P4 entry conditions

**Supersedes:** `DEC-056`, in respect of the `BOOT-01` wording only
**Superseded By:** none

---

## DEC-058

**Decision ID:** DEC-058
**Date:** 2026-08-16
**Status:** ACCEPTED

**Context:**
`DEC-057` extended `EXP-009` with F1 raw, Platt and isotonic arms so that
the champion's calibration claim would rest on a measured result rather
than on transfer from the superseded F3 candidate.

**Decision:**
Select raw probabilities for the F1 champion. No post-hoc calibrator is
adopted for V1. The finding that no calibration method is distinguishable
from raw at this support is now recorded against the champion itself.

**Rationale:**
Pooled rolling-origin results across the three F1 arms are: raw Brier
0.006325, log loss 0.042009, calibration intercept 2.007319, calibration
slope 2.019474, average precision 0.096668, ROC-AUC 0.835537; Platt Brier
0.007765, log loss 0.044835, intercept -1.482620, slope 1.044271, average
precision 0.095012, ROC-AUC 0.838287; isotonic Brier 0.007509, log loss
0.062091, intercept -4.435530, slope 0.128850, average precision 0.071853,
ROC-AUC 0.824284. Paired bootstrap differences against F1 raw are: raw to
Platt Brier, player-cluster median +0.001335 with 95% interval
[-0.000004, 0.003681] (includes zero), temporal week-block median +0.001431
with interval [0.000844, 0.002004] (excludes zero, Platt worse); raw to
isotonic Brier, player-cluster median +0.001179 with interval
[0.000320, 0.002238] (excludes zero, isotonic worse), temporal week-block
median +0.001189 with interval [0.000775, 0.001660] (excludes zero,
isotonic worse). Average-precision intervals for both comparisons include
zero under both resampling schemes.

Both Platt and isotonic pull the calibration slope toward 1 (from 2.019 to
1.044 and 0.129 respectively), but that correction is bought entirely at a
Brier-score cost: isotonic's degradation excludes zero under both
resampling schemes and Platt's excludes zero under temporal week-block
resampling, so neither meets the pre-registered gate for adoption.

Under `DEC-007` calibration is a first-class metric, and under the
pre-registered gate a difference is claimed only where the paired interval
excludes zero under both resampling schemes. No arm meets that bar on
probability quality. The binding constraint remains 104 pooled positive
player-days fitted fold-wise, which is a property of the cohort rather than
of any candidate, and the result reproduces the pattern already recorded
for F3 under `DEC-052`.

**Alternatives Considered:**
Adopting a calibrator on the strength of an improved calibration slope
alone, rejected on the same grounds as `DEC-052`: a slope correction bought
at a measured probability-accuracy cost is not an improvement in calibrated
performance. Deferring the calibration decision to V1-P5, rejected because
the final test is single-use and the probability transform must be frozen
before it is spent.

**Consequences:**
- The V1 champion reports raw F1 probabilities. This is now traceable to a
  measured result on the champion.
- The probability transform is frozen ahead of V1-P5 and may not be revised
  without a superseding decision.
- V1-P4 begins: champion selection gate, `EXP-018` explanation stability
  and `EXP-019` alert-budget simulation, against raw F1.
- Alert-budget behaviour is percentile-based and therefore rank-determined,
  so this decision does not alter capture at the frozen 1%, 2.5% and 5%
  review rates.
- The model card records that calibration was tested on the champion and
  that no method was adopted, with the support limitation stated.
- The final-test lock is unaffected.

**Affected Components:** champion probability output, V1-P4 entry, V1-P5
pre-registration, model card content

**Supersedes:** none
**Superseded By:** none

---

## DEC-059

**Decision ID:** DEC-059
**Date:** 2026-08-16
**Status:** ACCEPTED

**Context:**
`DEC-058` selected raw probabilities for the F1 champion and rejected Platt
scaling on the grounds that its calibration-slope correction was bought at
a Brier-score cost. That record also states the project's standing
inferential rule, that a difference is claimed only where the paired
interval excludes zero under both resampling schemes.

Those two statements are inconsistent. Platt's Brier degradation against F1
raw is [-0.000004, 0.003681] under player-cluster resampling, which
includes zero, and [0.000844, 0.002004] under temporal week-block
resampling, which excludes it. Under the stated rule the cost is not
established, so it cannot carry the rejection. The position differs from
F3, where the equivalent intervals were [0.000037, 0.002358] and
[0.000553, 0.001306] and the cost cleared both schemes, which is why
`DEC-052` was sound on the same reasoning.

Isotonic is unaffected. Its degradation is [0.000320, 0.002238] and
[0.000775, 0.001660], excluding zero under both schemes.

**Decision:**
The selection made in `DEC-058` stands. The F1 champion reports raw
probabilities and the transform remains frozen ahead of V1-P5.

Supersede the rationale of `DEC-058` and record the following grounds in
its place.

Platt does not correct F1's calibration. It exchanges one calibration
defect for another. It improves the slope from 2.019474 to 1.044271 while
worsening calibration in the large: mean predicted risk moves from 0.023012
to 0.027420 against an observed rate of 0.006185, so overprediction rises
from roughly 3.7 times to roughly 4.4 times, and the intercept moves from
2.007319 to -1.482620. Log loss degrades from 0.042009 to 0.044835.

Record as a standing rule that the two-scheme requirement applies
symmetrically. A cost may not be treated as established on weaker evidence
than a benefit.

**Rationale:**
For a decision-support product that displays a risk figure, error in the
level of predicted risk is at least as consequential as error in its
spread. `DEC-007` requires that a stated 20% risk mean approximately 20%,
which is a statement about level. A transform that sharpens the slope while
moving the average further from the observed rate does not serve that
requirement, and this holds independently of any bootstrap interval.

Log loss is not bootstrapped anywhere in this experiment suite, which
carries intervals only for Brier score and average precision. Its
degradation is therefore an unqualified point difference rather than an
unestablished one, and it points the same way as the calibration-in-the-
large result.

The symmetry rule matters beyond this decision. Applied asymmetrically, the
two-scheme requirement would make adoption hard and rejection easy, which
would bias the programme toward whatever was selected first. Stating it
explicitly removes that asymmetry from future gates.

**Alternatives Considered:**
Adopting Platt on the grounds that its Brier cost is not established,
rejected because the calibration-in-the-large deterioration and the log
loss degradation both point against it and neither depends on a contested
interval. Leaving `DEC-058` standing unamended, rejected because the record
would state an inferential rule and then not apply it symmetrically within
the same document, in a programme whose headline evidence is methodological
rigour and whose model card will be read against its own decision log.
Re-running `EXP-009`, rejected because no new measurement is required; the
existing evidence supports the corrected reasoning as it stands.

**Consequences:**
- The champion's probability transform is unchanged. No experiment,
  evidence table, figure or report requires regeneration.
- The rationale of `DEC-058` is superseded. Its decision, alternatives and
  consequences stand.
- The two-scheme requirement applies symmetrically to costs and benefits in
  every future gate.
- The absence of uncertainty intervals for log loss, calibration slope and
  calibration intercept is recorded as a known limitation of the current
  uncertainty suite. It is not remediated now, since Brier and average
  precision carry intervals and the V1 conclusions do not rest on the
  unbootstrapped metrics, but it must be stated in the model card.
- V1-P4 remains authorised and unaffected.
- The final-test lock is unaffected.

**Affected Components:** DEC-058 rationale, inferential standard for all
future gates, uncertainty-suite limitations, model card content

**Supersedes:** `DEC-058`, in respect of rationale only
**Superseded By:** none

---

## DEC-060

**Decision ID:** DEC-060
**Date:** 2026-08-17

**Status:** ACCEPTED

**Context:**
Phase V1-P4 covers champion selection, explanation stability (`EXP-018`) and
alert-budget simulation (`EXP-019`). Champion selection has been settled
across three prior decisions: `DEC-054` selected F1 over F3 and arm C,
`DEC-058` selected raw probabilities with no post-hoc calibrator, and
`DEC-059` corrected the grounds for that selection. `EXP-018` has no
specification in this document, carrying only two passing references.
`EXP-019` carries a brief specification in section 5 D2 whose review rates
of 5%, 10% and 20% differ from the 1%, 2.5% and 5% budgets frozen under
`DEC-036` and used in every experiment since `EXP-002`.

**Decision:**
Close the champion selection gate. The V1 champion is F1 reporting raw
probabilities: nine predictors comprising `daily_load_log1p`,
`daily_load_sum_7d_log1p`, `daily_load_sum_28d_log1p`, `fatigue_lag1`,
`fatigue_mean_prior_7d`, `fatigue_mean_prior_28d`, `readiness_lag1`,
`readiness_mean_prior_7d` and `readiness_mean_prior_28d`. No further
candidate is evaluated in V1.

Specify and authorise `EXP-018` and `EXP-019` as set out in doc 19 sections
5 D2 and 5 D3, development data only.

Adopt top-N-per-team-day as the product-facing operating point for the V1
dashboard. The frozen 1%, 2.5% and 5% review rates remain the comparison
basis for cross-experiment evidence under `DEC-036` and are unaffected;
both are reported alongside each other.

**Rationale:**
The champion question is settled and re-opening it would relitigate three
decisions without new evidence. Recording the gate closure explicitly
prevents the selection resting on inference across three separate records.

Top-N is the form in which a practitioner actually works. A coach reviews a
fixed number of players before training, not a percentage of player-days,
and a percentage is not interpretable at the point of use. It is computed
within team-day rather than globally because the cohort contains two squads
and a global ranking could place every alert in one of them, which would be
operationally useless to the other.

Retaining the percentile budgets as the comparison basis preserves
comparability with `EXP-002`, `EXP-003`, `EXP-009`, `EXP-016`, `EXP-007` and
`EXP-008`, all of which report capture at 1%, 2.5% and 5%. Superseding
`DEC-036` would invalidate that comparability for no gain, since both views
can be reported from the same predictions.

Explanation stability is inexpensive for this champion because F1 is a
nine-predictor linear model whose attribution is its standardised
coefficients. Had the boosted candidate been adopted under `EXP-008`, this
phase would have required a full attribution framework. The rejection
recorded in `DEC-056` reduced the cost of this phase as a side effect.

**Alternatives Considered:**
Making the percentile budgets product-facing, rejected because a review rate
is not actionable at the point of use and the dashboard must be operable
without reading code, per the `DEC-046` definition of done. Superseding
`DEC-036` to replace the frozen budgets with top-N, rejected because it
would break comparability across six completed experiments to no purpose.
Computing top-N across the full cohort rather than within team-day, rejected
because it could concentrate every alert in one squad.

**Consequences:**
- The champion is frozen for V1. Any change requires a superseding decision
  before V1-P5.
- `EXP-018` and `EXP-019` are authorised against raw F1, development data
  only.
- The dashboard presents top-N per team-day as its primary operating point,
  with the false-alert burden displayed alongside every operating point
  offered.
- Percentile capture continues to be reported in all experiment evidence.
- Any predictor whose coefficient sign is unstable across estimable folds
  may not be displayed as a driver in the dashboard. The `EXP-018` result
  determines which predictors those are.
- No alert threshold is a medical threshold, a clearance decision or
  participation advice, in any artefact or interface.
- The final-test lock is unaffected.

**Affected Components:** champion freeze, V1-P4 scope, EXP-018 and EXP-019
specifications, dashboard operating point, model card content

**Supersedes:** none
**Superseded By:** none

---

## Open Decisions Awaiting Resolution

Recorded for visibility. Each becomes a numbered decision when resolved. None has been silently chosen.

Phase V1-P4 (champion selection, `EXP-018` explanation stability, `EXP-019` alert-budget simulation) is authorised and begins against raw F1 probabilities, per `DEC-054` and `DEC-058`. Final-test performance access remains prohibited until the V1 pre-registration checklist is complete at phase V1-P5.

Resolved in this revision: the F1 champion calibration question (`DEC-058`, raw selected for V1; no post-hoc calibrator adopted); the `BOOT-01` false-failure question on the raw-versus-isotonic average-precision comparison (`DEC-057`, reformulated to require sign agreement only where the paired interval excludes zero; the prior FAIL was a specification defect, not an estimator defect); the `EXP-008` complexity-verdict question (`DEC-056`, boosted classification rejected for V1; F1 remains champion); the `DEC-052` average-precision claim (superseded by the corrected estimator; the calibration selection itself stands).

Resolved previously: the `EXP-007` survival-framing question (`DEC-055`, rejected for V1 on evidence-backed diagnostic grounds; F1 remains champion). Noted, no action required until V1-P7: the `lifelines` dependency added for `EXP-007` constrains numpy to 1.26 and scipy to 1.17, and is a removal candidate now that survival framing is rejected. The `EXP-009` calibration method question (`DEC-052`, raw selected); the doc 19 section 5 / section 5A ordering conflict (`DEC-053`, section 5A governs); the `EXP-016` champion question (`DEC-054`, F1 becomes the V1 champion candidate, superseding `DEC-043` in respect of candidate selection only).

### Resolved

| Item | Resolved by |
|------|-------------|
| OD-01 Package name | DEC-010 |
| OD-02 Dependency locking | DEC-011 |
| OD-03 Git baseline | DEC-015, with hosting deferred to OD-08 |
| OD-04 Repository structure | DEC-012 |
| OD-05 Configuration strategy | DEC-013 |
| OD-06 Vertical-slice execution locus | DEC-014 |
| OD-08 Remote hosting and branch policy | DEC-017 |
| OD-07 Source-archive provenance | Transfer verification and schema audit, 2026-08-13 |
