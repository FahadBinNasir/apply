# Status: RULES Agent

## Progress
- `ProductionRulesEngine` implemented in `app/pipeline/rules/engine.py`:
  - Hard filters: Location (Karachi/Remote only), Avoid fields (sales, BD, HR, admin, accounting), Education gates (MS required), Night shift, Expired deadlines (`NOW_OVERRIDE`).
  - Soft filters: Level/Experience (fresh grad / trainee / intern / 0-1 yrs never rejected, 2-3 yrs = STRETCH, >3 yrs = SKIPPED).
  - Special tiers: WALKIN, MANUAL (link/form/LinkedIn/no email).
  - Unknown gender on female-only -> STRETCH with warning flag.
- `ProductionScorer` implemented in `app/pipeline/rules/scoring.py`:
  - Combines rules evaluation and base score into final Tier and human-readable reason summary.
- `ProductionDeduper` implemented in `app/pipeline/rules/dedupe.py`:
  - Token-set ratio matching across company and title using `rapidfuzz`.
- Unit tests written and green: `tests/rules/test_rules.py` (13 passed, covering F1-F12 fixtures, deduplication, night shift, and gender checks).
- Requirements listed in `requirements/rules.txt`.
- Env vars declared in `contracts/env/rules.yaml`.

## Interfaces Implemented
- `RulesEngine` (from `contracts.protocols`)
- `Scorer` (from `contracts.protocols`)
- `Deduper` (from `contracts.protocols`)

## Open Issues / Notes
- None. Fully deterministic and validated against `profile.seed.yaml` and `fixtures.md`.
