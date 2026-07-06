# Execution-Aware Short-Horizon Equity Reversal
### Evidence of decay, costs, and capacity limits (US equities, 2000–2024)

![tests](https://github.com/andrewzhang615-star/equity-statarb/actions/workflows/ci.yml/badge.svg)

**Does short-horizon residual reversal in US equities still survive realistic execution?**
This repo answers that with a leak-safe CRSP backtest, building from a raw reversal baseline
up to a sector-residual, turnover-controlled strategy, then stress-testing it for costs,
capacity, and regime dependence — and validating it once on a sealed out-of-sample period.
A second, **pre-registered** phase then tests mentor-suggested refinements — volume
conditioning, an earnings exclusion, and latent-factor (PCA) residualization.

**Headline finding:** the edge was real and strong in the early 2000s but **decayed steadily
and does not survive realistic costs out-of-sample (2019–2024)** — a crowded, cost-sensitive,
low-capacity anomaly with substantial recent decay.

|                              | Gross Sharpe | Net Sharpe @7bps | Breakeven cost |
|------------------------------|:-----------:|:----------------:|:--------------:|
| In-sample (2000–2018)        | 0.90        | **+0.34**        | 11.3 bps       |
| **Out-of-sample (2019–2024)**| **0.23**    | **−0.15**        | **4.2 bps**    |

Deflated Sharpe of the in-sample result (accounting for the 12 configurations tried): **0.20**.

**Phase 2 (pre-registered refinements):** volume conditioning was *rejected by the data*
(in liquid large caps, high-volume moves revert **more** — Campbell–Grossman–Wang 1993); an
**earnings-announcement exclusion** helps (earnings moves drift, per PEAD) but pays for itself
in forced turnover; **15-factor PCA residualization** helps most, cutting volatility by a third.
Combined: in-sample gross Sharpe **1.37** / net@7 **0.28** vs the 0.80 / 0.14 sector baseline on
identical dates — with the **breakeven cost unchanged (~8.8 bps)** and **no gross edge on the
(spent) 2019–2024 window (−0.07)**. Phase 2's deflated Sharpe is **0.83** (vs 0.20 in Phase 1):
selection risk was fixed; regime decay was not.

![Net equity curve — in-sample then out-of-sample](reports/figures/oos_equity.png)

## Why this question
Short-horizon reversal (Lehmann 1990; Lo–MacKinlay 1990) is a textbook stat-arb effect. The
practitioner's question isn't "does it appear in a backtest" — it's whether it survives
**turnover, transaction costs, and capacity** once implemented honestly. This project answers
that with disciplined methodology rather than a curve fit; the goal is a credible research
process, and the negative-but-rigorous result is the point.

## The research arc
- **Leak-safe data layer** — survivorship-bias-free CRSP daily via WRDS; delisting returns
  imputed (Shumway −30% for missing performance delistings); point-in-time universe; and a
  strict split between the *realized-return* panel and the *tradability* mask, so a losing
  position can never silently vanish from PnL.
- **Signal ladder** — raw reversal → market-residual → **leave-one-out sector-residual**;
  each step lifts the per-trade edge (breakeven 4.4 → 5.1 → 5.5 bps).
- **Turnover control** — EWMA signal smoothing roughly halves turnover and flips the
  in-sample net Sharpe positive (breakeven 5.5 → 11.3 bps).
- **Execution layer** — a cost-sensitivity curve and a square-root market-impact capacity
  analysis (usable capacity ~$10–100M; a thin-name participation tail is the binding
  constraint, partly controlled by an ADV position cap).
- **Diagnostics** — subperiod decay; beta-adjusted legs (the alpha is **short-side**,
  concentrated in **low-price** names → a borrow caveat); regime conditioning (the strategy
  behaves like **short-momentum / liquidity provision** — earns in high-dispersion markets,
  loses when trends persist); broad PnL (top-10 names ≈ 8%).
- **One-shot OOS** — the frozen candidate evaluated exactly once on 2019–2024.
- **Phase 2: pre-registered refinements** — each layer's hypothesis, construction, and
  stop-rule committed to this repo *before* its data or results existed. Volume conditioning:
  diagnostic failed → no variant built. Earnings exclusion: point-in-time Compustat–CRSP
  linking; earnings-window moves have *inverted* reversal IC (−0.0105 vs +0.0125 clean).
  PCA (k=15, rolling 252d SVD): the largest gain, via risk reduction. The combined candidate
  is re-checked on 2019–2024 explicitly labeled as a **spent** holdout, not fresh evidence.

## Key figures
`reports/figures/oos_equity.png` (net equity, IS │ OOS) · `rolling_breakeven.png` (the decay) ·
`decile_monotonicity.png` · `earnings_eventtime.png` (reversion vs PEAD drift) · `pca_scree.png` ·
`cost_sensitivity.png` · `capacity.png` · `participation_cap.png`.
Full write-up: **`reports/Equity_StatArb_Memo.pdf`** (regenerate the figure set: `python scripts/paper_figures.py`).

## Reproduce
```bash
pip install -r requirements.txt
# 1) pull CRSP (needs a WRDS account; first call prompts for login)
python -c "from src.data.wrds_pull import pull_crsp_daily; pull_crsp_daily()"
# 2) build leak-safe panels
python -c "from src.data.load import build_panel, build_sector_panel; build_panel(); build_sector_panel()"
# 2b) earnings dates for Phase 2 (Compustat rdq + CCM link)
python -c "from src.data.earnings import pull_earnings_dates; pull_earnings_dates()"
# 3) analyses (each writes a table and/or a figure)
python scripts/run_backtest.py       # raw vs market-residual vs sector-residual
python scripts/cost_sensitivity.py   # net Sharpe vs cost
python scripts/capacity.py           # net Sharpe vs AUM (market impact)
python scripts/robustness.py         # subperiod decay + beta-adjusted legs
python scripts/oos_evaluation.py     # the one-shot OOS
# 4) Phase 2 (pre-registered refinements)
python scripts/volume_diagnostic.py  # 2A: reversal by abnormal-volume tercile (rejected)
python scripts/earnings_diagnostic.py # 2B: earnings-window vs clean moves
python scripts/earnings_exclusion.py # 2B: exclusion candidate vs baseline
python scripts/pca_comparison.py     # 2C: PCA(k=15) vs sector residual
python scripts/final_combined.py     # 2x2 grid -> combined candidate
python scripts/phase2_endgame.py     # spent-holdout check + Phase 2 deflated Sharpe
pytest -q                            # 37 tests (incl. look-ahead + leak guards)
```

## Repo map
```
config.yaml          single source of truth (universe, costs, params, OOS split)
research_log.md      full dated decision journal + experiment ledger
src/
  data/    wrds_pull (raw CRSP) · load (leak-safe panels) · earnings (rdq + point-in-time CCM links)
  signals/ reversal · residual (market + LOO sector) · volume (abnormal volume) · pca (rolling factor residuals)
  portfolio/ construct (locked candidate)
  backtest/ engine (look-ahead-safe) · metrics (Sharpe/IR/DD/turnover/deflated Sharpe)
  execution/ impact (square-root impact, participation, capacity)
scripts/   one script per analysis (see Reproduce)
tests/     metric, pipeline-leak, signal, and impact tests
reports/   memo + figures
```

## Honest limitations
Flat 7 bps cost headline (2–10 bps sensitivity reported); square-root impact coefficient is
uncertain (a range is shown); short borrow is not modeled (relevant since the alpha is
short-side); daily data, so this is *execution-aware*, not intraday/limit-order-book. The 2019–2024
window is spent after Phase 1; the Phase 2 candidate's genuinely fresh holdout (2025+) awaits
the next CRSP vintage.

## References
Lehmann (1990) · Lo & MacKinlay (1990) · Avellaneda & Lee (2010) · Jegadeesh & Titman (1993) ·
Harvey, Liu & Zhu (2016) · Bailey & López de Prado (2014) · Almgren & Chriss (2000) ·
Bernard & Thomas (1989) · Campbell, Grossman & Wang (1993) · Llorente et al. (2002).
