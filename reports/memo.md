---
title: "Execution-Aware Short-Horizon Equity Reversal"
subtitle: "Evidence of Decay, Costs, and Capacity Limits in US Equities (2000–2024)"
author: "Andrew Zhang · Research memo"
date: "June 2026"
---

**Abstract.** I test whether short-horizon cross-sectional reversal in US equities survives a realistic, implementation-aware backtest. Using survivorship-bias-free CRSP daily data (2000–2024) and a deliberately leak-safe pipeline, I build the strategy up in stages — from a raw reversal baseline to a sector-residual signal with turnover control — and stress-test it for transaction costs, capacity, regime dependence, and out-of-sample stability. The signal is genuinely predictive and, after residualization and turnover control, is net-profitable in sample (Sharpe 0.34 after 7 bps costs; break-even cost 11.3 bps). But its edge has decayed steadily over the sample, it is capacity-constrained (~$10–100M), and on a single pre-registered out-of-sample test (2019–2024) it does not survive realistic costs (net Sharpe −0.15 at 7 bps; break-even 4.2 bps). The result is consistent with a crowded, cost-sensitive anomaly that has been largely arbitraged away, and the value of the work is the end-to-end methodology used to reach that conclusion rigorously.

## 1. Research question

Short-horizon reversal — the tendency for recent relative losers to outperform recent relative winners over days to weeks — is a long-documented effect (Lehmann, 1990; Lo and MacKinlay, 1990). The question that matters for a practitioner is not whether it appears in a frictionless backtest, but whether it remains economically meaningful once turnover, transaction costs, and capacity are taken seriously. This memo answers that question with an emphasis on methodology: every result is built to be defensible rather than optimized for a headline Sharpe.

## 2. Data and look-ahead discipline

The sample is CRSP daily data for common shares (share codes 10–11) on NYSE, AMEX, and NASDAQ, January 2000 through December 2024 — 27.2 million name-days across 12,859 securities. CRSP is survivorship-bias-free and includes delisting returns, which matters because a reversal book is drawn toward distressed names. Two data choices do most of the work:

- **Delisting returns.** 44.5% of delisting events have a missing return in CRSP. Following Shumway (1997), missing returns on performance-related delistings are set to −30% rather than zero, so failed names are not quietly recorded as flat exits.
- **Separation of PnL from tradability.** The backtest keeps two distinct panels: a realized-return panel (never masked) for computing PnL, and a lagged eligibility mask (top-1,000 by trailing dollar volume, prior-close price ≥ $5, delisting rows excluded) that only governs which names may receive new weight. This prevents the most common silent leak, in which a position that becomes ineligible disappears from PnL instead of realizing its loss.

Weights are formed at each day's close and shifted one day before earning returns, so the strategy only ever uses information available at decision time. A test suite (28 tests) guards the metrics and the look-ahead and disappearing-loser leaks.

## 3. Methodology

### 3.1 Signal construction

The base signal is the negative of each name's trailing five-day return, winsorized at ±20% for signal formation only (never for realized PnL). I then remove common variation before measuring reversal, in two escalating steps: a market residual (rolling beta to the equal-weighted eligible universe), and a leave-one-out sector residual (demeaning within two-digit SIC industry against eligible peers, excluding the name itself so it cannot anchor its own benchmark). Residualizing targets idiosyncratic reversal rather than sector or market co-movement.

### 3.2 Portfolio and turnover control

Signals map to dollar-neutral, cross-sectionally demeaned weights with a 2% per-name cap. Because daily five-day reversal turns the book over quickly, I apply exponentially-weighted smoothing (half-life of five days) to the signal. This is the single most important implementation choice, trading a small amount of gross edge for a large reduction in turnover. The frozen candidate is: sector-residual five-day reversal, EWMA half-life 5, top-1,000 universe, 7 bps per-turnover cost.

## 4. In-sample results (2000–2018)

Each layer of construction raises the per-trade edge, summarized by the break-even cost (the cost per unit turnover at which net return is zero):

| Variant (in-sample)        | Gross Sharpe | Turnover/day | Break-even |
|----------------------------|:------------:|:------------:|:----------:|
| Raw reversal               | 0.67         | 0.63         | 4.4 bps    |
| + market residual          | 1.00         | 0.63         | 5.1 bps    |
| + sector residual (LOO)    | 1.22         | 0.64         | 5.5 bps    |
| + EWMA turnover control     | 0.90         | 0.23         | 11.3 bps   |

Residualization lifts break-even from 4.4 to 5.5 bps; turnover control then roughly halves turnover and doubles break-even to 11.3 bps, flipping the strategy net-positive at a 7 bps cost (net Sharpe 0.34, ~2.2% annualized). I deliberately stopped tuning here and froze the specification before any out-of-sample evaluation.

## 5. Execution: costs and capacity

Because the strategy's viability rests on implementation, the cost and capacity analysis is treated as central rather than an afterthought. Net Sharpe falls roughly linearly with assumed cost, crossing zero near the 11.3 bps break-even (Figure 1).

![Figure 1. In-sample net Sharpe versus assumed per-turnover cost. Net-positive up to the ~11.3 bps break-even; about 0.08 Sharpe lost per bp.](reports/figures/cost_sensitivity.png){ width=5.6in }

