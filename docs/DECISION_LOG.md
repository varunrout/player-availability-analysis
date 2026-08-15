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
**Superseded By:** none

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

## Open Decisions Awaiting Resolution

Recorded for visibility. Each becomes a numbered decision when resolved. None has been silently chosen.

M0 implementation and development-only validation are authorised under `DEC-039`. M1 implementation remains pending project-owner review of the M0 results. Final-test performance access remains prohibited.

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
