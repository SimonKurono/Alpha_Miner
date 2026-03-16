# UI Runbook: Streamlit Console (Executive-First)

## Purpose
Local console for Features 1-5 with:
1. Readable run stories and status chips.
2. Visual-first analytics (Altair charts where applicable).
3. Debug JSON only in collapsible sections.

## Screens
1. `Create Run`
2. `Run Timeline`
3. `Run Monitor`
4. `Results Dashboard`
5. `Factor Library`
6. `Report Viewer`

## Start UI
```bash
PYTHONPATH=src streamlit run ui/streamlit_app.py
```

## Create Run Highlights
1. Stage-specific run forms for Feature 1-5.
2. Feature 2 preflight button validates:
   - env variables
   - ADC credentials
   - Gemini dry-run (with optional Google Search tool)
3. Post-run diagnostics include:
   - run status
   - agent health (`ok|failed`)
   - warning classification

## Agent Health Policy
1. App-name mismatch warnings are treated as hard health failures in UI diagnostics.
2. UI shows explicit remediation text when health is `failed`.
3. Runtime helper is enforced in CLI:
   - `src/alpha_miner/pipelines/runtime_utils.py`

## Timeline and Monitor
1. Timeline source: `artifacts/run_index.json`.
2. Timeline shows filtered stage/status and lineage progression chips.
3. Monitor shows:
   - summary metrics
   - lineage table
   - artifact integrity table
   - issues/remediation panel

## Visualizations
1. Results Dashboard:
   - top Sharpe bar chart
   - IC vs Turnover scatter
   - net return curves
2. Factor Library:
   - originality vs complexity scatter
   - accepted/rejected split tables
3. Report Viewer:
   - selected factor summary table + rendered markdown note

## Troubleshooting
1. `ModuleNotFoundError: alpha_miner`:
   - launch with `PYTHONPATH=src`.
2. Feature 2 preflight fails:
   - verify `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION`
   - verify ADC (`gcloud auth application-default login`)
3. Missing artifacts:
   - use Run Monitor issue panel to locate missing paths
   - rerun upstream stage.

