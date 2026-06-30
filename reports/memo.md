---
title: "Execution-Aware Short-Horizon Equity Reversal"
subtitle: "Evidence of Decay, Costs, and Capacity Limits in US Equities (2000--2024)"
author: "Andrew Zhang"
documentclass: article
fontsize: 12pt
geometry: "margin=1.25in"
abstract: |
  This paper asks whether short-horizon cross-sectional reversal in US equities remains exploitable once implementation frictions are taken seriously. Using survivorship-bias-free CRSP daily data for 2000--2024 and a leak-safe backtest, I construct the strategy in stages, from a raw reversal baseline to a sector-residual signal with turnover control, and evaluate it under realistic transaction costs, capacity constraints, regime conditioning, and a single out-of-sample test. The signal is predictive, and after residualization and turnover control it is net-profitable in sample (Sharpe 0.34 net of 7 bps, with a break-even cost of 11.3 bps). Its edge nonetheless declines steadily across the sample, its capacity is limited (on the order of \$10--100M), and on a pre-registered 2019--2024 holdout it no longer survives realistic costs (net Sharpe -0.15 at 7 bps; break-even 4.2 bps). The evidence is consistent with a crowded, cost-sensitive anomaly that has been largely arbitraged away. The contribution is primarily methodological: a transparent framework for assessing whether a documented anomaly remains economically viable after costs.
---

# 1 Research question

Short-horizon reversal, the tendency for recent relative losers to outperform recent relative winners over horizons of days to weeks, is well documented (Lehmann, 1990; Lo and MacKinlay, 1990). For a practitioner the relevant question is not whether the effect is present in a frictionless backtest, but whether it remains economically meaningful once turnover, transaction costs, and capacity are accounted for. This paper addresses that question for liquid US equities, with an emphasis on methodological transparency: each result is constructed to withstand the standard objections rather than to maximize in-sample performance.

# 2 Data and look-ahead discipline

The sample consists of CRSP daily data for common shares (share codes 10--11) listed on the NYSE, AMEX, and NASDAQ over January 2000 through December 2024, comprising 27.2 million name-days across 12,859 securities. CRSP is survivorship-bias-free and records delisting returns, which is material here because a reversal strategy tends to accumulate positions in distressed names. Two features of the data construction are central.

- **Delisting returns.** Delisting returns are missing for 44.5% of delisting events. Following Shumway (1997), missing returns on performance-related delistings are set to -30% rather than zero, so that failed firms are not recorded as costless exits.
- **Separation of return measurement from tradability.** The backtest maintains two distinct panels: a realized-return panel, used to compute PnL and never masked, and a lagged eligibility mask (the top 1,000 names by trailing dollar volume, with prior-close price $\geq$ \$5 and delisting rows excluded) that governs only which names may receive new weight. This separation prevents a common contamination in which a position that loses eligibility is dropped from the return calculation rather than realizing its terminal loss.

Weights are formed at each day's close and lagged one day before they earn returns, so that the strategy conditions only on information available at the decision time. A suite of 28 unit tests guards the performance metrics and the look-ahead and disappearing-position safeguards.

# 3 Methodology

## 3.1 Signal construction

The base signal is the negative of each name's trailing five-day return, winsorized at $\pm$20% for signal construction only and never for realized PnL. Common variation is removed before reversal is measured, in two steps of increasing stringency. The first is a market residual, obtained from a rolling regression on the equal-weighted eligible universe. The second is a leave-one-out sector residual, formed by demeaning within two-digit SIC industry against eligible peers while excluding the name itself, so that a security does not anchor its own benchmark. Residualization isolates idiosyncratic reversal from sector- and market-level co-movement.

## 3.2 Portfolio and turnover control

