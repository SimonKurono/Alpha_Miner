# Alpha Miner - Project Context
*Last updated: 2024-01-18 14:30 UTC | Session: s007*

---

## 🎯 CURRENT STATE
**Phase:** Implementation - Core Agents  
**Completion:** 35% overall (MVP target: 60%)  
**Status:** ⚠️ BLOCKED - Storage format decision needed  
**Next Milestone:** End-to-end MVP (hypothesis → factor → backtest → report)

---

## 🔥 THIS SESSION
**Goal:** Unblock FactorConstructionAgent + complete core logic  
**Tasks:**
1. Resolve D005 (factor storage: SQLite vs JSON) - benchmark both
2. Complete `FactorConstructionAgent.construct()` - AST → Python code
3. Write 15 unit tests for code generation edge cases
4. Update factor registry schema in `configs/factor_schema.yaml`

**Success criteria:** Can generate + save a valid factor from AST

---

## ✅ COMPLETED (Recent)

### Week 3: Core Infrastructure
- [x] **System architecture** (2024-01-15)
  - 6-agent ADK tree finalized
  - Tool contracts defined (12 Pydantic models)
  - `docs/architecture.md` + Mermaid diagram

- [x] **Factor DSL + Parser** (2024-01-16)
  - Lark grammar: 8 operations (Rank, Normalize, Delay, Sum, etc.)
  - AST nodes: BinaryOp, Function, Field, Constant
  - Complexity scoring: `node_count + 2*depth + variety_bonus`
  - Files: `src/dsl/grammar.lark`, `src/dsl/ast.py`

- [x] **HypothesisAgent** (2024-01-17)
  - Generates 3 factor theses per run
  - Incorporates risk tolerance parameter
  - Tool: `HypothesisGeneratorTool` (working)

- [x] **DataIngestionAgent** (2024-01-18)
  - SEC EDGAR: 10-K/10-Q retrieval (rate-limited to 10/s)
  - Market data: yfinance integration (abstracted interface)
  - Caching layer: 7-day TTL
  - ⚠️ Tech debt: hardcoded paths (TD001)

---

## 🚧 IN PROGRESS

| Agent/Module | Progress | Blocker | Next Step |
|--------------|----------|---------|-----------|
| **FactorConstructionAgent** | 60% | D005 | AST → code generator |
| **EvaluationAgent** | 30% | Waiting on above | Backtest integration |
| **Multi-agent debate** | 10% | Design only | Implement round-robin |
| **Streamlit UI** | 5% | Low priority | After E2E works |

### FactorConstructionAgent Details
**What works:**
- AST parsing from DSL expressions ✅
- Complexity scoring ✅
- Hypothesis alignment (basic cosine similarity) ✅

**What's blocked:**
- Code generation: `ast_to_code()` stubbed but incomplete
- Factor saving: no storage backend chosen (D005)
- Originality check: needs factor registry to compare against

**Files:**
- `src/agents/factor_construction.py` (280 lines, 40% complete)
- `src/dsl/code_generator.py` (stub only)
- `tests/test_factor_construction.py` (5 tests, need 15+)

---

## 🚨 BLOCKERS & CRITICAL DECISIONS

### Active Blockers
**[B001] Factor storage format** - CRITICAL  
- **Impact:** Blocks FactorConstructionAgent save, EvaluationAgent load, UI factor browser
- **Options:**
  - SQLite: Queryable, ACID, harder to version control
  - JSON: Git-friendly, human-readable, no queries
  - Parquet: Fast for large data, not human-readable
- **Action needed:** Benchmark write 100 + read/filter performance
- **Decision by:** End of this session

### Recent Decisions
**[D004] Backtest engine = Vectorbt** (2024-01-18)
- Rationale: 10x faster than Backtrader, good vectorization
- Alternative: Custom engine (too much work for MVP)
- Files affected: `src/backtesting/engine.py`

**[D003] Price data = yfinance** (2024-01-17)
- Rationale: Free, good enough for prototype
- Risk: May hit rate limits with 500 stocks
- Mitigation: Implemented data provider abstraction, can swap later

**[D002] Parser = Lark** (2024-01-16)
- Rationale: Simpler grammar syntax than PLY
- Alternative: pyparsing (more verbose)

---

## 📋 NEXT ACTIONS (Priority Order)

### Immediate (This Session)
1. **[2hr]** Run storage benchmark
   - Write test: 100 factors × 3 versions each
   - Read test: Filter by Sharpe > 1.0, sort by date
   - Document results in `docs/storage_decision.md`
   - Make D005 decision

2. **[3hr]** Complete AST → Python code generation
   - Implement `CodeGenerator.visit()` for all AST nodes
   - Handle edge cases: division by zero, missing fields
   - Generate vectorized pandas code (not loops)
   - Example: `Rank(close / Delay(close, 5))` → valid Python

