# Vendored — do not edit here

This `pipeline/` package is **vendored** from the ML repo:

- Source: https://github.com/jiahuiiiii/Kestrel-ML.git
- Path in source: `pipeline/`
- Commit: `d40eea8`

It is a package of pure functions over plain dicts/dataclasses — the backend
imports the four contract functions (`news.fetch`, `llm.classify_batch`,
`catalysts.apply`, `evaluator.evaluate`) and persists what they return. See
`app/service/ml_adapter.py` for the backend↔ML shape translation and
`app/service/scheduler_service.py` for the orchestration loop.

**Do not edit files in this directory.** Fixes belong upstream in Kestrel-ML;
re-vendor by re-copying `pipeline/` and bumping the commit above. The ML repo
keeps the tests/eval harness that prove this code.
