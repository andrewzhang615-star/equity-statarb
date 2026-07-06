---
title: "Execution-Aware Short-Horizon Equity Reversal"
subtitle: "Evidence of Decay, Costs, and Capacity Limits in US Equities (2000--2024)"
author: "Andrew Zhang"
documentclass: article
fontsize: 12pt
geometry: "margin=1.25in"
fig-pos: H
header-includes:
  - \usepackage{float}
  - \floatplacement{figure}{H}
abstract: |
  This paper asks whether short-horizon cross-sectional reversal in US equities remains exploitable after implementation frictions. Using survivorship-bias-free CRSP daily data for 2000--2024, I build a leak-safe backtest from raw reversal to a sector-residual, turnover-controlled strategy, then evaluate it under transaction costs, capacity constraints, regime diagnostics, and a single out-of-sample test. The signal is predictive and net-profitable in sample after costs (net Sharpe 0.34 at 7 bps; break-even 11.3 bps), but its edge declines steadily, capacity is limited (roughly \$10--100M), and the pre-registered 2019--2024 holdout is not profitable after realistic costs (net Sharpe -0.15; break-even 4.2 bps). The evidence is consistent with substantial decay in a crowded, cost-sensitive anomaly. A second, pre-registered phase (volume conditioning, earnings-announcement exclusion, and latent-factor residualization) raises in-sample gross Sharpe to 1.37 but does not materially improve break-even cost or recent-period viability. The contribution is methodological: a transparent framework for assessing whether a documented anomaly remains economically viable after costs.
---

# 1 Research question

Short-horizon reversal, the tendency for recent relative losers to outperform recent relative winners over days to weeks, is well documented (Lehmann, 1990; Lo and MacKinlay, 1990). For a practitioner, the question is not whether the effect appears in a frictionless backtest but whether it remains economically meaningful after turnover, transaction costs, and capacity. This paper addresses that question for liquid US equities, emphasizing methodological transparency rather than in-sample maximization.

# 2 Data and look-ahead discipline

The sample consists of CRSP daily data for common shares (share codes 10--11) listed on the NYSE, AMEX, and NASDAQ from January 2000 through December 2024: 27.2 million name-days across 12,859 securities. CRSP is survivorship-bias-free and records delisting returns, which matters because reversal strategies tend to accumulate distressed names. Two data-construction choices are central.

- **Delisting returns.** Delisting returns are missing for 44.5% of delisting events. Following Shumway (1997), missing returns on performance-related delistings are set to -30% rather than zero, so that failed firms are not recorded as costless exits.
- **Separation of return measurement from tradability.** The backtest maintains two distinct panels: a realized-return panel, used to compute PnL and never masked, and a lagged eligibility mask (the top 1,000 names by trailing dollar volume, with prior-close price $\geq$ \$5 and delisting rows excluded) that governs only which names may receive new weight. This separation prevents a common contamination in which a position that loses eligibility is dropped from the return calculation rather than realizing its terminal loss.

Weights are formed at each day's close and lagged one day before they earn returns, so that the strategy conditions only on information available at the decision time. A suite of 37 unit tests guards the performance metrics and the look-ahead and disappearing-position safeguards.

# 3 Methodology

## 3.1 Signal construction

The base signal is the negative of each name's trailing five-day return, winsorized at $\pm$20% for signal construction only and never for realized PnL. Common variation is removed before reversal is measured. I first estimate a market residual from a rolling regression on the equal-weighted eligible universe, then form a leave-one-out sector residual by demeaning within two-digit SIC industry while excluding the name itself. Residualization isolates idiosyncratic reversal from sector- and market-level co-movement.

## 3.2 Portfolio and turnover control

Signals are mapped to dollar-neutral, cross-sectionally demeaned weights subject to a 2% per-name cap. Because daily five-day reversal is high-turnover, the signal is smoothed with a five-day-half-life EWMA. Smoothing sacrifices some gross signal strength but sharply lowers turnover, which proves decisive for net performance. The fixed specification is a sector-residual five-day reversal signal with EWMA half-life five, a top-1,000 universe, and a 7 bps per-turnover cost.

# 4 In-sample results (2000--2018)

Each stage of construction raises the per-trade edge, summarized by the break-even cost, defined as the cost per unit turnover at which net return is zero.

**Table 1.** Construction ladder, in-sample 2000--2018.

