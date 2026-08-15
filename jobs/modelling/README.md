# Modelling Jobs

Canonical modelling jobs generate retained artifacts. Matching notebooks import the same shared
functions but do not write persistent outputs.

## EXP-002 M0

```powershell
poetry run python jobs/modelling/run_exp_002_m0_baselines.py
```

This job evaluates training and validation data only. The locked final-test partition is recorded
for support but no final-test predictions or performance metrics are created.

## EXP-003 M1-F1

```powershell
poetry run python jobs/modelling/run_exp_003_m1_f1.py
```

This job searches only the frozen F1 regularisation grid, persists validation-only predictions and
a development candidate pipeline, and does not fit F2/F3, select post-hoc calibration or evaluate
the final test.

## EXP-003 M1 Feature Ladder

```powershell
poetry run python jobs/modelling/run_exp_003_m1_feature_ladder.py
```

This job compares the cumulative F1/F2/F3 contracts under unchanged model and validation settings.
It persists consolidated and per-feature-set development evidence without selecting calibration or
evaluating the locked final test.