Signals are mapped to dollar-neutral, cross-sectionally demeaned weights subject to a 2% per-name cap. Because daily five-day reversal generates high turnover, the signal is smoothed with an exponentially weighted moving average with a five-day half-life. Smoothing exchanges a modest reduction in gross signal strength for a substantial reduction in turnover, and proves decisive for net performance. The resulting specification, fixed for all subsequent tests, is a sector-residual five-day reversal signal with an EWMA half-life of five days, a top-1,000 universe, and a 7 bps per-turnover cost.

# 4 In-sample results (2000--2018)

Each stage of construction raises the per-trade edge, summarized by the break-even cost, defined as the cost per unit turnover at which net return is zero.

**Table 1.** Construction ladder, in-sample 2000--2018.

| Variant (in-sample)        | Gross Sharpe | Turnover/day | Break-even |
|----------------------------|:------------:|:------------:|:----------:|
| Raw reversal               | 0.67         | 0.63         | 4.4 bps    |
| + market residual          | 1.00         | 0.63         | 5.1 bps    |
| + sector residual (LOO)    | 1.22         | 0.64         | 5.5 bps    |
| + EWMA turnover control    | 0.90         | 0.23         | 11.3 bps   |

Residualization raises break-even from 4.4 to 5.5 bps; turnover control then approximately halves turnover and roughly doubles break-even, to 11.3 bps, rendering the strategy net-profitable at a 7 bps cost (net Sharpe 0.34, approximately 2.2% annualized). The specification is frozen at this point, prior to any out-of-sample evaluation.

# 5 Execution: costs and capacity

Because the strategy's viability depends on implementation, the cost and capacity analysis is central to what follows. Net Sharpe declines approximately linearly in the assumed cost, reaching zero near the 11.3 bps break-even (Figure 1).

![In-sample net Sharpe as a function of the assumed per-turnover cost. The strategy is net-positive up to the 11.3 bps break-even, losing approximately 0.08 in Sharpe per basis point.](reports/figures/cost_sensitivity.png){ width=5.4in }

Capacity is assessed under a square-root market-impact model, $\text{impact} \approx \eta \cdot \sigma \cdot \sqrt{\text{trade}/\text{ADV}}$, a standard approximation (Almgren et al., 2005; Tóth et al., 2011), with the coefficient $\eta$ reported across a plausible range rather than fixed at a single value. Usable capacity is modest, on the order of \$10--100M depending on $\eta$ (Figure 2). The binding constraint is not average liquidity but a thin-name tail: at \$1B of deployed capital, the largest single-name participation reaches several multiples of daily volume. Capping positions at a fraction of ADV controls this tail and limits the deterioration at scale, but does not extend the profitable frontier; it functions as a risk control rather than a means of expanding capacity.

![Net Sharpe as a function of deployed AUM under a square-root market-impact model, for three impact coefficients.](reports/figures/capacity.png){ width=5.4in }

# 6 Diagnostics

## 6.1 The edge has decayed

Partitioning the in-sample period into three sub-periods, break-even declines monotonically: 17.6 bps over 2000--2006, 8.0 bps over 2007--2012, and 6.9 bps over 2013--2018. Because break-even is invariant to the assumed cost level, this represents genuine decay in the per-trade edge, consistent with increased crowding, decimalization, and tighter markets, rather than an artifact of the cost assumption. By 2013--2018 the strategy is profitable only at execution costs below roughly 5 bps.

## 6.2 Where the alpha is, and what it costs to harvest

After market exposure is removed, the alpha is concentrated on the short side: the information ratio is 1.37 for shorting residual winners against 0.18 for buying residual losers, and the long leg's raw return is largely market beta. The profitable short positions are concentrated in low-price securities (\$5--25), which tend to be the most expensive and difficult to borrow. PnL is otherwise broadly distributed; the ten largest contributors account for roughly 8% of gross profit and 2,356 names contribute positively, indicating that the result does not derive from a small number of outlier securities, although it exhibits a tilt toward technology sectors.

## 6.3 Risk character

