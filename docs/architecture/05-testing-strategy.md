# Testing Strategy

## Current-state problems (resolves KI-25)

- `conftest.py` shares state via mutable attributes set directly on the `pytest` module namespace, rather than proper fixtures — fragile, hidden coupling, not test-isolated.
- Only the audio sync path is exercised anywhere in the suite; brightness sync (`synchronize_videos_from_brightness`) has zero test coverage.
- Nearly every test depends on a real dataset downloaded from Figshare and real ffmpeg/deffcode execution — slow, requires network access, and requires FFmpeg installed. There are no fast, isolated unit tests for most logic.
- There are no GUI tests (and, going forward, will need no PySide6 tests at all once it's removed).

## Target test pyramid

### `core` — unit tests

Fast, isolated, no real video/audio files or subprocess calls required:

- Pipeline stage tests using a mocked `VideoBackend` (trivial given the `Protocol`-based interface from [02-core-library.md](02-core-library.md) — a test double just needs matching method signatures).
- Pure-function tests for lag normalization (`LagResult` contract, KI-02) and brightness-event detection (KI-08) using small synthetic numpy arrays — this is what closes the current zero-coverage gap on the brightness path cheaply, without needing real video fixtures.
- Regression tests specifically targeting each fixed known issue where feasible (e.g. a synthetic case that would have tripped the old index-0 sentinel bug, KI-08; a case verifying the `Path.exists()` fix, KI-10).

### `core` — integration tests

A small number of tests run against tiny real fixture videos (a few seconds each) checked into the repo, instead of relying on a large downloaded dataset for every test run. This covers real ffmpeg/deffcode invocation without the cost of the full Figshare dataset.

One slower, more thorough tier still exercises the existing Figshare-downloaded sample dataset for full end-to-end confidence, but is marked `@pytest.mark.slow` and excluded from the default local/CI run — opt-in only (e.g. a scheduled CI job or an explicit `pytest -m slow` invocation).

### `api` — endpoint tests

`TestClient`-based tests hitting each endpoint in [03-api-design.md](03-api-design.md), with the underlying `core` pipeline dependency-injected as a fast/mocked implementation so these tests don't wait minutes for a real ffmpeg trim to complete.

### `frontend` — component tests

Vitest + React Testing Library, covering the `useJobPolling` hook and the Setup/Progress/Result screens from [04-frontend.md](04-frontend.md). No end-to-end test requirement for v1 — explicitly deferred.

## Fixture / conftest redesign

Replace the current `pytest`-namespace-global pattern with proper `pytest.fixture`s:

- A session-scoped fixture providing the small checked-in fixture videos, used by default across the fast integration tier.
- A separate, explicitly opt-in fixture for downloading and using the full Figshare dataset, used only by the slow-marked tests.

## CI plan

- Fix the Python version mismatch (KI-26): the CI matrix should match whatever `requires-python` actually claims in `pyproject.toml`, rather than testing only 3.10 against a wider claimed range.
- Run `core` unit tests (and `api` tests) on every push/PR.
- Run the slow/integration tier (real fixture videos, and the full Figshare-based tier) on a schedule or behind an explicit label/trigger, not on every push.
- Run `frontend` tests (`npm test`) in CI alongside the Python suite.
- Actually wire up the linting that already has config but isn't enforced today: `.flake8` exists but is not run in any CI workflow, and only Black formatting is checked on PRs. Recommend consolidating Black + flake8 + isort into `ruff` (format + lint in one tool) during the rewrite to reduce tooling overhead — flagged as a nice-to-have, not a blocker for the rewrite itself.

## Known issues resolved by this document

KI-25, and (jointly with `02-core-library.md`) the regression-test angle on KI-08/KI-10.
