# CI Pipeline Documentation

## 1. Overview

This project uses GitHub Actions to implement a Continuous Integration (CI) pipeline
for the MLOps Iris project. The workflow is defined in `.github/workflows/ci.yml`.

The pipeline automatically runs when code is pushed to the `main` or `develop`
branches and when a pull request targets either of these branches.

The CI pipeline checks Python code quality, executes automated tests, generates test
and coverage reports, and validates model accuracy against a predefined threshold.

## 2. CI Jobs

The workflow consists of three jobs executed in dependency order.

### 2.1 Build and Lint

**Job name:** `build-and-lint`

**Purpose:** Verify that the Python source code compiles successfully and follows the
configured linting standards.

**Main steps:**
- Check out the repository.
- Set up Python 3.11.
- Install project dependencies, Flake8, and testing tools.
- Compile the Python files in `src` and `tests`.
- Run Flake8 on the source code.

**Success condition:** Python compilation and linting complete without errors.

### 2.2 Test Suite

**Job name:** `test-suite`

**Dependency:** `needs: build-and-lint`

**Purpose:** Execute the automated tests to verify the correctness of the data-processing
pipeline and related functionality.

**Main steps:**
- Check out the repository and set up Python 3.11.
- Install project dependencies and testing tools.
- Create the required data directories.
- Collect the Iris dataset.
- Preprocess the dataset.
- Engineer features.
- Execute the tests using pytest.
- Generate test results and code coverage reports.
- Upload the reports as a GitHub Actions artifact named `test-and-coverage-reports`.

The artifact contains `test-results.xml` and `coverage.xml` when both files are generated
successfully. These artifacts are downloadable from the completed workflow run's summary
page.

**Success condition:** All tests pass.

### 2.3 Model Quality Gate

**Job name:** `model-quality-gate`

**Dependency:** `needs: test-suite`

**Purpose:** Verify that the model satisfies the minimum acceptable accuracy requirement.

**Main steps:**
- Check out the repository and set up Python 3.11.
- Install the required dependencies.
- Prepare the Iris dataset by running the collection, preprocessing, and feature-engineering stages.
- Execute `tests/test_model_quality.py`.

The normal minimum accuracy threshold is `0.90` (90%).

**Success condition:** The model-quality tests pass, including the minimum accuracy
assertion.

## 3. Job Dependency Order

The jobs are configured with the following dependency sequence:

```
build-and-lint
      |
      v
  test-suite
      |
      v
model-quality-gate
```

The dependency configuration uses the `needs` keyword:
- `test-suite` requires `build-and-lint` to succeed.
- `model-quality-gate` requires `test-suite` to succeed.

Consequently, a failure in an upstream job causes downstream jobs to be skipped by
default unless the workflow explicitly overrides this behavior. This creates a fail-fast
pipeline: if linting fails, the (more expensive, longer-running) test and model-quality
jobs never execute, saving compute time and giving faster, more targeted feedback.

## 4. Branch Protection Ruleset

A GitHub branch ruleset named **Protect main - CI checks** was configured to protect the
`main` branch.

The ruleset includes:
- Requiring changes to be submitted through a pull request.
- Requiring the configured CI status checks to pass before merging.
- Requiring branches to be up to date before merging (if enabled in repository settings).

The required status checks selected in GitHub are:
- `build-and-lint`
- `test-suite`
- `model-quality-gate`

This configuration helps prevent changes from being merged into `main` when the required
checks fail, converting an informal best practice ("please test before you push") into a
technically guaranteed gate enforced uniformly by GitHub.

## 5. Pull Request Verification

A feature branch named `feature/ci-verification-test` was created, and a harmless README
change was committed and pushed. A pull request was opened from this branch into `main`.
The `pull_request` trigger started the GitHub Actions workflow, and all three jobs
completed successfully. The pull request was subsequently merged after the checks passed.
This verified that the CI workflow runs on pull requests as intended.

## 6. Model-Quality Regression Demonstration

To test the pipeline's ability to detect a model-quality regression, a temporary branch
named `feature/simulate-regression` was created. The threshold in
`tests/test_model_quality.py` was temporarily changed from:

```python
MIN_ACCEPTABLE_ACCURACY = 0.90
```

to:

```python
MIN_ACCEPTABLE_ACCURACY = 0.999
```

A pull request was opened from the temporary branch into `main`.

**Observed results:**
- Build and Lint: Passed.
- Test Suite: Failed (model accuracy 0.9667 fell below the 0.999 threshold).
- Model Quality Gate: Skipped (depends on the successful completion of `test-suite`).

The test output reported an accuracy of approximately 0.9667 (96.67%), which is below
the required 99.90%. The error confirmed:

```
AssertionError: Model accuracy 0.9667 fell below
the minimum acceptable threshold of 0.999
```

The other 15 tests passed. This demonstrates that the CI workflow detects a model-quality
regression and returns a failed status.

**Follow-up:** The demonstration pull request was closed without merging, and the
temporary threshold change was reverted on `main` so the normal threshold of `0.90`
remains in effect.

## 7. Verification Evidence

- `.github/workflows/ci.yml` exists and defines the three CI jobs with correct `needs:`
  dependencies.
- `test-results.xml` is generated in JUnit XML format and contains `<testsuite>` and
  `<testcase>` elements for every test, which CI tools parse to display pass/fail
  summaries.
- Test and coverage artifacts are downloadable from the completed workflow run's summary
  page.
- The branch protection ruleset correctly enforces the quality gate: a failing check
  disables the PR merge button with the message "Required statuses must pass before
  merging."
- `docs/CI_PIPELINE.md` exists and accurately documents the pipeline structure and the
  regression-blocking demonstration evidence.