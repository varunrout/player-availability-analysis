"""Training-only preprocessing for interpretable baseline models."""

from __future__ import annotations

from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

F1_FEATURES = (
    "daily_load_log1p",
    "daily_load_sum_7d_log1p",
    "daily_load_sum_28d_log1p",
    "fatigue_lag1",
    "readiness_lag1",
    "fatigue_mean_prior_7d",
    "fatigue_mean_prior_28d",
    "readiness_mean_prior_7d",
    "readiness_mean_prior_28d",
)


def build_f1_pipeline(*, regularisation_c: float, max_iterations: int) -> Pipeline:
    """Build the frozen F1 imputation, scaling and logistic pipeline."""
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    C=regularisation_c,
                    l1_ratio=0,
                    solver="lbfgs",
                    max_iter=max_iterations,
                    class_weight=None,
                ),
            ),
        ]
    )


def transformed_feature_names(pipeline: Pipeline) -> list[str]:
    """Return fitted imputer output names in coefficient order."""
    imputer = pipeline.named_steps["imputer"]
    return [str(value) for value in imputer.get_feature_names_out(F1_FEATURES)]