Conditioning returns on the market environment shows that the edge is concentrated in high-volatility and high-dispersion regimes, in which dislocations are larger; the strategy is compensated for supplying liquidity into such dislocations. Its worst episodes are informative. The deepest drawdown occurs during the comparatively calm 2003--2007 bull market, and the worst individual months are momentum extremes in both directions, the 2000 dot-com peak and the 2009 rebound, rather than selloffs as such. The strategy is therefore best characterized as short momentum and long reversion with a liquidity-provision profile: it profits when dislocations mean-revert and loses when trends persist.

# 7 Out-of-sample test (2019--2024)

The frozen specification is evaluated once on the sealed 2019--2024 period, with no parameters adjusted after the holdout is observed. The edge does not survive (Table 2, Figure 3).

**Table 2.** In-sample versus out-of-sample summary.

|                            | Gross Sharpe | Net @7bps | Break-even | Max DD  |
|----------------------------|:------------:|:---------:|:----------:|:-------:|
| In-sample 2000--2018       | 0.90         | +0.34     | 11.3 bps   | -14.0%  |
| Out-of-sample 2019--2024   | 0.23         | -0.15     | 4.2 bps    | -23.1%  |

Break-even continues to decline, to 4.2 bps, below any realistic cost, and net Sharpe is positive only at an implausible 2 bps. The largest out-of-sample drawdown coincides with the 2020 COVID crash and subsequent rebound, a violent-momentum regime of the kind the in-sample diagnostics identify as adverse. A deflated Sharpe ratio computed on the in-sample result, accounting for the twelve specifications examined, assigns only a 0.20 probability that the true Sharpe is positive; the in-sample edge is therefore statistically fragile once selection is taken into account.

![Net equity (log scale, 7 bps cost) over the full sample, in-sample followed by out-of-sample. Strong early gains give way to a long plateau and an out-of-sample decline.](reports/figures/oos_equity.png){ width=5.8in }

# 8 Conclusion

Short-horizon residual reversal was a strong effect in the early 2000s that has since decayed below tradable levels: by the out-of-sample period it no longer clears realistic costs, its capacity is limited, and its residual alpha lies on the expensive-to-borrow short side. This pattern is consistent with the typical life cycle of a widely known, crowded anomaly. The principal contribution of the paper is methodological. A leak-safe data pipeline, a transparent construction sequence, an execution and capacity layer, regime and attribution diagnostics, a pre-registered specification, and a single out-of-sample test together make the negative conclusion credible.

## 8.1 Limitations and future work

- Transaction costs are summarized by a flat 7 bps headline assumption, with sensitivity reported over 2--10 bps; the market-impact coefficient is uncertain and is presented as a range. Short-borrow costs are not modeled, which is a material omission given the short-side, low-price concentration of the alpha.
- Because the analysis uses daily data, it is execution-aware rather than intraday; a natural extension would employ TAQ or limit-order-book data and a path-dependent participation cap.
- Further extensions include PCA and Ornstein--Uhlenbeck residuals (Avellaneda and Lee, 2010), a longer-horizon momentum tilt and multi-signal blending, explicit modeling of borrowing costs, and conditioning on external macroeconomic variables such as the VIX, the slope of the yield curve, and recession indicators.

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

Harvey, C.R., Y. Liu, and H. Zhu (2016), "... and the Cross-Section of Expected Returns," *Review of Financial Studies*.

Jegadeesh, N. and S. Titman (1993), "Returns to Buying Winners and Selling Losers," *Journal of Finance*.

Lehmann, B.N. (1990), "Fads, Martingales, and Market Efficiency," *Quarterly Journal of Economics*.

Lo, A.W. and A.C. MacKinlay (1990), "When Are Contrarian Profits Due to Stock Market Overreaction?" *Review of Financial Studies*.

Shumway, T. (1997), "The Delisting Bias in CRSP Data," *Journal of Finance*.

Tóth, B., et al. (2011), "Anomalous Price Impact and the Critical Nature of Liquidity in Financial Markets," *Physical Review X*.

```{=latex}
\par\endgroup
```
