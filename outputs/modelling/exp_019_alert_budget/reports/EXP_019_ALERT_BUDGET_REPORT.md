# EXP-019 - Alert-Budget Simulation Report

## Automated Status

Development run: **PASS**. Project-owner operating-point review required.

Raw F1 champion probabilities (`DEC-058`, `DEC-059`) are translated into review operating points on pooled rolling-origin predictions: top 1, 3 and 5 players per team-day as the product-facing primary view (`DEC-060`), and the frozen 1%, 2.5% and 5% review rates as the `DEC-036` comparison basis, reported side by side from the same prediction set. A 5%/10%/20% capacity sensitivity is retained but is never a headline. No final-test prediction or performance is created.

Tie-break rule: predicted_probability descending, then player_id ascending.

## Operating Points

| Type | Value | Alerts | Alerts/100 days | Precision | Represented onsets | Captured | Recall | False alerts/captured |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| capacity_sensitivity | 0.05 | 841 | 5.00 | 0.0666 | 18 | 13 | 0.7222 | 60.3846 |
| capacity_sensitivity | 0.1 | 1682 | 10.00 | 0.0380 | 18 | 14 | 0.7778 | 115.5714 |
| capacity_sensitivity | 0.2 | 3363 | 20.00 | 0.0241 | 18 | 15 | 0.8333 | 218.8000 |
| percentile | 0.01 | 169 | 1.01 | 0.0473 | 18 | 2 | 0.1111 | 80.5000 |
| percentile | 0.025 | 421 | 2.50 | 0.0903 | 18 | 11 | 0.6111 | 34.8182 |
| percentile | 0.05 | 841 | 5.00 | 0.0666 | 18 | 13 | 0.7222 | 60.3846 |
| top_n_per_team_day | 1 | 674 | 4.01 | 0.0504 | 18 | 9 | 0.5000 | 71.1111 |
| top_n_per_team_day | 3 | 2022 | 12.02 | 0.0307 | 18 | 13 | 0.7222 | 150.7692 |
| top_n_per_team_day | 5 | 3370 | 20.04 | 0.0205 | 18 | 13 | 0.7222 | 253.9231 |

## Findings

| ID | Status | Domain | Evidence |
|---|---|---|---|
| ALERT-01 | PASS | final_test_isolation | zero final-test predictions or performance metrics produced |
| ALERT-02 | PASS | top_n_scope | top-N selection never exceeds N players within any team-day group |
| ALERT-03 | PASS | false_alert_burden | every operating point reports false alerts per captured onset inline |
| ALERT-04 | PASS | event_count_reporting | every operating point carries represented-onset and player-day counts |
| ALERT-05 | PASS | one_day_gap_sensitivity | one-day-gap sensitivity present alongside the three-day headline |
| ALERT-06 | PASS | shared_prediction_set | percentile and top-N views are generated from the same pooled prediction set |

## Interpretation Boundary

The selected operating point is a review-prioritisation policy. It is never a medical threshold, a clearance decision or participation advice. If no operating point captures onsets at a burden a practitioner would accept, that is a valid and reportable finding.

## Gate

The project owner records which operating points the dashboard will offer, each with its false-alert burden stated.