| Variant (in-sample)        | Gross Sharpe | Turnover/day | Break-even |
|----------------------------|:------------:|:------------:|:----------:|
| Raw reversal               | 0.67         | 0.63         | 4.4 bps    |
| + market residual          | 1.00         | 0.63         | 5.1 bps    |
| + sector residual (LOO)    | 1.22         | 0.64         | 5.5 bps    |
| + EWMA turnover control    | 0.90         | 0.23         | 11.3 bps   |

The signal is broadly monotonic across the cross-section (Figure 1): forward residual returns generally rise from the strongest recent winners (decile 1) to the strongest recent losers (decile 10), and the short side contributes the largest effect, anticipating the short-side concentration documented in Section 6.2.

![Mean next-day residual return by reversal-signal decile, in-sample (2000--2018). Decile 1 contains the strongest recent winners (candidate shorts), while decile 10 contains the strongest recent losers (candidate longs).](reports/figures/decile_monotonicity.png){ width=5.4in }

Residualization raises break-even from 4.4 to 5.5 bps; turnover control then approximately halves turnover and roughly doubles break-even, to 11.3 bps, rendering the strategy net-profitable at a 7 bps cost (net Sharpe 0.34, approximately 2.2% annualized). The specification is frozen at this point, prior to any out-of-sample evaluation.

# 5 Execution: costs and capacity

Because the strategy's viability depends on implementation, the cost and capacity analysis is central to what follows. Net Sharpe declines approximately linearly in the assumed cost, reaching zero near the 11.3 bps break-even (Figure 2).

![In-sample net Sharpe as a function of the assumed per-turnover cost. The strategy is net-positive up to the 11.3 bps break-even, losing approximately 0.08 in Sharpe per basis point.](reports/figures/cost_sensitivity.png){ width=5.4in }

Capacity is assessed under a square-root market-impact model, $\text{impact} \approx \eta \cdot \sigma \cdot \sqrt{\text{trade}/\text{ADV}}$ (Almgren et al., 2005; Tóth et al., 2011), with $\eta$ reported across a plausible range. Usable capacity is modest, roughly \$10--100M depending on $\eta$ (Figure 3). The binding constraint is a thin-name tail rather than average liquidity: at \$1B, the largest single-name participation reaches several multiples of daily volume. An ADV position cap controls this tail but does not extend the profitable frontier; it is a risk control, not new capacity.

![Net Sharpe as a function of deployed AUM under a square-root market-impact model, for three impact coefficients.](reports/figures/capacity.png){ width=5.4in }

# 6 Diagnostics

## 6.1 The edge has decayed

Break-even declines monotonically across in-sample sub-periods: 17.6 bps over 2000--2006, 8.0 bps over 2007--2012, and 6.9 bps over 2013--2018. Because break-even is invariant to the assumed cost level, this reflects genuine decay in per-trade edge, consistent with crowding, decimalization, and tighter markets. By 2013--2018 the strategy is profitable only below roughly 5 bps. Figure 4 traces the same decay continuously: rolling three-year break-even falls from about 50 bps in the earliest windows to below 10 bps by the mid-2000s, then oscillates around the assumed cost line before ending below it.

![Rolling three-year break-even cost of the Phase 1 candidate. The dashed horizontal line marks the 7 bps assumed cost; the dotted vertical line marks the start of the previously examined Phase 1 out-of-sample window.](reports/figures/rolling_breakeven.png){ width=5.4in }

## 6.2 Where the alpha is, and what it costs to harvest

After market exposure is removed, alpha is concentrated on the short side: the information ratio is 1.37 for shorting residual winners versus 0.18 for buying residual losers, while the long leg's raw return is largely market beta. The profitable shorts are concentrated in low-price securities (\$5--25), raising a borrow-cost caveat. PnL is otherwise broad: the ten largest contributors account for roughly 8% of gross profit and 2,356 names contribute positively, though with a tilt toward technology sectors.

## 6.3 Risk character

The edge is concentrated in high-volatility and high-dispersion regimes, where dislocations are larger and liquidity provision is better compensated. Its worst episodes are momentum extremes rather than selloffs per se: the 2000 dot-com peak, the 2009 rebound, and the calm 2003--2007 bull market. The strategy is therefore best characterized as short momentum and long reversion with a liquidity-provision profile.

# 7 Out-of-sample test (2019--2024)

The frozen specification is evaluated once on the sealed 2019--2024 period, with no parameters adjusted after the holdout is observed. The out-of-sample evidence is weak relative to the in-sample period (Table 2, Figure 5).

