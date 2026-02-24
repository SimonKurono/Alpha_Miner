# Alpha Miner

An agentic framework for discovering, evaluating, and refining quantitative alpha signals. Built with the **Google Agent Development Kit (ADK)** and **Gemini 2.x** models.

Alpha Miner automates the quant research workflow — from raw data ingestion through hypothesis generation, factor construction, backtesting, and research-note writing — using specialized AI agents that collaborate, debate, and iterate.

## Architecture

The system is organized as a multi-agent pipeline with five core stages:

1. **Data Ingestion** — Parallel retrieval of market data (prices, volume, returns) and unstructured text (SEC 10-K/10-Q filings, news/sentiment).
2. **Hypothesis Generation** — LLM-driven generation of explicit factor theses, conditioned on risk tolerance and grounded in ingested data.
3. **Factor Construction** — Translation of hypotheses into formulaic factor expressions via a custom DSL, with AST-based originality and complexity scoring.
4. **Evaluation Loop** — Backtesting with walk-forward validation, computing Sharpe ratio, Information Coefficient, turnover, and decay analysis.
5. **Report Generation** — Automated research-note writing summarizing promoted factors and their evidence.

### Agent Tree

| Agent | Type | Responsibility |
|---|---|---|
| Root Orchestrator | `SequentialAgent` | Coordinates the end-to-end pipeline |
| Data Ingestion Agent | `ParallelAgent` | SEC EDGAR + market data retrieval with caching |
| Hypothesis Generation Agent | `LlmAgent` | Generates factor theses with risk-tolerance conditioning |
| Factor Construction Agent | `SequentialAgent` | DSL parsing, AST validation, code generation, originality/complexity scoring |
| Evaluation Agent | `LoopAgent` | Backtest execution, metrics computation, promotion decisions |
| Report Agent | `LlmAgent` | Research note generation |

### Factor DSL

Factors are expressed in a constrained domain-specific language supporting:
- **Operations:** `Rank()`, `Normalize()`, `WinsorizedSum()`, `Delay()`, `Sum()`
- **Arithmetic:** `+`, `-`, `*`, `/`
- **Fields:** `close`, `volume`, `market_cap`, `returns_1d`, `returns_5d`

Example:
```
Rank(close / Delay(close, 5)) * 0.6 + Rank(Normalize(volume)) * 0.4
```

Expressions are parsed into an AST and scored for **complexity** (`node_count + 2*depth + variety_bonus`) and **originality** (Levenshtein distance on AST serialization vs. existing factor library).

## Project Structure

```
src/alpha_miner/
├── agents/
│   ├── data_ingestion/       # SEC EDGAR + market data retrieval
│   ├── hypothesis_generation/# LLM-driven factor thesis generation
│   └── factor_construction/  # DSL → AST → code pipeline
├── tools/
│   └── factors/              # DSL parser, AST nodes, validators, scoring
└── pipelines/                # CLI entrypoints for each feature

configs/                      # YAML configs per feature stage
docs/
├── feature_plans/            # Design docs for each feature
├── runbooks/                 # Operational guides
└── validation/               # Smoke-test and regression reports
tests/                        # Unit + integration tests
other_agents/                 # Reference ADK agent examples (blog, currency, e-commerce, etc.)
```

## Current Status

| Feature | Status | Notes |
|---|---|---|
| Feature 1 — Data Ingestion | Complete | SEC EDGAR + market data with caching layer |
| Feature 2 — Hypothesis Generation | Active (temporary gate) | `text_coverage_min` temporarily lowered to `0.10` |
| Feature 3 — Factor Construction | MVP complete | DSL parser, AST validation, scoring, CLI all operational |
| Feature 4 — Backtesting Loop | Not started | Next milestone |

**Test suite:** 41 passing | **Feature 3 smoke:** 10 candidates generated, 3 accepted

## Setup

1. **Clone and create a virtual environment:**
   ```bash
   git clone <repo-url> && cd Google_Agents
   python -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables** in a `.env` file:
   ```env
   GOOGLE_API_KEY=your_api_key_here
   ```

## Usage

Run individual pipeline stages via CLI:

```bash
# Feature 2 — Hypothesis generation
python -m alpha_miner.pipelines.feature2_hypothesis_cli

# Feature 3 — Factor construction
python -m alpha_miner.pipelines.feature3_factor_cli
```

Run the test suite:

```bash
pytest tests/
```

## Data Sources

| Source | Data | Notes |
|---|---|---|
| SEC EDGAR | 10-K/10-Q filings, XBRL fundamentals | Rate-limited to 10 req/s |
| yfinance | Price, volume, returns | Free; abstracted behind data-provider interface |
| FRED API | Macro series | Optional |
| GDELT | News text / sentiment | Optional |

## Research Grounding

This project draws on:

- **AlphaAgents** (arXiv:2508.11152) — Specialized analyst-role agents, internal debate/consensus, risk-tolerance conditioning.
- **AlphaAgent** (arXiv:2502.16789) — Originality enforcement via AST similarity, hypothesis-factor alignment scoring, complexity control.
- **Google ADK** — Multi-agent orchestration with `SequentialAgent`, `ParallelAgent`, `LoopAgent`, tool contracts, and session state management.

## Key Documentation

- [`blueprint.md`](blueprint.md) — Full technical specification and design decisions
- [`context.md`](context.md) — Living project state tracker (current session, blockers, next actions)
- [`docs/feature_plans/`](docs/feature_plans/) — Per-feature design documents
- [`docs/runbooks/`](docs/runbooks/) — Operational guides for running each feature
- [`docs/validation/`](docs/validation/) — Smoke-test and regression reports

## Disclaimer

Alpha Miner is an educational and research tool. It does not constitute financial advice. All backtesting results are hypothetical and subject to known limitations including survivorship bias and look-ahead bias (documented and mitigated where possible).
