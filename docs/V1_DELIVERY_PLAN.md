# Player Availability Analysis - V1 Delivery Plan

Governing decision: `DEC-046`. Evaluation protocol: `DEC-047`. Outcome sensitivity: `DEC-048`.

This plan covers the route from the current EXP-009 gate to a shippable V1. It is the operational companion to `PROJECT_STATE.md`, which remains the record of current truth.

---

## What V1 is

A complete subjective-data player-availability decision-support system, released as an operable product with an honest account of what it can and cannot support.

**The headline evidence is methodological, not performance.** No V1 artefact presents discrimination as the primary result.

## Why the goal is framed this way

Effective outcome support is the binding constraint on everything downstream.

| Measure | Value |
|---|---|
| Represented onsets, frozen cohort | 66 |
| Onsets in train / validation / final test | 56 / 5 / 5 |
| Share of onsets from top five players | 74.6% |
| Players with any event, development | 12 of 50 |
| Onset decline, 2020 to 2021 | roughly tenfold, at flat player-days |

The 2021 collapse tracks reporting engagement rather than injury incidence, consistent with the Stage 2 finding that wellness reporting rises from 62.9% on ordinary days to 97.3% on onset days. The dataset supports a well-built system and an honest uncertainty account. It does not support a claim that injuries are predicted.

---

## Definition of done

V1 ships when every item below is true.

**Methodology**
- [ ] Calibration characterised for the champion, with reliability curve, slope, intercept and expected calibration error.
- [ ] Pooled rolling-origin reported as the primary evaluation, with estimable-fold counts stated and per-fold results shown.
- [ ] Unseen-player generalisation reported with support-aware aggregation.
- [ ] One-day-gap sensitivity reported for every headline result.
- [ ] Leakage suite passing, including future-append invariance.
- [ ] Survival framing either adopted or explicitly rejected with evidence.
- [ ] Complexity ladder conclusion recorded for M2.

**Product**
- [ ] Batch inference writing to `paa_product`.
- [ ] Dashboard on Cloud Run: squad overview, player detail, data quality, model health.
- [ ] Every risk figure displayed with uncertainty and data-completeness context.
- [ ] No prohibited language anywhere in the interface.

**Engineering**
- [ ] Containerised and reproducible from a clean clone.
- [ ] CI running lockfile, lint, types, tests and leakage checks.
- [ ] Cost recorded and within envelope.

**Evidence**
- [ ] Model card leading with limitations.
- [ ] Final test spent exactly once against pre-registered claims.
- [ ] README, architecture diagram, case study, interview narrative.

---

## Phases

Each phase carries an owner approval gate on its specification before implementation, and on its results before the next phase begins. This mirrors the Stage 0 to Stage 8 model already in use.

### V1-P1 Calibration (`EXP-009`)
Raw against Platt against isotonic on F3, development data only.

*Exit:* calibration behaviour characterised; sensitivity to the 8.4%-coverage robust fatigue predictor audited per `DEC-043`; "no method distinguishable at this support" accepted in advance as a valid outcome.

### V1-P2 Survival modelling (`EXP-010`)
Cox proportional hazards on the frozen predictor contract, with proportional-hazards diagnostics.

*Exit:* an explicit, evidence-backed conclusion on whether time-to-event framing adds practitioner value over the binary-horizon framing. Rejection with evidence is a successful outcome.

### V1-P3 Complexity test (`EXP-011`)
Gradient boosting under the same contract and evaluation.

*Exit:* a recorded verdict on whether nonlinearity earns its place at this sample size. A negative result is expected and is reportable as-is.

### V1-P4 Champion selection and explainability (`EXP-012`)
Select the champion across all candidates on calibration, pooled rolling-origin, unseen-player evidence and alert burden. Produce explanations and stability evidence.

*Exit:* champion recorded with rationale; explanation stability measured; no final-test access.

### V1-P5 Pre-registration and final test (`EXP-013`)
Freeze claims, metrics and thresholds in writing. Then spend the final test once.

*Exit:* final-test evaluation executed once against pre-registered claims. Results reported whether favourable or not.

**This is irreversible.** No tuning, feature change or model change may follow. Any second access requires a new superseding decision.

### V1-P6 Product
Batch inference into `paa_product`, then the Cloud Run dashboard.

*Exit:* a reviewer can operate the product and reach a correct understanding of both output and its limits without reading code.

### V1-P7 Operationalisation
Containers, CI, monitoring hooks, cost recording.

*Exit:* reproducible from a clean clone; CI enforcing the gates currently run by hand.

### V1-P8 Release evidence
Model card, README, architecture diagram, case study, interview narrative.

*Exit:* every external claim traceable to a measured result.

---

## Sequencing rules

1. Specification approved before implementation, results approved before the next phase. No exceptions.
2. Final test is touched only in V1-P5, once.
3. No GPS or objective processing during V1.
4. Any material design change requires a decision record before the work, not after.
5. Phases V1-P1 through V1-P3 may be reordered if evidence justifies it; V1-P4 onwards is strictly ordered.

## Scope control

If time pressure rises, cut in this order:

1. M2 complexity test, recording the omission.
2. The API layer, keeping the dashboard.
3. Monitoring depth, keeping data-quality surfaces.

Never cut: leak-safe validation, calibration, the limitations account, the model card, the dashboard, or single-use final-test discipline.

## Risks

| Risk | Mitigation |
|---|---|
| Sparse events make every comparison inconclusive | Pooled rolling-origin under `DEC-047`; "not distinguishable" pre-accepted as a valid finding |
| Event concentration in five players | Support-aware unseen-player aggregation; concentration restated wherever performance is cited |
| Reporting engagement decays over time | Treated as a documented dataset property; reporting-derived predictors remain under audit per `DEC-031` |
| Sparse robust-fatigue predictor drives apparent F3 gain | Explicit audit in V1-P1; removal candidate |
| Temptation to revisit the final test | Single-use rule; second access requires a superseding decision |
| Overclaiming in portfolio material | Every external claim traced to a measured result before release |
