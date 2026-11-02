# Experiment 8 — Testing Strategy

This document summarizes the automated test suite added for the `mlops-iris-classifier`
MLOps project (Experiment 8: Unit Testing of Data Processing Functions, Training
Pipelines, and Model Outputs).

The suite is run with **pytest** (CI-compatible) and produces a JUnit XML report
(`test-results.xml`) plus a coverage report, enabling automated quality gating in CI/CD
(Experiment 9).

## Tool stack

| Tool | Purpose |
|------|---------|
| pytest | Test runner / CI-compatible test execution |
| pytest-cov | Code coverage measurement |
| scikit-learn, pandas, numpy | ML/data libraries under test |

Run the full suite:

```bash
pytest --cov=src --cov-report=term-missing --junitxml=test-results.xml
```

## Test files by layer

ML correctness is verified at three layers: **data**, **pipeline**, and **model quality**.

| Test file | Layer | What it verifies |
|-----------|-------|------------------|
| `tests/test_preprocess.py` | Data | `src/pipeline/preprocess.py` — duplicate removal, median imputation of missing numeric values, dropping rows with missing target, empty DataFrame handling. |
| `tests/test_features.py` | Data | `src/pipeline/features.py` — `sepal_area`, `petal_area`, `sepal_to_petal_length_ratio` computation; `petal_length_bin` categories; zero petal length yields NaN ratio without crashing. |
| `tests/test_validate.py` | Data | `src/pipeline/validate.py` — clean data passes; missing column, invalid species, and out-of-range value all raise `DataValidationError` (negative testing of failure paths). |
| `tests/test_training_pipeline.py` | Pipeline | End-to-end training smoke test on a small synthetic dataset — model trains without error, `.predict()` output shape, `predict_proba` rows sum to 1. |
| `tests/test_model_quality.py` | Model quality | Quality gate on the real Experiment 4 feature set — predictions fall within the known label set; test accuracy exceeds `MIN_ACCEPTABLE_ACCURACY = 0.90`. |

## Coverage

Measured with `pytest --cov=src`:

| Module | Coverage |
|--------|----------|
| `src/pipeline/preprocess.py` | 83% |
| `src/pipeline/features.py` | 75% |
| `src/pipeline/validate.py` | 71% |
| **Overall (`src/`)** | **18%** |

The unit tests exercise the majority of branches in the data-processing modules,
including the adversarial/edge cases (empty DataFrame, missing values, division by
zero, missing/invalid/out-of-range data). Overall source-code coverage is ≈18% because
coverage is measured across the whole `src/` tree, much of which (CLI entry points,
Experiment 5–7 tuning scripts, DVC/Feast glue) is not exercised by this suite.

## CI usage

- `test-results.xml` is generated in JUnit XML format and contains `<testsuite>` and
  `<testcase>` elements for every test, which CI tools parse to display pass/fail
  summaries (Experiment 9).
- `tests/test_model_quality.py` acts as a model quality gate: a code or data change that
  silently degrades accuracy below `0.90` fails the suite and should block a merge.

> Verification: all 16 tests pass in ≈4 s. To confirm the quality gate catches
> regressions, temporarily lower `MIN_ACCEPTABLE_ACCURACY` to `0.99` —
> `pytest tests/test_model_quality.py` should FAIL — then restore it to `0.90`.