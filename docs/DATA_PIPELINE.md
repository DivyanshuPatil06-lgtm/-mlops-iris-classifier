# Data Pipeline Documentation

Experiment 4 — Data Collection, Preprocessing, Feature Engineering, Validation, and Pipeline Automation.

The end-to-end data pipeline is defined declaratively in [`dvc.yaml`](../dvc.yaml) and is
executed with a single command:

```bash
dvc repro
```

Each stage is a standalone Python module under `src/pipeline/` with a CLI interface
(`argparse`), so it can also be run and tested in isolation.

---

## Pipeline Flow

```
        +-----------+
        |  collect  |  data/raw/iris_raw.csv
        +-----------+
              |
              v
        +------------+
        | preprocess |  data/processed/iris_preprocessed.csv
        +------------+
              |
              v
        +----------+
        | features |  data/processed/iris_features.csv
        +----------+
              |
              v
        +----------+
        | validate |  (no output; raises + exit 1 on failure)
        +----------+
```

### DVC dependency graph (`dvc dag`)

```
  +---------+
  | collect |
  +---------+
       *
       *
       *
+------------+
| preprocess |
+------------+
       *
       *
       *
 +----------+
 | features |
 +----------+
       *
       *
       *
 +----------+
 | validate |
 +----------+
```

`collect` is the only root stage (no declared `deps`); every subsequent stage declares
the previous stage's output as a `dep`, producing a strict linear dependency chain
`collect -> preprocess -> features -> validate`.

---

## Stage 1 — Data Collection (`src/pipeline/collect.py`)

| Attribute | Value |
|-----------|-------|
| **Purpose** | Simulate ingesting raw data from an external source and land it, unchanged, in the raw data zone. |
| **Inputs** | None (data source: `sklearn.datasets.load_iris`). |
| **Outputs** | `data/raw/iris_raw.csv` |
| **Command** | `python src/pipeline/collect.py --output data/raw/iris_raw.csv` |

**Behaviour**

- Loads the Iris dataset as a frame and renames the `target` column to `species`.
- Maps integer targets to human-readable species names (`setosa`, `versicolor`, `virginica`).
- Adds a collection-time audit column `collected_at` (UTC ISO-8601 timestamp).
- Writes the raw file (150 rows x 6 columns) to the raw zone.

**Validation rules enforced** — none at collection time. Data enters the lake
unmodified so that collection is fully reproducible; all cleaning happens downstream.

---

## Stage 2 — Data Preprocessing (`src/pipeline/preprocess.py`)

| Attribute | Value |
|-----------|-------|
| **Purpose** | Clean the raw data: remove duplicates, enforce numeric types, and impute missing values. |
| **Inputs** | `data/raw/iris_raw.csv` |
| **Outputs** | `data/processed/iris_preprocessed.csv` |
| **Command** | `python src/pipeline/preprocess.py --input data/raw/iris_raw.csv --output data/processed/iris_preprocessed.csv` |

**Behaviour**

1. **Duplicate removal** — drops exact duplicate records (`df.drop_duplicates()`).
   *Note: the stock sklearn Iris dataset contains one duplicate row, so 150 raw rows
   become 149 clean rows.*
2. **Type correction** — coerces each measurement column to numeric with
   `pd.to_numeric(..., errors="coerce")`, turning unparseable values into `NaN`.
3. **Missing-value imputation** — any resulting `NaN` is filled with the column median
   (logged per column).
4. **Target integrity** — rows with an unresolvable `species` are dropped
   (`dropna(subset=["species"])`).
5. **Metadata cleanup** — the collection-time column `collected_at` is removed so that
   downstream stages and outputs are deterministic.

**Validation rules enforced** — none (cleaning stage). Its output is what the
`validate` stage later asserts on.

---

## Stage 3 — Feature Engineering (`src/pipeline/features.py`)

| Attribute | Value |
|-----------|-------|
| **Purpose** | Derive new, model-useful features from the raw measurements. |
| **Inputs** | `data/processed/iris_preprocessed.csv` |
| **Outputs** | `data/processed/iris_features.csv` |
| **Command** | `python src/pipeline/features.py --input data/processed/iris_preprocessed.csv --output data/processed/iris_features.csv` |

**Derived features**

| Feature | Definition | Rationale |
|---------|-----------|-----------|
| `sepal_area` | `sepal length (cm) * sepal width (cm)` | Interaction term capturing sepal size. |
| `petal_area` | `petal length (cm) * petal width (cm)` | Interaction term capturing petal size. |
| `sepal_to_petal_length_ratio` | `sepal length (cm) / petal length (cm)` | Shape ratio; guards against divide-by-zero via `.replace(0, pd.NA)`. |
| `petal_length_bin` | `pd.cut(petal length, bins=[0, 2, 4.5, 7], labels=["short","medium","long"])` | Binned categorical feature. |

