# Research Log

A running journal of decisions, experiments, and dead ends. The point is to make
the *process* legible - for the memo and for interviews. Every signal variant
tested gets a line here (this is also what feeds the trial count for the
deflated Sharpe).

---

## 2026-06-27 - Project scoping

**Decisions**
- Topic: **execution-aware short-horizon residual reversal on liquid US
  equities**.
- Core research question: does residual short-term reversal survive realistic
  turnover, transaction costs, and capacity constraints?
- Audience: both buy-side QR and HFT/MM -> rigorous empirical signal research
  plus practical execution/cost discipline.
- Timeline: ~2-3 week intensive sprint. Deliverable: research memo + this repo.
- Data: **CRSP daily via WRDS** (survivorship-bias-free, delisting returns,
  point-in-time share/exchange codes).
- Universe: top-1000 by trailing 60d dollar volume, >= $5 price, common shares,
  NYSE/AMEX/NASDAQ. Membership lagged 1 day (no look-ahead).
- OOS protocol: 2000-2018 research, **2019-2024 held out** as a true test set.

**MVP order**
1. Pull CRSP and build a clean returns panel.
2. Implement raw short-horizon reversal.
3. Implement residualized reversal.
4. Add linear costs, turnover, and cost sensitivity.
5. Add a simple capacity curve.
6. Run IS/OOS and parameter robustness.

**Stretch goals**
- PCA residualization and Avellaneda-Lee OU s-scores.
- Longer-horizon momentum tilt.
- Deflated Sharpe / more formal multiple-testing adjustment.
- More detailed Almgren-Chriss-style impact model.

**Reading (skim, priority order)**
1. Lehmann (1990) / Lo & MacKinlay (1990) - short-horizon reversal
2. Avellaneda & Lee (2010) - residual stat-arb blueprint
3. Almgren & Chriss (2000) - execution and impact framing
4. Harvey-Liu-Zhu (2016) + deflated Sharpe (Bailey & Lopez de Prado 2014) - rigor
5. Jegadeesh & Titman (1993) - momentum stretch goal

**Next**
- [ ] Pull CRSP daily via WRDS (`src/data/wrds_pull.py`) - *Andrew's action item*.
- [ ] Build + sanity-check returns panel (`src/data/load.py`); EDA notebook.
- [ ] Implement raw reversal baseline before residual/PCA work.
- [ ] Gate: confirm data is clean & look-ahead-free before optimizing signals.

---

## 2026-06-27 - Data-hygiene foundation (pre-signal correctness gate)

Locked before any signal research (reviewed across two models):
- **Two-panel separation.** `returns_full` (PnL) is NEVER masked by price/liquidity/
  eligibility. A separate `eligible` boolean mask (price >= $5, top-N ADV) is used ONLY to
  form new target weights. Filters decide what we may trade, not which returns exist.
- **Delisting returns realized, not erased.** Missing *performance* delisting returns
  (dlstcd 500, 520-584) are imputed (default -0.30; Shumway 1997), not filled with 0.
  Mergers/other codes keep their actual dlret (missing -> 0). Imputation runs in
  `build_panel()` from config; the raw pull stays raw.
- **Delisting-date attachment.** If a delisting date has no matching price row, the loss is
  compounded into that permno's last available date (no silent drop).
- **Sensitivity:** main table {0.0, -0.30, -0.55}; -1.00 is a separate bankruptcy-only stress.
- **NaN (non-delisting) returns:** treated as 0 while held (carry), applied only AFTER
  delisting rows are set.
- **Pull fields added:** permco (dedupe dual-class later), askhi/bidlo (Corwin-Schultz spreads
  later), point-in-time siccd (NOT header hsiccd), dlret/dlstcd/dlstdt.
