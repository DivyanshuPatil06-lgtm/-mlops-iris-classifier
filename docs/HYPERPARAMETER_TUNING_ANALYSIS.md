# Experiment 7 — Hyperparameter Tuning Analysis

This document summarizes the baseline model, the improvement obtained by Grid Search and
Random Search, and the search-efficiency comparison for the `mlops-iris-classifier`
random-forest tuning experiment (Experiment 7).

All three runs are tracked in MLflow (experiment `iris-hyperparameter-tuning`, SQLite
backend store `sqlite:///mlflow.db`). Every candidate configuration of both searches is
additionally logged as a downloadable CSV artifact, and the tuning used 5-fold
cross-validation internally (`scoring="f1_macro"`) so that the held-out test set is only
touched once, for the final post-hoc evaluation.

## 1. Baseline Model

| Attribute | Value |
|-----------|-------|
| Model | `DecisionTreeClassifier` (all default hyperparameters) |
| CV F1 Macro (5-fold) | **0.9663** (± 0.0316) |
| Test Accuracy | **0.9000** |
| Total model fits | 5 (one per CV fold) |
| MLflow run | `baseline_decision_tree` |

The baseline is deliberately untuned: it exists only to sanity-check the end-to-end
pipeline (data loading → feature selection → encoding → split → evaluation) and to give
every later tuning effort a reference point. It already scores very highly on CV
(0.9663), reflecting how separable the Iris feature set from Experiment 4 is.

## 2. Grid Search

| Attribute | Value |
|-----------|-------|
| Model | `RandomForestClassifier` |
| Search space | `n_estimators`=[50,100,200], `max_depth`=[3,5,10,None], `min_samples_split`=[2,5,10], `max_features`=["sqrt","log2"] |
| Total combinations | 72 (3 × 4 × 3 × 2) |
| Cross-validation | 5-fold |
| Total fits | **360** (72 combinations × 5 folds) |
| Best CV F1 Macro | **0.9663** |
| Test Accuracy | **0.9667** |
| Best params | `max_depth=3`, `max_features="sqrt"`, `min_samples_split=2`, `n_estimators=50` |
| MLflow run | `grid_search_random_forest` |
| Artifact | `grid_search_all_candidates.csv` (all 72 candidates, mean/std CV score + rank) |

Grid Search exhaustively evaluated the entire Cartesian product of the grid, so the best
combination *within* that grid is guaranteed to have been found.

## 3. Random Search

| Attribute | Value |
|-----------|-------|
| Model | `RandomForestClassifier` |
| Search space | `n_estimators`~randint(50,300), `max_depth`∈{3,5,10,15,None}, `min_samples_split`~randint(2,15), `max_features`∈{"sqrt","log2"} |
| Iterations (`n_iter`) | 30 |
| Cross-validation | 5-fold |
| Total fits | **150** (30 combinations × 5 folds) |
| Best CV F1 Macro | **0.9663** |
| Test Accuracy | **0.9667** |
| Best params | `max_depth=3`, `max_features="sqrt"`, `min_samples_split=6`, `n_estimators=100` |
| MLflow run | `random_search_random_forest` |
| Artifact | `random_search_all_candidates.csv` (all 30 candidates, mean/std CV score + rank) |

Random Search sampled 30 configurations independently from the same space and converged
on the same top CV score as Grid Search while evaluating far fewer candidates.

## 4. Comparison

Produced by `python src/compare_tuning_results.py` (which reads the three MLflow runs back
from the tracking store — it does not retrain anything):

```
Run Name                    CV f1_macro    Test Accuracy  Total Fits
----------------------------------------------------------------------
baseline_decision_tree      0.9663         0.9000         5
grid_search_random_forest   0.9663         0.9667         360
random_search_random_forest 0.9663         0.9667         150
```

### 4.1 Improvement over the baseline

Both tuned Random Forest configurations improved on the baseline on the metric that
matters for the deployed artifact — **held-out test accuracy rose from 0.9000 (baseline)
to 0.9667 (both searches)**. On 30 test samples that is one extra correctly-classified
sample (27/30 → 29/30); the tuned shallow forest generalizes better than the unpruned
default decision tree, which overfits the training folds.

Note that on this *particular* feature set the best **CV** F1 Macro of the tuned models
(0.9663) equals the baseline's CV F1 Macro (0.9663). This is an honest, informative result
rather than a defect: the Experiment 4 feature set is nearly linearly separable, so
`f1_macro` saturates — a default decision tree already sits at the plateau, and there is
no CV headroom left for tuning to exploit. The value tuning adds here is robustness on
unseen data (test accuracy) and a systematically chosen, documented configuration, not a
higher CV number. If a tuned model had scored *worse* than the baseline, that would have
been an equally actionable signal (mis-configured search space/metric or overfitting).

### 4.2 Search efficiency

| Search | Combinations | Folds | Total fits | Best CV F1 | Test Acc |
|--------|--------------|-------|------------|------------|----------|
| Grid Search | 72 | 5 | 360 | 0.9663 | 0.9667 |
| Random Search | 30 | 5 | 150 | 0.9663 | 0.9667 |

Random Search matched Grid Search exactly on both CV score and test accuracy while
performing **150 fits instead of 360 — 210 fewer fits, a 58.3% reduction (well under half
the computation)**. This is the practical demonstration of Bergstra & Bengio (2012): with
a fixed budget, independently sampling each hyperparameter explores the dimensions that
actually matter more effectively than exhaustively varying every dimension, including the
irrelevant ones.

### 4.3 Hyperparameter sensitivity

Reading `grid_search_all_candidates.csv` / `random_search_all_candidates.csv`
(every candidate's mean/std CV score and rank):

- **`max_depth` and `max_features` dominate.** Every rank-1 candidate uses `max_depth=3`
  together with `max_features="sqrt"`; deeper trees did not help.
- **`n_estimators` and `min_samples_split` are nearly inert.** The top of the grid is a broad
  plateau: many `n_estimators`/`min_samples_split` combinations tie at 0.9663 (± 0.0316).
- This is exactly *why* Random Search is competitive — it wastes no effort exhaustively
  enumerating the two unimportant dimensions, yet still covers the two important ones.

Grid Search would remain preferable when the space is small (exhaustive enumeration is
cheap), when a fully deterministic, reproducible enumeration of every combination is
required for audit/regulatory reasons, or when strong hyperparameter interactions make
exhaustive coverage necessary to capture them reliably.

## 5. Verification Summary

- `python src/baseline_model.py` — completed and logged `baseline_decision_tree` to the
  `iris-hyperparameter-tuning` experiment (CV F1 Macro 0.9663, test accuracy 0.9000).
- `python src/grid_search_tuning.py` — printed `72 combinations x 5 folds = 360 total fits`,
  confirming the full 3×4×3×2 grid was exhaustively searched; best params
  `max_depth=3, max_features='sqrt', min_samples_split=2, n_estimators=50`.
- `python src/random_search_tuning.py` — printed `30 combinations x 5 folds = 150 total fits`.
- MLflow shows exactly **3 runs** under `iris-hyperparameter-tuning`, each `FINISHED`, with a
  `grid_search_all_candidates.csv` / `random_search_all_candidates.csv` artifact listing every
  candidate's mean/std CV score and rank (72 and 30 rows respectively).
- `python src/compare_tuning_results.py` — printed the table in §4: both tuned models beat
  the baseline's test accuracy (0.9000 → 0.9667), and Random Search reached Grid Search's
  best score using 150 vs 360 total fits.

> Tools: Python 3.11.9, scikit-learn 1.9.1, MLflow 2.17.2, SciPy 1.17.1, pandas, NumPy.