Capacity uses a square-root market-impact model, impact ≈ η·σ·√(trade/ADV) — a standard practitioner approximation (Almgren et al., 2005; Tóth et al., 2011) — with the coefficient η shown across a plausible range rather than assumed. Usable capacity is modest — roughly $10–100M depending on η (Figure 2). The binding constraint is not average liquidity but a thin-name tail: at $1B of capital the largest single-name participation reaches multiples of daily volume. A position cap at a fraction of ADV controls that tail and limits the damage at scale, but does not extend the profitable frontier; it is a risk control, not a capacity unlock.

![Figure 2. Capacity: net Sharpe versus deployed AUM under square-root impact, for three impact coefficients.](reports/figures/capacity.png){ width=5.6in }

## 6. Diagnostics

### 6.1 The edge has decayed

Split into three in-sample sub-periods, break-even falls monotonically: 17.6 bps (2000–2006), 8.0 bps (2007–2012), 6.9 bps (2013–2018). Because break-even is independent of the assumed cost level, this is genuine decay in the per-trade edge — consistent with crowding, decimalization, and tighter markets — not an artifact of the cost assumption. By 2013–2018 the strategy is profitable only if one executes below roughly 5 bps.

### 6.2 Where the alpha is, and what it costs to harvest

After removing market exposure, the alpha is concentrated on the short side (information ratio 1.37 for shorting residual winners versus 0.18 for buying residual losers); the long leg's raw return is mostly market beta. The profitable short positions concentrate in low-price names ($5–25), which are precisely the names that are more expensive and harder to borrow. PnL is otherwise broad — the top ten names account for only about 8% of gross profit, and 2,356 names contribute positively — so the result is not a handful of lucky stocks, though it leans toward technology sectors.

### 6.3 Risk character

Conditioning returns on the market environment shows the edge is concentrated in high-volatility and high-dispersion regimes, where dislocations are larger; the strategy is paid to provide liquidity into those dislocations. Its worst stretches are revealing: the deepest drawdown is a long, slow grind through the calm 2003–2007 bull market, and the worst individual months are momentum extremes in both directions (the 2000 dot-com blow-off and the 2009 rebound), not selloffs per se. The honest characterization is short momentum / long reversion with a liquidity-provision profile: it earns when dislocations mean-revert and suffers when trends persist.

## 7. Out-of-sample test (2019–2024)

The frozen candidate was evaluated once on the sealed 2019–2024 period, with no parameters chosen after looking. The edge does not survive (Table 2, Figure 3).

|                            | Gross Sharpe | Net @7bps | Break-even | Max DD  |
|----------------------------|:------------:|:---------:|:----------:|:-------:|
| In-sample 2000–2018        | 0.90         | +0.34     | 11.3 bps   | −14.0%  |
| Out-of-sample 2019–2024    | 0.23         | −0.15     | 4.2 bps    | −23.1%  |

Break-even continues its decline to 4.2 bps, below the realistic cost line; net Sharpe is positive only at an unrealistic ~2 bps. The largest out-of-sample drawdown coincides with the 2020 COVID crash and rebound — the violent-momentum regime the diagnostics predicted would hurt. A deflated Sharpe ratio on the in-sample result, accounting for the twelve configurations evaluated, gives only a 0.20 probability that the true Sharpe is positive: even the in-sample edge is statistically fragile once selection is accounted for.

![Figure 3. Net equity (log scale, 7 bps), in-sample then out-of-sample. Strong early gains, a long plateau through the decay, and an out-of-sample decline.](reports/figures/oos_equity.png){ width=6in }

## 8. Conclusion

Short-horizon residual reversal was a strong, real effect in the early 2000s that has decayed below tradable levels: by the out-of-sample period it no longer clears realistic costs, its capacity is small, and its remaining alpha sits on the expensive-to-borrow short side. This is the expected life cycle of a well-known, crowded anomaly. The deliverable is the method — a leak-safe pipeline, a transparent construction ladder, an execution and capacity layer, regime and attribution diagnostics, a pre-registered specification, and a single honest out-of-sample test — which is what makes the negative conclusion trustworthy.

### Limitations and future work

- Costs are a flat 7 bps headline with 2–10 bps sensitivity; the impact coefficient is uncertain and shown as a range. Short borrow is not modeled, which matters given the short-side, low-price concentration of the alpha.
- Daily data makes this execution-aware, not intraday; a natural extension is TAQ / limit-order-book data and a true path-dependent participation cap.
- Further extensions: PCA / Ornstein–Uhlenbeck residuals (Avellaneda and Lee, 2010), explicit borrow-cost modeling, and external macro conditioning (VIX, the yield-curve slope, recession dating).

## References

Almgren, R., and Chriss, N. (2000). Optimal execution of portfolio transactions. *Journal of Risk*.

Almgren, R., Thum, C., Hauptmann, E., and Li, H. (2005). Direct estimation of equity market impact. *Risk*.

Avellaneda, M., and Lee, J. (2010). Statistical arbitrage in the US equities market. *Quantitative Finance*.

Bailey, D., and López de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management*.

Harvey, C., Liu, Y., and Zhu, H. (2016). … and the cross-section of expected returns. *Review of Financial Studies*.

Jegadeesh, N., and Titman, S. (1993). Returns to buying winners and selling losers. *Journal of Finance*.

Lehmann, B. (1990). Fads, martingales, and market efficiency. *Quarterly Journal of Economics*.

Lo, A., and MacKinlay, A. C. (1990). When are contrarian profits due to stock market overreaction? *Review of Financial Studies*.

Shumway, T. (1997). The delisting bias in CRSP data. *Journal of Finance*.

Tóth, B., et al. (2011). Anomalous price impact and the critical nature of liquidity in financial markets. *Physical Review X*.