3. **[1hr]** Factor registry schema
   - Define: metadata (id, timestamp, hypothesis_id, metrics)
   - Define: expression (DSL string + AST JSON)
   - Define: code (generated Python)
   - Create: `FactorRegistry.add()` and `FactorRegistry.search()`

### Next Session
4. **[4hr]** Complete EvaluationAgent
   - Integrate Vectorbt backtest engine
   - Compute: Sharpe, IC, turnover, decay
   - Implement walk-forward validation
   - Pass/fail thresholds: Sharpe > 0.5 IS, > 0.3 OOS

5. **[2hr]** End-to-end MVP test
   - Single hypothesis: "Revenue growth predicts returns"
   - Generate 3 factor candidates
   - Backtest on 50 stocks, 1 year
   - Output: metrics + factor expression

---

## ⚠️ KNOWN ISSUES & TECH DEBT

### P1 - Must Fix Before MVP
- **[I001]** Parser fails on nested `Rank(Rank(x))`
  - Workaround: Limit to single-level nesting
  - Impact: Reduces DSL expressiveness
  - Fix: Update Lark grammar recursion rules (2hr)

### P2 - Fix Before Production
- **[TD002]** No retry logic for API calls
  - Impact: Will fail on transient errors
  - Fix: Add tenacity decorator to all API tools (3hr)

- **[TD001]** Hardcoded paths in DataIngestionAgent
  - Impact: Not portable across systems
  - Fix: Move to `configs/paths.yaml` (1hr)

### P3 - Nice to Have
- **[TD003]** AST similarity uses Levenshtein (inefficient)
  - Impact: Slow for large factor libraries (>1000 factors)
  - Fix: Implement tree edit distance (4hr)

---

## 📦 KEY FILES (What to Review)

### To work on this session:
```
src/alpha_miner/agents/factor_construction.py    # main focus
src/alpha_miner/dsl/code_generator.py            # needs implementation
src/alpha_miner/dsl/ast.py                       # understand node types
tests/test_factor_construction.py                # expand coverage
configs/factor_schema.yaml                       # create this
```

### Recently changed:
```
src/alpha_miner/agents/data_ingestion.py         # completed yesterday
src/alpha_miner/tools/sec_edgar.py               # rate limiting added
pyproject.toml                                   # vectorbt 0.26 added
```

### Reference docs:
```
docs/architecture.md                             # agent tree
docs/factor_dsl.md                              # DSL specification
docs/evaluation_methodology.md                  # backtest protocol (draft)
```

---

## 🎓 SESSION HANDOFF

### What just happened:
- Completed DataIngestionAgent with SEC EDGAR + yfinance integration
- Added caching layer (saves ~80% of API calls in testing)
- Made decision D004: using Vectorbt for backtesting
- Identified blocker B001: storage format must be decided

### Current state of FactorConstructionAgent:
- AST parsing: ✅ Working for all 8 operations
- Complexity scoring: ✅ Formula implemented
- Code generation: ❌ Stubbed only - THIS IS YOUR FOCUS
- Factor saving: ❌ Blocked by B001

### What the next session needs to know:
1. **If D005 → SQLite:** Use schema in `src/database/schema.sql`, add `sqlalchemy` dependency
2. **If D005 → JSON:** Create `data/factors/` directory, use `{factor_id}.json` naming
3. Code generator should output pandas-compatible code (vectorized ops)
4. Test with these expressions:
```python
   "Rank(close / Delay(close, 5))"
   "Normalize(volume) * 0.5 + Normalize(returns)"
   "(close - Delay(close, 20)) / Delay(close, 20)"
```

### Open questions:
- Should generated code include error handling? (e.g., ZeroDivisionError)
- How to handle missing data in `Delay()` at start of time series?
- Should we cache compiled code or regenerate each time?

### Expected outcome this session:
- D005 resolved with data
- FactorConstructionAgent 100% complete
- 15+ passing tests
- Can save/load factors
- Ready to start EvaluationAgent integration

---

## 📊 QUICK METRICS
- **Code:** 2,400 LOC | 6/12 modules complete
- **Tests:** 180 tests | 65% coverage (target: 80%)
- **Performance:** DataIngestion: 15s for 50 stocks | Target backtest: <30s
- **Dependencies:** 12 packages | Python 3.11 | ADK 0.1.7

---

## 🔗 IMPORTANT LINKS
- AlphaAgent paper: arXiv:2502.16789
- AlphaAgents paper: arXiv:2508.11152
- ADK docs: https://github.com/google/adk-python
- SEC EDGAR API: https://www.sec.gov/edgar/sec-api-documentation

---