**Table 2.** In-sample versus out-of-sample summary.

|                            | Gross Sharpe | Net @7bps | Break-even | Max DD  |
|----------------------------|:------------:|:---------:|:----------:|:-------:|
| In-sample 2000--2018       | 0.90         | +0.34     | 11.3 bps   | -14.0%  |
| Out-of-sample 2019--2024   | 0.23         | -0.15     | 4.2 bps    | -23.1%  |

Break-even falls to 4.2 bps, below realistic costs, and net Sharpe is positive only at an implausible 2 bps. The largest out-of-sample drawdown coincides with the 2020 COVID crash and rebound, a violent-momentum regime consistent with the in-sample diagnostics. A deflated Sharpe ratio accounting for twelve examined specifications assigns only a 0.20 probability that the true Sharpe is positive; the in-sample edge is fragile once selection is considered.

![Net equity (log scale, 7 bps cost) over the full sample, in-sample followed by out-of-sample. Strong early gains give way to a long plateau and an out-of-sample decline.](reports/figures/oos_equity.png){ width=5.4in }

# 8 Pre-registered refinements

Motivated by feedback on the initial results, a second phase asked whether reversal improves when conditioning on the likely cause of each move: temporary liquidity pressure, which should revert, versus information, which should not. Because the 2019--2024 holdout had already been unsealed, each refinement's hypothesis, construction, and stopping rule were pre-registered before its data or results existed. All development used 2000--2018; diagnostic tests are excluded from the trial count, and three candidate configurations enter the Phase 2 multiple-testing adjustment.

## 8.1 Volume conditioning: hypothesis rejected

The first hypothesis held that residual moves on abnormally low volume are more likely liquidity-driven and should revert more strongly. Abnormal volume is the five-day signal-window mean dollar volume relative to a non-overlapping trailing 60-day base. In this universe the data reject the hypothesis: one-day rank IC is higher after high-volume moves (+0.0130) than low-volume moves (+0.0074), and the five-day gradient disappears. This is consistent with evidence that, in large low-information-asymmetry stocks, heavy volume often reflects liquidity demand rather than information (Campbell, Grossman, and Wang, 1993; Llorente, Michaely, Saar, and Wang, 2002). Per the pre-registered rule, no volume-conditioned variant was built.

## 8.2 Earnings-announcement exclusion: hypothesis supported

Earnings announcements are identifiable information events, and returns around them drift rather than revert (Bernard and Thomas, 1989). Compustat report dates were mapped to CRSP identifiers using point-in-time links, placed on the first trading day on or after the report date, and used only after announcement. Signals whose five-day window contains an announcement show negative reversal IC (-0.0105), versus +0.0125 for clean signals: earnings-window moves are inverted reversal candidates. Excluding flagged names raises gross Sharpe from 0.90 to 1.03, but forced exit and re-entry raises turnover by roughly 16%, leaving break-even essentially unchanged. Figure 6 shows the mechanism: clean signals revert by roughly 10 bps per unit position over ten days, while earnings-window signals drift against the position.

![Average cumulative residual PnL per unit position over the ten days after signal formation, in-sample. Clean moves revert; earnings-window moves drift against the position, consistent with post-earnings-announcement drift.](reports/figures/earnings_eventtime.png){ width=5.4in }

## 8.3 Latent-factor residualization

The final refinement replaces two-digit-SIC sectors with a statistical-factor residual: correlation-based principal components estimated on rolling 252-day standardized returns, re-estimated every 21 trading days, with loadings applied forward. The primary specification pre-registers $k=15$ factors; $k=5$ and $k=30$ are sensitivities only. The top 15 explain roughly 52% of standardized variance. On common dates, PCA residualization raises gross Sharpe from 0.80 to 1.22 at identical turnover, almost entirely by lowering volatility (6.0% to 4.3%). It improves risk control, not per-trade edge. Figure 7 shows the variance-explained curve flattening beyond roughly fifteen components.

![Average cumulative share of standardized-return variance explained by the leading principal components, across all 288 rolling estimations. The pre-registered $k=15$ explains roughly 52%.](reports/figures/pca_scree.png){ width=5.4in }

## 8.4 The combined candidate and a non-independent validation check

**Table 3.** Residual method and earnings exclusion, in-sample common dates (2001--2018).

