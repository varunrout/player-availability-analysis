# V1-P6 API service (DEC-064). Internal ingress only; reads the batch-inference
# serving artefact from Cloud Storage and the committed evidence tables below.
# No credential is baked into this image; Cloud Run supplies ADC at runtime.
FROM python:3.12-slim AS base

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install "poetry>=2.0,<3.0"

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root

COPY src ./src
COPY configs ./configs
# Model-health reference tables only: the specific committed evidence the
# governing decisions rest on, not the full outputs tree. Paths preserved so
# repo_root()/outputs/modelling/... resolves the same way as in local dev.
COPY outputs/modelling/exp_009_calibration/tables/arm_pooled_metrics.csv outputs/modelling/exp_009_calibration/tables/arm_pooled_metrics.csv
COPY outputs/modelling/exp_019_alert_budget/tables/alert_budget_results.csv outputs/modelling/exp_019_alert_budget/tables/alert_budget_results.csv
COPY outputs/modelling/v1_p5_final_test/tables/final_test_metrics.csv outputs/modelling/v1_p5_final_test/tables/final_test_metrics.csv
COPY outputs/modelling/v1_p5_final_test/tables/claims.csv outputs/modelling/v1_p5_final_test/tables/claims.csv

RUN pip install --no-deps -e .

EXPOSE 8080
CMD ["uvicorn", "player_availability.api.app:app", "--host", "0.0.0.0", "--port", "8080"]