The output dataset has 9 columns (4 raw + `species` + 4 engineered features).

**Why this lives in a declared pipeline stage (not a notebook)** — see Q3 below:
reproducibility, automatic re-execution on upstream change, and prevention of
training-serving skew.

---

## Stage 4 — Data Validation (`src/pipeline/validate.py`)

| Attribute | Value |
|-----------|-------|
| **Purpose** | Assert schema and statistical expectations before data is allowed to flow to training. Hard-fails the pipeline on any violation. |
| **Inputs** | `data/processed/iris_features.csv` |
| **Outputs** | None (the validated dataset is the file it inspects). |
| **Command** | `python src/pipeline/validate.py --input data/processed/iris_features.csv` |

**Validation rules enforced**

1. **File presence** — raises a `DataValidationError` if the input file is missing.
2. **Schema / column presence** — the following columns must all exist:

   ```
   sepal length (cm), sepal width (cm), petal length (cm), petal width (cm),
   species, sepal_area, petal_area, sepal_to_petal_length_ratio, petal_length_bin
   ```

3. **Null check** — no null values are permitted in any column.
4. **Category check** — `species` must only contain
   `{setosa, versicolor, virginica}`.
5. **Range checks** (statistical / distributional):

   | Column | Expected range |
   |--------|----------------|
   | `sepal length (cm)` | 3.0 – 9.0 |
   | `sepal width (cm)` | 1.5 – 5.5 |
   | `petal length (cm)` | 0.5 – 8.0 |
   | `petal width (cm)` | 0.05 – 3.0 |

**Failure semantics** — on any violation the stage logs each error and raises
`DataValidationError`; the CLI entry point catches it and exits with **status code 1**.
A non-zero exit code is the signal DVC / CI uses to halt downstream stages, preventing
silently corrupted data from reaching model training.

---

## Running and Verifying the Pipeline

```bash
# 1. Full run — executes all 4 stages in order, exit code 0
dvc repro

# 2. Idempotent re-run — all stages report "didn't change, skipping"
dvc repro

# 3. View the dependency graph
dvc dag

# 4. Prove validation halts on bad data (expect exit code 1)
python -c "import pandas as pd; p='data/processed/iris_features.csv'; df=pd.read_csv(p); df.loc[0,'sepal length (cm)']=50.0; df.to_csv(p,index=False)"
python src/pipeline/validate.py --input data/processed/iris_features.csv   # exits 1
dvc checkout data/processed/iris_features.csv                               # restore good data
```

`dvc.lock` is generated/updated after each `dvc repro`, recording the exact content
hashes of every stage's dependencies and outputs. DVC uses these hashes to decide
which stages must be re-executed.

---

## Post-Lab Questions

**Q1. How does `dvc repro` decide which stages to re-execute, and why does this matter at scale?**
`dvc repro` compares the current content hashes of each stage's declared `deps`
(code + data) against the hashes stored in `dvc.lock` from the last successful run.
If a stage's dependencies are unchanged, DVC skips it and reuses its outputs; if any
hash differs, DVC re-runs that stage and, transitively, every downstream stage.
At scale this avoids re-running multi-hour jobs over terabytes of data for a one-line
change to an unrelated downstream script — the same economics as `make` not
recompiling unchanged source files.

**Q2. Why does `validate` raise an exception / exit non-zero instead of warning and continuing?**
In an automated pipeline a non-zero exit code is the standard failure signal that halts
downstream execution (and fails CI jobs). If validation only warned, invalid or
out-of-distribution data would silently flow into training, producing a model that appears
to train and deploy fine but is quietly unreliable — the exact "silent failure" problem
data validation exists to prevent. A hard failure forces human (or automated rollback)
intervention before bad data reaches production.

**Q3. Why should feature logic live in a versioned, declared stage rather than an ad-hoc notebook?**
Notebook cells are (1) not automatically re-executed or validated when upstream data
changes, since they aren't wired into `dvc repro`/CI; (2) prone to training-serving skew,
because the inference service must reimplement the same logic separately and any drift
silently degrades predictions; and (3) not reproducible or auditable, since cells can be
run out of order without leaving a hash-tracked record. Declaring features as a
`dvc.yaml` stage with explicit `deps`/`outs` makes the logic a first-class, versioned,
auto-triggered artifact that serving code can import directly.