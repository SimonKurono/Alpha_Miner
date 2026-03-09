# Alpha Miner - Project Context
*Last updated: 2026-02-27 11:24 UTC | Session: s012*

---

## 🎯 CURRENT STATE
**Phase:** UI Intuition + Gemini Connectivity Cycle  
**Completion:** 97% overall  
**Status:** ⚠️ `GO_PENDING_LOCAL_GEMINI_LIVE_CHECK`  
**Next Milestone:** Local live Gemini+Search smoke + deployment hardening

---

## 🔥 THIS SESSION
**Goal:** Make UI intuitive and add Feature 2 Gemini + Google Search connectivity with strict health diagnostics.

**Tasks Completed:**
1. Extended Feature 2 model policy and schema contracts:
   - Added `gemini_with_search` and `gemini_only`.
   - Added `gemini_model` and `enable_google_search_tool`.
2. Implemented Gemini backend in model factory with deterministic fallback behavior.
3. Added model trace persistence:
   - `artifacts/<run_id>/model_trace.json`
4. Added strict runtime agent health contract in `runtime_utils`.
5. Reworked Streamlit UI to executive-first:
   - run story sections
   - status chips
   - preflight checks for Feature 2
   - debug-only JSON pattern
   - Altair visualizations in dashboard/library
6. Updated unit/integration tests for new model and runtime logic.
7. Updated runbooks and published validation report.
8. Patched Streamlit deprecation warnings by replacing `use_container_width` with `width="stretch"` across UI tables/charts.

---

## ✅ COMPLETED (Recent)

### Feature 2 Connectivity
- [x] `src/alpha_miner/agents/hypothesis_generation/schemas.py`
- [x] `src/alpha_miner/agents/hypothesis_generation/config_loader.py`
- [x] `src/alpha_miner/agents/hypothesis_generation/run_config_agent.py`
- [x] `src/alpha_miner/agents/hypothesis_generation/model_factory.py`
- [x] `src/alpha_miner/agents/hypothesis_generation/role_agents.py`
- [x] `src/alpha_miner/agents/hypothesis_generation/artifact_publisher_agent.py`
- [x] `src/alpha_miner/pipelines/feature2_hypothesis_cli.py`
- [x] `configs/feature2_hypothesis.yaml`

### Runtime Health
- [x] `src/alpha_miner/pipelines/runtime_utils.py` now enforces strict agent-health validation.

### UI Redesign
- [x] `ui/streamlit_app.py` refactored for readability and visual-first flow.
- [x] JSON moved to debug expanders in monitor/library/viewer flows.
- [x] Feature 2 preflight diagnostics added.

### Test Additions/Updates
- [x] `tests/unit/test_model_factory.py`
- [x] `tests/unit/test_pipeline_runtime_utils.py`
- [x] `tests/unit/test_ui_command_builder.py`
- [x] `tests/integration/test_feature2_hypothesis_e2e.py`

---

## 🚧 IN PROGRESS

| Agent/Module | Progress | Blocker | Next Step |
|--------------|----------|---------|-----------|
| Gemini live validation | 80% | local auth/network variability | run local Feature 2 smoke in gemini_with_search mode |
| Deployment hardening | 40% | container/deploy runbooks not finalized | add Cloud Run deploy checklist and smoke report |
| Observability polish | 70% | no centralized remote view | keep local run index; consider export layer later |

---

## 🚨 BLOCKERS & CRITICAL DECISIONS

**[R021] Live Gemini+Search path depends on local ADC/network** - MEDIUM  
- Code path implemented and fallback-safe.
- Final sign-off requires local live command verification.

---

## 📋 NEXT ACTIONS (Priority Order)

1. **[30-45m]** Run local Feature 2 live smoke with Gemini+Search.
2. **[45-60m]** Capture UI screenshots for updated readability validation.
3. **[2-3h]** Begin Cloud Run deployment hardening cycle.

---

## ⚠️ KNOWN ISSUES & TECH DEBT

- **[I018]** External provider variability (SEC/GDELT/RSS) remains.
- **[I019]** ADK internals may still emit warnings; UI now classifies mismatch signals as hard health failures.
- **[I017]** UI remains local-artifact based.

---

## 📦 KEY FILES (What to Review)

```
ui/streamlit_app.py
src/alpha_miner/agents/hypothesis_generation/model_factory.py
src/alpha_miner/agents/hypothesis_generation/role_agents.py
src/alpha_miner/pipelines/runtime_utils.py
configs/feature2_hypothesis.yaml
docs/runbooks/feature2_hypothesis.md
docs/runbooks/ui_streamlit_console.md
docs/validation/ui_gemini_connectivity_report_20260227.md
```

---

## 📊 QUICK METRICS
- Feature coverage: F1-F5 backend complete.
- UI mode: executive-first summaries + visuals + debug-expanders.
- New Feature 2 defaults: `model_policy=gemini_with_search`, `gemini_model=gemini-2.5-flash`.
- Pending sign-off item: local live Gemini+Search smoke.

---
