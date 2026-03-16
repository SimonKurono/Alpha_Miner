# Feature 5 Plan: Writing/Report Generation

## Goal
Implement a deterministic report-generation workflow that consumes Feature 4 outputs and publishes a research-note package for downstream UI and export layers.

## Locked Defaults
- Report mode: `deterministic_first`
- Factor policy: `promoted_plus_top_fallback`
- Fallback count: `3`
- Runtime budget: `300s`
- Scope: backend only (no UI changes)

## Implemented Components
- Agents: `src/alpha_miner/agents/report_generation/`
  - run config, artifact loading, data prep/selection
  - report drafting, quality gate, publisher
  - root workflow composition
- Reporting tools: `src/alpha_miner/tools/reporting/`
  - evaluation bundle loader
  - composite score + policy selection
  - deterministic markdown renderer
  - report quality validator
- CLI: `src/alpha_miner/pipelines/feature5_report_cli.py`
- Config: `configs/feature5_report.yaml`
- Tests: unit, integration, and golden trajectory suite

## Artifacts
- `artifacts/<run_id>/research_note.md`
- `artifacts/<run_id>/research_note.json`
- `artifacts/<run_id>/report_quality.json`
- `artifacts/<run_id>/report_manifest.json`

## Notes
- When no promoted factors exist, fallback selection is used and caveat language is inserted in the executive summary.
- Quality gate enforces required headings plus educational/research disclaimer language.
