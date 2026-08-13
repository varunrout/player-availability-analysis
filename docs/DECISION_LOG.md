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

## Open Decisions Awaiting Resolution

Recorded for visibility. Each becomes a numbered decision when resolved. None has been silently chosen.

**OD-07 - Source-archive provenance.** No SoccerMon archive was located in the searchable Drive account during the baseline session. The location, licence record and SHA-256 checksum of the subjective archive are unverified. Blocks all ingestion work.

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