- **Eligibility lag:** computed contemporaneously; the engine's weight `.shift(1)` is the single
  sufficient look-ahead lag (no double-lag). *[Flagged for the other model's review.]*

Tests (`tests/test_pipeline.py`): imputation by code; delisting attachment (matched + unmatched);
engine leak-closure (held delisting loser realizes its loss + exit turnover); eligibility filters.

---

## 2026-06-27 - Hardening (post second-model review)

- **Delisting rows forced ineligible.** `apply_delisting_returns` sets a `delist_event` flag and
  `build_eligibility` ANDs it out, so a reversal signal can't try to buy a name on the day it
  delists. Side benefit: a held name's exit turnover now lands on the delisting day, not a day late.
- **Unmatched delistings attach to the last date ON OR BEFORE `dlstdt`** (not the permno's global
  max date), so dirty rows after a delisting can't misplace the loss.
- **`build_panel` asserts unique `(permno, date)`** before pivoting; an overlapping dsenames join
  now fails loudly instead of silently averaging returns. (If it fires on the real pull, dedup by
  latest `nameendt`.)

Tests now 12 passing. Cleared to implement the raw reversal baseline.

---

## 2026-06-27 - Data gate (EDA on the real CRSP pull)

Raw: 27.2M daily rows, 2000-01-03 .. 2024-12-31, 12,859 permnos, **0 duplicate (permno, date)**.
Missingness < 0.05%. 23,657 dsedelist rows; **44.5% missing dlret** (481 missing+performance -> imputed -0.30).

**Bug found & fixed:** dsedelist includes `dlstcd=100` ("still trading"); 3,804 such rows matched a trading
day and were wrongly flagged as delistings. Now filter `dlstcd >= 200`. Panels rebuilt; 13 tests pass.

**Verification (twin-leak closed):** returns_full carries delisting losses — 16,406 cells <= -30%,
3,143 <= -50%, min -100%. Imputed performance delistings land ~-0.30 on their terminal date (spot-checked).

**Open for signal phase:** extreme returns (max +3,972%, a sub-$1 name spiking to $9.77). Reversal shorts
winners and the same-day $5 filter lets a just-spiked name in -> (a) winsorize returns before forming the
signal and (b) use a persistent/lagged price filter, not contemporaneous price.

Coverage: 6,289 days x ~971 tradable names/day (stable). **Data gate: PASS.**

---

## 2026-06-27 - Result: raw 5-day reversal (IN-SAMPLE 2000-2018)

Dollar-neutral, ~969 names/day, signal winsorized +/-20%, eligibility = prior-close >= $5, 7 bps/unit turnover.

- **Gross Sharpe 0.67** (ann 6.7%, vol 10.5%, maxDD -14%): a real but modest reversal effect, in
  line with Lehmann / Lo-MacKinlay.
- **Net Sharpe -0.39** (ann -4.5%, maxDD -69%): costs destroy it.
- Turnover 0.63/day (sum|dw|) -> **breakeven cost 4.4 bps per unit turnover**. Realistic all-in costs
  exceed that, so **raw short-horizon reversal does NOT survive costs** -- exactly the project's question.
- Gross Sharpe ~0.67 (not implausibly high) is reassurance the pipeline isn't leaking.

Next (MVP): does residualization (market, then sector) raise gross Sharpe and/or cut turnover enough to
clear breakeven? Plus a lower-turnover variant (longer lookback / holding / signal threshold). Holdout sealed.

---

## 2026-06-27 - Market-residual reversal vs raw (IS 2000-2018)

Market residualization (`resid = ret - rolling-beta * mkt`, mkt = EW mean of the **eligible/tradable**
universe) lifted **gross** Sharpe 0.67 -> 1.00: vol fell 10.5% -> 8.0% AND gross ann return rose
6.7% -> 8.0%. Because the **mean edge** rose (not just vol), **breakeven improved 4.4 -> 5.1 bps/turn**.
Net is still negative at 7 bps (-0.39), so it does not yet survive realistic costs -- but the gap narrowed.

Note: an earlier run used a full-CRSP (microcap-tilted) market proxy and showed gross 0.89 / breakeven
4.6 with the edge ~flat. Switching to the *eligible-universe* proxy (the universe we actually trade) both
fixed a text/code mismatch and gave a cleaner residual -> bigger edge. Lesson stands that **breakeven
(= mean gross / turnover) is the cost-relevant metric, not vol/Sharpe**; remaining levers are sector
neutralization (mean edge) and turnover reduction (no-trade bands, smoothing, longer holding).
(Net maxDD ~-70% is just the bleed of a net-losing strategy, not a real risk stat.)

---

## Experiment ledger

| Date | Signal / variant | Params | IS Sharpe | OOS Sharpe | Notes |
|------|------------------|--------|-----------|------------|-------|
| 2026-06-27 | raw 5d reversal, $-neutral | lb=5, winsor +/-20%, prior-close $5, 7bps | 0.67 gross / -0.39 net | sealed | turnover 0.63/day; **breakeven 4.4bps**; dies on costs |
| 2026-06-27 | market-residual 5d reversal | + 60d rolling beta vs EW eligible-universe market | 1.00 gross / -0.39 net | sealed | vol→8.0%; **breakeven 5.1bps**; closer, still dies at 7bps |
