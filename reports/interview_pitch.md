# Interview pitch — Execution-Aware Equity Reversal

## 2-minute version

I tested whether a classic stat-arb signal — short-horizon reversal in US equities — still survives realistic implementation, using survivorship-bias-free CRSP daily data from 2000 to 2024.

The backtest is deliberately leak-safe: realized returns and tradability are kept in separate panels so a losing position can't silently vanish, delisting returns are imputed (Shumway), and weights are shifted one day so nothing uses future information. I built the signal up in stages — raw reversal, then residualizing out market and then sector co-movement (leave-one-out within industry), then EWMA smoothing to control turnover. In sample that's net-positive after costs: Sharpe 0.34 at 7 bps, break-even cost 11.3 bps.

But I treated cost and capacity as first-class, not an afterthought. Capacity is only about \$10–100M — the binding constraint is a thin-name tail, not average liquidity — and the alpha is concentrated on the short side, in low-price names that are expensive to borrow.

The headline finding is decay. Break-even fell from about 18 bps in the early 2000s to under 7 by 2013–2018, and on a single pre-registered out-of-sample test (2019–2024) the strategy doesn't clear realistic costs — break-even 4.2 bps, net Sharpe −0.15, and a deflated Sharpe of 0.20. So the honest conclusion is that this is a crowded, cost-sensitive anomaly that has been largely arbitraged away.

What I'm most proud of is the process: the leak-safe pipeline, the construction ladder, the cost and capacity layer, and the discipline of freezing the spec and testing out-of-sample exactly once. That's what makes the negative result trustworthy.

## 10-minute version (walkthrough)

1. **Motivation** — reversal is textbook (Lehmann; Lo–MacKinlay); the real question is whether it survives turnover, costs, and capacity. Goal: a defensible process, not a headline Sharpe.
2. **Data & leak-safety** — CRSP, survivorship-free; the two panels (realized PnL vs lagged eligibility); delisting imputation; the weight-shift; 28 tests including a "disappearing-loser" guard.
3. **Construction ladder** — raw → market-residual → sector-residual (LOO). Show break-even rising 4.4 → 5.1 → 5.5 bps: residualizing isolates idiosyncratic reversal.
4. **Turnover control** — EWMA hl=5 halves turnover, doubles break-even to 11.3 bps, flips net-positive in sample. The key implementation lever.
5. **Cost & capacity** — cost-sensitivity curve (Figure 1); square-root impact with η as a range (Figure 2); capacity ~\$10–100M; the thin-name tail and the position cap as a risk control.
6. **Diagnostics** — decay across sub-periods; beta-adjusted legs (alpha is short-side, low-price → borrow caveat); regime conditioning → short-momentum / liquidity-provision profile; broad PnL.
7. **Out-of-sample** — one shot on 2019–2024: doesn't survive (break-even 4.2 bps, net −0.15); deflated Sharpe 0.20; the 2020 drawdown matches the predicted risk.
8. **Conclusion** — expected life cycle of a crowded anomaly; the method is the deliverable.

## Questions they'll ask (and answers)

- **"How do you know it isn't overfit or leaking?"** Separate PnL/eligibility panels, one-day weight shift, a test suite with explicit look-ahead and disappearing-loser guards, a spec frozen before the holdout, a single OOS run, and a deflated Sharpe (0.20) that prices in the 12 configs I tried.
- **"Why does it decay?"** Crowding, 2001 decimalization, and tighter electronic markets competing away the liquidity-provision premium. Break-even is independent of the assumed cost, so the falling break-even is genuine edge decay, not a cost assumption.
- **"What's the capacity?"** ~\$10–100M depending on the impact coefficient. The binding constraint is a thin-name tail (single-name trades exceed daily volume at \$1B), which a per-name ADV cap controls — but capping limits downside, it doesn't add capacity.
- **"Where's the alpha, and is the short side realistic?"** After removing market beta, the alpha is on the short side (IR 1.37 vs 0.18 long), concentrated in low-price names — so borrow cost and squeeze risk (e.g., 2021 meme stocks) are real frictions I don't fully model. An honest caveat.
- **"Why is a negative result a good project?"** Because it's a *trustworthy* one. I built the full machinery, stayed disciplined, and showed *why* a famous strategy stopped working — which is more useful, and harder, than presenting a fragile high-Sharpe curve.
- **"What would you do next?"** Intraday TAQ / limit-order-book data with a true path-dependent participation cap; explicit borrow-cost modeling; PCA/Ornstein–Uhlenbeck residuals (Avellaneda–Lee); and external macro conditioning (VIX, yield-curve slope, recessions).
