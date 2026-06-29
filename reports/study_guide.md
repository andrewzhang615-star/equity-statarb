# Study Guide — Execution-Aware Equity Reversal

A personal roadmap for owning this project cold before mock interviews. Work top to
bottom. **Understand the pipeline first; read papers afterward** to deepen the "why"
(papers feel abstract until you've seen what we actually did).

For each item, the bar is: *explain it out loud in 2–3 sentences without notes.*
Keep `research_log.md` (the play-by-play) and `reports/Equity_StatArb_Memo.pdf`
(the narrative) open as you go.

---

## Phase 1 — Understand the pipeline (do this before any papers)

Walk the repo in data-flow order. After each module, run the matching script and read its output.

- [ ] **`config.yaml`** — every knob in one place: universe, costs, residual/signal params, IS/OOS split.
- [ ] **`src/data/wrds_pull.py`** — what we pull from CRSP (`dsf` prices/returns, `dsenames` point-in-time names/SIC, `dsedelist` delisting). The pull is "dumb and complete" — no judgment calls.
- [ ] **`src/data/load.py`** — the heart of the rigor:
  - `returns_full` (realized PnL, never masked) vs `eligible` (lagged tradability mask). Be able to explain the **disappearing-loser leak** this separation prevents.
  - delisting imputation (Shumway −30% for missing performance delistings); point-in-time sector panel.
- [ ] **`src/signals/reversal.py`, `residual.py`** — base signal = −(trailing 5-day return), winsorized for the signal only; then market residual, then **leave-one-out sector residual**. Explain *why* residualize and what LOO fixes in small sectors.
- [ ] **`src/portfolio/construct.py`** — the locked candidate: residual reversal → EWMA smoothing (turnover control) → dollar-neutral, capped weights.
- [ ] **`src/backtest/engine.py`** — the single `.shift(1)` look-ahead defense; turnover; PnL computed on `returns_full`. Run `scripts/run_backtest.py`.
- [ ] **`src/backtest/metrics.py`** — Sharpe, breakeven cost, deflated Sharpe.
- [ ] **`src/execution/impact.py`** — square-root impact, participation, capacity. Run `scripts/cost_sensitivity.py` and `scripts/capacity.py`.
- [ ] **Diagnostics & OOS** — run `scripts/robustness.py`, `signal_diagnostics.py`, `pnl_attribution.py`; then re-read `scripts/oos_evaluation.py` and `reports/oos_summary.txt`.

## Phase 2 — The core ideas to master (these get probed)

- [ ] Survivorship/delisting bias and the two-panel design.
- [ ] Look-ahead and the single weight-shift.
- [ ] **Breakeven cost = mean(gross)/turnover** — cost-independent, so it's the clean lens on the decay.
- [ ] Why residualize; leave-one-out.
- [ ] EWMA turnover control — cuts turnover more than gross edge, so net flips positive.
- [ ] Square-root impact + the participation tail → small capacity.
- [ ] **Deflated Sharpe = 0.20** — P(true Sharpe > 0) after 12 trials; pre-registration; the one-shot OOS.
- [ ] Beta-adjusted legs → alpha is short-side, in low-price names (borrow caveat).
- [ ] Economic story: liquidity provision / short-momentum; decay via crowding + decimalization.

## Phase 3 — Papers (only after Phase 1)

Read selectively and tie each back to a specific choice we made.

**High priority**
- [ ] **Lehmann (1990); Lo & MacKinlay (1990)** — the reversal effect itself; Lo–MacKinlay's overreaction-vs-lead-lag decomposition. → our core signal and the liquidity-provision interpretation.
- [ ] **Shumway (1997)** — short; the delisting bias and the −30% fix. → our data-hygiene step.

**Useful context**
- [ ] **Avellaneda & Lee (2010)** — the full residual stat-arb blueprint (PCA factors + Ornstein–Uhlenbeck s-scores). *Our strategy is deliberately simpler* — market/sector residual + plain reversal, not their PCA/OU machinery (a documented "stretch" we chose not to build). Read it to see what the fuller version looks like.
- [ ] **Bailey & López de Prado (2014); Harvey, Liu & Zhu (2016)** — deflated Sharpe and multiple testing. → why we counted trials, froze the spec, and trust the OOS.

**Market impact (our capacity model)**
- [ ] **Almgren et al. (2005), "Direct Estimation of Equity Market Impact"** — the empirical impact paper closest to our η·σ·√(participation) form.
- [ ] **Tóth et al. (2011)** — the square-root law of impact.
- [ ] **Almgren & Chriss (2000)** — optimal-execution framing (impact vs timing risk); useful background, less directly our model.

---

## Editing the memo (source of truth = Markdown)

`reports/memo.md` is the clean source. After editing it, regenerate both outputs:

```bash
cd <repo>
pandoc reports/memo.md -o reports/Equity_StatArb_Memo.docx
pandoc reports/memo.md -o reports/Equity_StatArb_Memo.pdf --pdf-engine=xelatex \
  -V geometry:margin=1in -V mainfont="Helvetica Neue" -V fontsize=11pt
```

If you prefer editing in Word, copy important prose changes back into `reports/memo.md`
afterward so the two don't drift. Keep any changed numbers consistent with
`research_log.md` (and with the README and the interview pitch — all four match today).

## When you're ready

Run the mock interview: have Claude play the interviewer and drill the five questions
(overfitting/leakage, OOS failure, transaction costs, capacity, short-side realism).
You're ready when you can give the 2-minute pitch and defend each number from memory.
