# Experiment 5 — Feature Store Analysis

This document summarizes the observed benefits of introducing a Feast Feature Store
into the `mlops-iris-classifier` MLOps workflow (Experiment 5).

## Overview

A feature repository was created under `practical5_feast/iris_feature_repo/feature_repo`
using `feast init -t local`. The feature-engineered output of Experiment 4
(`data/processed/iris_features.csv`) was converted into a Feast-ready Parquet source
(`data/iris_features.parquet`) carrying an entity key (`sample_id`) and an event
timestamp (`event_timestamp`) / created timestamp (`created_timestamp`).

Two feature views were registered:

- `iris_measurements` — raw Iris measurements (`sepal length (cm)`, `sepal width (cm)`,
  `petal length (cm)`, `petal width (cm)`), TTL 365 days, online serving enabled.
- `iris_engineered_features` — engineered features (`sepal_area`, `petal_area`,
  `sepal_to_petal_length_ratio`, `petal_length_bin`), TTL 365 days, online serving enabled.

Both feature views share a single `FileSource` (`iris_features_source`) and a single
`Entity` (`sample_id`), and are grouped into one `FeatureService`
(`iris_feature_service`). The transformation logic for every feature is declared exactly
once in `features.py`, which acts as the single source of truth.

## Benefit 1 — Elimination of Training-Serving Skew

The same registered `iris_engineered_features` definitions were served along two distinct
paths:

- **Online (serving) path** — `get_online_features.py` retrieved `sepal_area`, `petal_area`,
  `sepal_to_petal_length_ratio`, and `petal_length_bin` from the SQLite online store with
  millisecond-scale point lookups.
- **Offline (training) path** — `get_historical_features.py` retrieved the *same* feature
  names via `get_historical_features()`, which performs a point-in-time-correct as-of join.

Because both paths are populated from the same feature definitions and the same ingestion
pipeline, the values served online are guaranteed to be computed identically to those used
in training. The classic failure mode in which the offline training transform and the
online inference transform drift apart over time (different rounding, units, or
missing-value handling) is structurally prevented — the inconsistency cannot arise if
there is only one definition.

## Benefit 2 — Feature Reusability

`reuse_features_for_clustering.py` demonstrates a structurally different consumer — an
unsupervised clustering task — retrieving the very same registered features through the
`iris_feature_service` Feature Service:

```
Features retrieved using Feature Service:
{'sample_id': [1], 'petal width (cm)': [0.2000...], 'petal length (cm)': [1.3999...],
 'sepal length (cm)': [4.9000...], 'sepal width (cm)': [3.0], 'petal_length_bin': ['short'],
 'sepal_area': [14.6999...], 'petal_area': [0.2800...], 'sepal_to_petal_length_ratio': [3.5]}
```

Zero re-implementation was required. The clustering task did not re-derive `sepal_area` or
`petal_area`; it requested them by name from the feature store. This is the organizational
payoff of the architecture: any team building a different model consumes the exact same,
validated feature definitions, improving consistency and reducing duplicated engineering
effort.

## Benefit 3 — Centralized Governance

A single `features.py` is the source of truth for every consuming model. Entity, data
source, feature schema, dtype, and TTL are declared once and registered with
`feast apply`, which writes them to a versioned local registry (`data/registry.db`).
Governance therefore happens in one auditable place rather than being distributed across
independent training scripts.

## Point-in-Time Correctness

`get_historical_features.py` demonstrates the as-of join guarantee. For each historical
label timestamp in the entity dataframe, only feature values that were actually valid at
or before that timestamp are retrieved — never a value from after that point in time. This
prevents "future leakage", which would otherwise inflate offline evaluation metrics that
fail to hold up in production.

## Offline vs Online Store

| Property        | Offline store                             | Online store                       |
|-----------------|-------------------------------------------|------------------------------------|
| Purpose         | Build point-in-time-correct training sets | Serve live predictions              |
| Access pattern  | Large batch scans over history            | Single-entity, low-latency lookups  |
| Contents        | Complete historical record                | Latest value per entity             |
| Implementation  | Parquet-backed file source                | SQLite key-value store              |

Both are populated from the same feature definitions, so training/serving consistency is
structurally guaranteed rather than manually maintained.

## Verification Summary

- `feast apply` — 1 entity + 2 feature views + 1 feature service created; `data/registry.db` written.
- `feast materialize-incremental` — 2 feature views materialized to the SQLite online store;
  `data/online_store.db` created (≈348 KB).
- `feast feature-views list` — both `iris_measurements` and `iris_engineered_features`
  report `AVAILABLE_ONLINE`.
- `get_online_features.py` — all 8 requested feature keys populated (no `None`) for `sample_id = 1`.
- `get_historical_features.py` — returns the requested entity rows (head of the 149-row
  Experiment 4 dataset) with all 8 feature columns populated and no unexpected nulls.
- `reuse_features_for_clustering.py` — non-trivial feature values returned through the
  Feature Service, confirming reuse by a structurally different model.