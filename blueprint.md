TECHNICAL CONSTRAINTS:
- ADK version: 0.1.x (or specify 1.x if using newer)
- Primary LLM: Claude 3.5 Sonnet via Vertex AI
- Prototype universe: S&P 500 (or Russell 3000 subset)
- Backtest period: 2020-2024 (5 years)
- Minimum viable factor library: 10 reference factors
- Local development: 16GB RAM, no GPU required
- Max runtime per hypothesis: 5 minutes
- Factor evaluation window: 252 trading days (1 year)
```


Role
You are a principal engineer + quant research lead. Produce a complete, implementation-ready project plan for a resume-grade system named “Alpha Miner”. This wil be implemented in the steps provided in this prompt + the blueprint.md file.

Non-negotiable constraints
- No proprietary datasets. Use only public and/or free-to-access APIs for the prototype.
- Use Google Agent Development Kit (ADK) in Python as the agent framework.
- Output must be rigorous and exhaustive: architecture, modules, interfaces, tests, evals, UI, deployment.
- Simple UI. Minimal clicks. Clear outputs. No feature bloat.
- Educational/research tool only. No claims of financial advice.
- Keep a context.md file that continuously updates after each new update and change in the following format as shown in context_md_example.md


ASSUMPTION PROTOCOL:
- State all assumptions in a dedicated "Assumptions" section at the start
- Flag HIGH-RISK assumptions (could invalidate design)
- Provide 2-3 alternatives for each high-risk assumption
- Mark sections with [ASSUMPTION: <brief note>] inline
- Proceed with the most reasonable path, but acknowledge alternatives

Concept to implement (match this structure exactly)
Alpha Miner is an agentic framework that discovers, evaluates, and refines alpha signals using:
- market data (prices/volume/returns)
- unstructured text (SEC filings like 10-K/10-Q, plus news/sentiment text)
Pipeline stages:
1) Parallel data ingestion (market + text)
2) Hypothesis generation (explicit factor thesis)
3) Factor construction (generate formulaic factor expressions + implementations)
4) Evaluation loop (backtest + robustness + decay + originality/complexity constraints)
5) Writing/report generation (research note)

Mandatory research grounding to incorporate
A) Use the AlphaAgents paper (arXiv:2508.11152) as inspiration for:
- Specialized “analyst role” agents (fundamental / sentiment / valuation)
- Internal debate/consensus mechanism when agents disagree
- Risk tolerance conditioning as an explicit parameter (risk-averse vs risk-neutral)
B) Use the AlphaAgent codebase repo structure as inspiration:
https://github.com/RndmVariableQ/AlphaAgent
Mirror its “production-like” layout: src package, constraints folder, docs folder, UI folder, configs, CLI entrypoints.
C) Use the AlphaAgent paper mechanisms (arXiv:2502.16789) for alpha-decay resistance:
- Originality enforcement via AST-based similarity vs existing factors
- Hypothesis–factor alignment scoring
- Complexity control using AST-derived constraints

Public data sources (prototype)
- SEC EDGAR JSON + XBRL endpoints hosted on data.sec.gov for filings and fundamentals
- FRED API for macro series
- GDELT (Doc API / available documented interfaces) for news text
- Price data: choose a free prototype source (Stooq via pandas-datareader is acceptable), but implement a data-provider abstraction so it can be swapped later.

Deliverables you must produce in your answer
1) Product spec
- Target user
- User stories
- UX principles for a “simple UI”
- Explicit non-goals

2) System architecture (FOCUS: ADK agent tree only)
- Mermaid diagram showing ONLY:
  - Root workflow agent
  - 3-5 key sub-agents (data ingestion, hypothesis, evaluation, report)
  - Tool boundaries
- One paragraph per agent: responsibility + inputs + outputs
- session.state schema (5-10 key namespaces max)
- Defer implementation details to later phase

3) ADK implementation design
- Which parts are LlmAgent vs CustomAgent vs Workflow Agents
- Explicit use of ADK primitives:
  - SequentialAgent, ParallelAgent, LoopAgent orchestration
  - session.state design (namespaced keys)
  - AgentTool usage for explicit sub-agent invocation
- Tool interfaces: function signatures, input/output schemas (Pydantic models)
- Failure handling: retries, rate limits, partial data, tool errors
- Observability plan: logging, tracing, run IDs, artifact persistence

4) Factor DSL specification (constrained scope)
- Support ONLY these operations initially:
  - Rank(), Normalize(), WinsorizedSum()
  - Basic arithmetic: +, -, *, /
  - Data fields: close, volume, market_cap, returns_1d, returns_5d
- Example valid expressions (provide 3)
- AST node types (max 10 node types)
- Complexity score formula (one equation)
- Originality score: Levenshtein distance on AST serialization
- Defer: advanced functions (cross-sectional, time-series)

5) Backtesting and evaluation methodology
- Backtest engine choice and rationale (lightweight + reproducible)
- Metrics to compute (minimum):
  - Sharpe ratio
  - Information ratio vs a benchmark
  - Information Coefficient (rank correlation of scores vs forward returns)
  - Turnover + basic transaction cost model (prototype)
  - Robustness: walk-forward / rolling windows
  - Decay analysis: performance degradation across time slices
- Bias controls:
  - look-ahead bias prevention (feature lags and time alignment)
  - survivorship bias acknowledgement and mitigation strategy (prototype limitations allowed, must be documented)
- Out-of-sample protocol and acceptance thresholds for “promoted” factors

6) Multi-agent debate module (from AlphaAgents inspiration)
- Define a debate coordinator agent
- Define a round-robin procedure and a stop condition (consensus rules)
- Define how debate outputs update hypothesis/factor proposals
- Define how debate logs are stored and shown in the UI

7) UI spec (simple, easy)
Implement one UI (Streamlit recommended for speed) with these screens:
- Create run
- Run monitor (agent steps + intermediate artifacts)
- Results dashboard (metrics + plots + factor expression)
- Factor library (browse + compare + export)
- Report viewer (final research note)
Include low-fidelity wireframes (ASCII boxes) and exact UI components.

8) Repository layout (must be explicit)
Provide a concrete directory tree and explain each folder.
Include:
- src package (alpha_miner/)
- agents/
- tools/
- constraints/
- backtesting/
- ui/
- docs/
- configs/
- tests/
- scripts/
- Makefile + pyproject.toml
- .env.example
- CI workflow outline

9) Testing and ADK evaluation suite
- Unit tests for parsers, AST measures, data joins, metrics
- Integration tests for end-to-end run on a tiny universe
- ADK eval: golden trajectories and regression checks
- Determinism strategy (seeding + caching)
- Expected runtime and resource profile for local execution

10) Deployment plan
- Local dev mode
- Containerization
- Deployment to Cloud Run using ADK conventions
- Optional: deployment to Vertex AI Agent Engine
- Secrets management plan (API keys)
- Cost containment for resume project

REFERENCE EXAMPLES (to calibrate scope):

Example hypothesis:
"Stocks with accelerating revenue growth (QoQ) and improving operating margins 
outperform over the next quarter, especially in the Technology sector."

Example factor expression:
factor = Rank(Revenue_Growth_QoQ) * 0.6 + Rank(Operating_Margin_Delta) * 0.4

Example evaluation output:
- Sharpe (2020-2024): 1.2
- IC (mean): 0.04
- Turnover: 35% monthly
- Promoted: Yes (passed IS/OOS threshold)

Example UI workflow:
User clicks "New Run" → enters hypothesis text → agent generates 3 factor candidates 
→ user sees live backtest metrics → user selects best → system generates research note


OUTPUT STRUCTURE:
1. Executive summary (1 page max)
2. For each deliverable:
   - Goal (2 sentences)
   - Design decisions table (3-5 rows: Decision | Rationale | Alternative)
   - Implementation sketch (pseudocode or class signatures)
   - Acceptance criteria (bullet list)
3. Appendices:
   - Mermaid diagrams
   - Code skeletons (20-30 lines each)
   - Sample config files
   
STYLE:
- Use tables for comparisons and specs
- Use code fences for all technical content
- Use Mermaid for all diagrams
- Keep prose tight: 1-2 sentences per paragraph
- Avoid: "As mentioned earlier", "It's worth noting", filler phrases

ONE-SHOT QUALITY CHECKLIST:
After generating, the output should allow a senior engineer to:
□ Understand the system in 10 minutes
□ Start coding within 30 minutes (with clear first file to create)
□ Have <5 fundamental questions before building
□ Estimate implementation time within 25% accuracy
□ Identify integration risks before coding

If any box is unchecked, the spec is insufficient.