|                             | Gross Sharpe | Net @7bps | Break-even |
|-----------------------------|:------------:|:---------:|:----------:|
| Sector-LOO                  | 0.80         | 0.14      | 8.5 bps    |
| Sector-LOO + exclusion      | 0.92         | 0.16      | 8.5 bps    |
| PCA (k=15)                  | 1.22         | 0.26      | 8.9 bps    |
| PCA (k=15) + exclusion      | 1.37         | 0.28      | 8.8 bps    |

The two effective refinements are approximately additive. The combined candidate roughly doubles net in-sample performance relative to the Phase 1 baseline on identical dates, yet break-even is essentially unchanged: the refinements improve risk-adjusted performance, not cost tolerance. Because 2019--2024 was unsealed in Phase 1, it is only a non-independent check; on it the combined candidate has no gross edge (gross Sharpe -0.07; net -0.64 at 7 bps). Phase 2's deflated Sharpe ratio is 0.83, versus Phase 1's 0.20, so selection effects are limited, but recent-period performance remains poor. The deflated Sharpe ratio corrects for trial selection, not regime change; a genuinely fresh 2025-onward holdout awaits data availability.

# 9 Conclusion

Short-horizon residual reversal was strong in the early 2000s but has decayed below tradable levels: by the out-of-sample period it no longer clears realistic costs, capacity is limited, and residual alpha lies on the expensive-to-borrow short side. This matches the life cycle of a widely known, crowded anomaly. The pre-registered refinements sharpen rather than alter the conclusion: better residualization and event filtering improve implementation, but no in-sample improvement restores out-of-sample viability. The paper's contribution is methodological: a leak-safe pipeline, transparent construction sequence, execution and capacity layer, diagnostics, pre-registration, and one-shot out-of-sample test make the negative conclusion credible.

## 9.1 Limitations and future work

- Transaction costs use a flat 7 bps headline assumption with 2--10 bps sensitivity; market impact is reported across $\eta$, and borrow costs are not modeled despite the short-side, low-price alpha concentration.
- The analysis is daily and execution-aware, not intraday; TAQ or limit-order-book data and a path-dependent participation cap are natural extensions.
- The 2019--2024 window is spent after Phase 1. A pre-registered 2025-onward evaluation, once data are available, remains the final untouched test.
- Further extensions include Ornstein--Uhlenbeck s-score rules (Avellaneda and Lee, 2010), longer-horizon momentum or multi-signal blending, explicit borrow costs, ex-ante earnings calendars, and macro conditioning with VIX, yield-curve slope, and recession indicators.

# References {-}

```{=latex}
\begingroup
\setlength{\parindent}{-0.4in}
\setlength{\leftskip}{0.4in}
```

Almgren, R. and N. Chriss (2000), "Optimal Execution of Portfolio Transactions," *Journal of Risk*.

Almgren, R., C. Thum, E. Hauptmann, and H. Li (2005), "Direct Estimation of Equity Market Impact," *Risk*.

Avellaneda, M. and J. Lee (2010), "Statistical Arbitrage in the US Equities Market," *Quantitative Finance*.

Bailey, D. and M. López de Prado (2014), "The Deflated Sharpe Ratio," *Journal of Portfolio Management*.

Bernard, V.L. and J.K. Thomas (1989), "Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium?" *Journal of Accounting Research*.

Campbell, J.Y., S.J. Grossman, and J. Wang (1993), "Trading Volume and Serial Correlation in Stock Returns," *Quarterly Journal of Economics*.

Harvey, C.R., Y. Liu, and H. Zhu (2016), "... and the Cross-Section of Expected Returns," *Review of Financial Studies*.

Jegadeesh, N. and S. Titman (1993), "Returns to Buying Winners and Selling Losers," *Journal of Finance*.

Lehmann, B.N. (1990), "Fads, Martingales, and Market Efficiency," *Quarterly Journal of Economics*.

Llorente, G., R. Michaely, G. Saar, and J. Wang (2002), "Dynamic Volume-Return Relation of Individual Stocks," *Review of Financial Studies*.

Lo, A.W. and A.C. MacKinlay (1990), "When Are Contrarian Profits Due to Stock Market Overreaction?" *Review of Financial Studies*.

Shumway, T. (1997), "The Delisting Bias in CRSP Data," *Journal of Finance*.

Tóth, B., et al. (2011), "Anomalous Price Impact and the Critical Nature of Liquidity in Financial Markets," *Physical Review X*.

```{=latex}
\par\endgroup
```
