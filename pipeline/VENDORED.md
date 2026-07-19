# Vendored — do not edit here

This `pipeline/` package is **vendored** from the ML repo:

- Source: https://github.com/jiahuiiiii/Kestrel-ML.git
- Path in source: `pipeline/`
- Commit: `d40eea8`
- ⚠️ **Ahead of that commit:** `proposals.py` + `prompts/propose_changes.md` were
  written in the ML working tree (with `tests/test_proposals.py`) but are **not
  committed upstream yet**. Commit them in Kestrel-ML and bump the hash above —
  until then this copy is the only reviewed one, and a naive re-vendor from
  `d40eea8` would silently delete the proposal reviewer.

It is a package of pure functions over plain dicts/dataclasses — the backend
imports the four contract functions (`news.fetch`, `llm.classify_batch`,
`catalysts.apply`, `evaluator.evaluate`) plus `proposals.suggest` (the thesis
reviewer behind the proposals queue) and persists what they return. See
`app/service/ml_adapter.py` for the backend↔ML shape translation,
`app/service/scheduler_service.py` for the orchestration loop, and
`app/service/proposal_generator.py` for the proposal persistence.

**Do not edit files in this directory.** Fixes belong upstream in Kestrel-ML;
re-vendor by re-copying `pipeline/` and bumping the commit above. The ML repo
keeps the tests/eval harness that prove this code.
