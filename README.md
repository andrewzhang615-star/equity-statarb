# Equity Statistical Arbitrage: Execution-Aware Residual Reversal

A research project testing whether short-horizon reversal in liquid US equities
survives a stricter, implementation-aware backtest. The core question is:

> **Does residual short-term reversal remain economically meaningful after
> realistic turnover, transaction costs, and capacity constraints?**

The project is intentionally scoped for a 2-3 week recruiting sprint. The goal is
not to find an overfit high-Sharpe backtest; it is to build a clean,
reproducible research repo that shows data discipline, honest evaluation, and
practical trading realism.

## MVP scope

The first complete version should include:

1. **CRSP daily data pipeline:** survivorship-bias-free US equities via WRDS,
   including delisting returns and point-in-time share/exchange filters.
2. **Liquid universe construction:** top names by lagged trailing dollar volume,
   with price and share-code filters applied without look-ahead.
3. **Raw short-horizon reversal baseline:** buy recent losers and sell recent
   winners in a dollar-neutral portfolio.
4. **Residualized reversal baseline:** remove common market/factor exposure,
   then test reversal on residual returns.
5. **Execution-aware evaluation:** turnover, commissions, slippage, cost
   sensitivity, and a simple capacity curve.
6. **Robustness:** in-sample vs. true out-of-sample, parameter sensitivity, and
   drawdown/regime diagnostics.

## Stretch goals

Only add these after the MVP works end-to-end:

- PCA residualization and Avellaneda-Lee-style OU s-scores.
- A longer-horizon momentum tilt.
- Formal multiple-testing adjustments / deflated Sharpe.
- More detailed market-impact modeling inspired by Almgren-Chriss.

## Data

Survivorship-bias-free **CRSP daily** data via WRDS (includes delisting returns and
point-in-time share/exchange codes). See `src/data/wrds_pull.py`.

> **Setup (one-time):** create a WRDS account, then `pip install wrds`. The first call to
> `wrds.Connection()` prompts for your username/password and offers to store a `~/.pgpass`
> file so future pulls are passwordless. Raw data is cached under `data/raw/` (git-ignored).

## Repository structure

```
config.yaml          Single source of truth: universe, dates, signal & cost params, seed
research_log.md       Running research journal (decisions, experiments, dead ends)
src/
  config.py           Loads config.yaml
  data/
    wrds_pull.py      Pull survivorship-free CRSP daily data from WRDS
    load.py           Clean + build the (dates x permno) returns panel; liquidity universe
  signals/
    reversal.py       Raw short-horizon reversal baseline                       [TODO]
    residual.py       Residualized reversal; PCA/OU as stretch                  [TODO]
    momentum.py       Momentum tilt stretch goal                                [TODO]
  portfolio/
    construct.py      Signal -> weights, blending, neutralization               [TODO]
    costs.py          Linear + impact transaction-cost models                   [TODO]
  backtest/
    engine.py         Vectorized cross-sectional backtest (look-ahead-safe)
    metrics.py        Sharpe, IR, drawdown, Calmar, turnover, deflated Sharpe
  execution/
    impact.py         Simple capacity curve; square-root impact as stretch       [TODO]
notebooks/            01_eda, 02_baseline, 03_signal_research, 04_results
scripts/run_backtest.py   End-to-end orchestration
tests/                Metric + look-ahead-guard tests
reports/              Figures + the research memo (memo.md)
```

## Quickstart

```bash
pip install -r requirements.txt
python -c "from src.data.wrds_pull import pull_crsp_daily; pull_crsp_daily()"   # your WRDS login
python -c "from src.data.load import build_panel; build_panel()"
pytest -q
```

## Current Status

Phase 0-1 (scaffold + data). The immediate next gate is to pull CRSP data,
build the returns panel, and run the raw reversal baseline. Signal modules are
stubs to be implemented in MVP order. See `research_log.md` for the running
plan and experiment ledger.

## References

- Lehmann (1990); Lo & MacKinlay (1990) - short-horizon reversal
- Avellaneda & Lee (2010), *Statistical Arbitrage in the US Equities Market*
- Jegadeesh & Titman (1993), *Returns to Buying Winners and Selling Losers*
- Harvey, Liu & Zhu (2016); Bailey & Lopez de Prado (2014) - multiple testing / deflated Sharpe
- Almgren & Chriss (2000), *Optimal Execution of Portfolio Transactions*
