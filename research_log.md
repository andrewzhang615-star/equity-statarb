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

## 2026-06-27 - Sector-residual reversal (leave-one-out), IS 2000-2018

Three-step progression (5d reversal, $-neutral, IS 2000-2018, 7 bps assumed):

| variant             | gross Sharpe | gross ann | vol   | gross maxDD | turnover | breakeven |
|---------------------|--------------|-----------|-------|-------------|----------|-----------|
| raw                 | 0.67         | 6.7%      | 10.5% | -14.3%      | 0.63     | 4.4 bps   |
| market-residual     | 1.00         | 8.0%      |  8.0% | -13.7%      | 0.63     | 5.1 bps   |
| sector-residual LOO | 1.22         | 8.9%      |  7.2% |  -8.2%      | 0.64     | 5.5 bps   |

Each residualization step raises the **per-trade edge** (breakeven 4.4 -> 5.1 -> 5.5 bps) and cuts vol +
drawdown, confirming market & (especially) sector co-movement contaminated raw reversal. Sector = leave-
one-out mean over eligible same-2-digit-SIC peers (>=5 peers), point-in-time.

**Turnover stays ~0.63/day across all three** -> none clears 7 bps (all net-negative). The breakeven math
is now demonstrated end-to-end: residualization improves the edge; the remaining 5.5 -> 7+ bps gap can only
come from **turnover reduction** (no-trade band, EWMA smoothing, longer holding) = decisive next lever.
Viability is also cost-assumption-sensitive: at <=5 bps the sector variant is ~breakeven -> motivates the
cost-sensitivity + capacity analysis.

---

## 2026-06-27 - Turnover reduction: strategy crosses to net-positive (IS 2000-2018)

Sweep on the sector-residual signal (7 bps assumed):

| config        | turnover | gross Sh | net Sh | breakeven |
|---------------|----------|----------|--------|-----------|
| base (daily)  | 0.635    | 1.22     | -0.33  | 5.5 bps   |
| EWMA hl=2     | 0.325    | 1.10     | +0.28  | 9.4 bps   |
| EWMA hl=3     | 0.279    | 1.02     | +0.33  | 10.3 bps  |
| EWMA hl=5     | 0.228    | 0.90     | +0.34  | 11.3 bps  |
| EWMA hl=10    | 0.173    | 0.74     | +0.33  | 12.5 bps  |
| hold k=5      | 0.292    | 1.05     | +0.28  | 9.5 bps   |

EWMA smoothing ~halves turnover for a modest gross give-up, pushing breakeven past 7 bps and flipping net
Sharpe -0.33 -> ~+0.34. Net is flat across hl 3-10 (plateau, not a knife-edge -> not obviously overfit).
Smoothing beats fixed-grid holding at equal turnover (hl=3 net 0.33 vs hold k=3 net 0.03): gradual vs lumpy.

Full arc: raw (4.4 bps, -0.39) -> +residualization (5.5, -0.33) -> +EWMA smoothing (~11, **+0.34**).
Short-horizon reversal survives realistic costs only once residualized AND traded slowly.

CAVEATS (do not over-claim): IS-only; halflife is a TUNED knob (best of sweep); net ~0.34 is modest. Plan:
(1) lock hl=5, (2) cost-sensitivity + capacity, (3) confirm on sealed 2019-2024 holdout ONCE,
(4) deflated Sharpe over the trial count. Do not trust the IS number until OOS + deflation survive it.

---

## 2026-06-27 - Cost sensitivity (locked candidate, IS 2000-2018)

Net Sharpe vs assumed per-turnover cost for sector-residual + EWMA hl=5 (turnover 0.228/day):

| cost bps | 0 | 5 | 7 (assumed) | 10 | 11.3 | 12 |
|----------|---|---|-------------|----|------|----|
| net Sh   | 0.90 | 0.50 | 0.34 | 0.10 | ~0 (breakeven) | -0.06 |

~Linear (~ -0.08 Sharpe per bp); net-positive for costs up to ~11 bps. Figure:
`reports/figures/cost_sensitivity.png`. Takeaway: viability hinges on executing below ~11 bps/turnover --
plausible for patient trading in top-1000 liquid names; even naive ~7 bps leaves a thin but positive
margin. Next: capacity (does the edge survive at scale once our own trades move prices?).

---

## 2026-06-27 - Capacity (locked candidate, IS 2000-2018)

Square-root impact on top of the 7 bps floor; net Sharpe vs AUM (eta = impact coeff):

| AUM   | eta=0.3 | eta=0.6 | eta=1.0 | max participation |
|-------|---------|---------|---------|-------------------|
| $10M  | 0.23    | 0.12    | -0.03   | 3.6%              |
| $100M | -0.01   | -0.36   | -0.84   | 35.8%             |
| $1B   | -0.78   | -1.90   | -3.38   | 358%              |

**Low-capacity strategy.** Even optimistic eta=0.3 caps useful capacity ~$50-100M; mid/conservative eta
caps it at ~$10-30M. Average participation stays tiny to $100M, but the MAX hits 36% of ADV at $100M and
>100% by ~$316M -> a thin-name tail is the binding constraint, not the average. MVP does NOT cap
participation; a real book would cap at ~1-5% ADV (bounds the tail, lowers deployable capital).
Figure: reports/figures/capacity.png.

Interpretation (literature-consistent): short-horizon residual reversal is a REAL but small-capacity edge --
which is precisely why it persists (can't be scaled away). Honest, strong narrative.

---

## 2026-06-27 - Robustness: subperiod DECAY + leg attribution (IS)

Subperiod stability (locked candidate, 7 bps):

| period    | gross Sh | net Sh | net ann | breakeven |
|-----------|----------|--------|---------|-----------|
| 2000-2006 | 1.11     | 0.67   | 6.0%    | 17.6 bps  |
| 2007-2012 | 0.71     | 0.09   | 0.4%    | 8.0 bps   |
| 2013-2018 | 0.85     | -0.01  | -0.1%   | 6.9 bps   |

**The net edge decayed.** Breakeven fell 17.6 -> 8.0 -> 6.9 bps; the GROSS per-trade edge ~halved over the
sample (classic short-horizon reversal decay: crowding, decimalization, tighter markets). Breakeven is
cost-assumption-independent, so the decay is real, not a flat-7bps artifact. Full-IS net Sharpe 0.34 was an
AVERAGE masking strong-early / dead-recent.

Nuance (don't over-read "dead"): flat 7 bps is anachronistic -- real costs fell post-2001 decimalization, so
this overcharges the recent era. 2013-2018 breakeven 6.9 bps -> at realistic ~2-3 bps it's ~breakeven, not
dead. Precise statement: edge decayed from large to THIN.

Implication for OOS: 2019-2024 is even more recent -> expect modest/decayed. Set expectations; do NOT p-hack
a recent-winning variant.

Leg attribution (gross, IS): long (buy resid losers) ann 5.5% / Sh 0.43; short (sell resid winners) ann
-0.8% / Sh ~0. Looks long-side concentrated BUT confounded by directional market exposure (long leg rides
market drift). Needs beta-adjusted legs to be conclusive.

---

## 2026-06-27 - Robustness round 2: subperiod x cost + beta-adjusted legs (IS)

Subperiod net Sharpe at 2/5/7/10 bps:

| period    | gross | break | @2   | @5   | @7    | @10   |
|-----------|-------|-------|------|------|-------|-------|
| 2000-2006 | 1.11  | 17.6  | 0.98 | 0.79 | 0.67  | 0.48  |
| 2007-2012 | 0.71  |  8.0  | 0.54 | 0.27 | 0.09  | -0.18 |
| 2013-2018 | 0.85  |  6.9  | 0.61 | 0.24 | -0.01 | -0.38 |
| ALL IS    | 0.90  | 11.3  | 0.74 | 0.50 | 0.34  | 0.10  |

Recent period (2013-2018) is **THIN, not dead**: net-positive at <=5 bps, ~0 at 7, negative at 10. The edge
became execution-dependent, not extinct (2-5 bps is realistic for liquid large-caps today).

Beta-adjusted legs (CAPM vs EW eligible market, gross IS) -- the naive "long-side" read was a MARKET-BETA
ARTIFACT:

| leg   | contrib_ann | beta  | alpha_ann | IR   |
|-------|-------------|-------|-----------|------|
| long  | 5.5%        | +0.63 | 0.8%      | 0.18 |
| short | -0.8%       | -0.51 | 4.6%      | 1.37 |

**Alpha is on the SHORT side** (selling residual winners): short-leg alpha IR 1.37 vs long-leg 0.18. The
long leg's 5.5% was mostly market beta. Short-side concentration helps explain persistence (harder to arb)
and flags an UNMODELED cost: short borrow/constraints (document as a caveat; do NOT short-tilt = p-hacking).

---

## 2026-06-27 - Robustness: liquidity buckets (IS, top 500/1000/1500)

Locked candidate restricted to top-N by dollar volume (both traded universe AND sector peer set), 7 bps:

| universe | names/day | gross | net  | net ann | breakeven |
|----------|-----------|-------|------|---------|-----------|
| top 500  | 448       | 0.79  | 0.31 | 2.2%    | 11.6 bps  |
| top 1000 | 940       | 0.90  | 0.34 | 2.2%    | 11.3 bps  |
| top 1500 | 1418      | 1.05  | 0.44 | 2.8%    | 12.2 bps  |

Edge is **liquidity-robust**: breakeven stable ~11-12 bps across tiers; the most-liquid top-500 keeps a
solid edge (gross 0.79, net 0.31) -> the alpha does NOT rely on illiquid/thin names. Sharpe rises modestly
top500->top1500 but breakeven (per-trade edge) is flat -> the uptick is mostly diversification, not extra
alpha. Ties to capacity: the thin-name tail was an EXECUTION/impact problem, not the alpha source (this also
answers the "thin-name reliance" check). top-500 is likely the more capacity-robust deployment (edge held +
higher ADV), but keep the locked candidate at top-1000 (switching to the best-looking bucket = p-hacking);
flag top-500 as a viable higher-capacity variant for the writeup.

---

## 2026-06-27 - Participation (position) cap (IS, eta=0.6)

Capped each name's position to cap_frac of its ADV$ (|w| <= cap_frac*ADV$/AUM, re-neutralized over TRADED
names), re-ran capacity. (Bug found & fixed first: a blanket re-neutralization leaked weight onto zero-ADV
untraded names -> inf participation / NaN net; now demean over traded names only + keep untraded at 0,
regression-tested.)

net Sharpe by AUM x cap (eta=0.6, 7 bps floor):

| AUM   | uncapped | cap5% | cap10% | cap25% |
|-------|----------|-------|--------|--------|
| $10M  | 0.12     | 0.12  | 0.12   | 0.12   |
| $100M | -0.36    | -0.32 | -0.36  | -0.36  |
| $1B   | -1.90    | -0.94 | -1.19  | -1.54  |
| $10B  | -6.61    | -1.43 | -1.91  | -2.75  |

max participation at $1B: uncapped 358% -> cap5% 26%, cap10% 25%.

Reads: the cap **sharply limits impact damage at scale** (tighter = better; $10B net -6.6 -> -1.4 w/ cap5%;
$1B max participation 358% -> ~25%). BUT it does NOT extend the net-positive frontier (still ~$10M, ~break-
even by $30M) -- it limits downside, not adds capacity, because the edge itself is thin. Caveat: a POSITION
cap bounds position/ADV but not the extreme TRADE/ADV tail (max ~300% at $10B); a true path-dependent trade
cap would (future refinement). Figure: reports/figures/participation_cap.png.

**Robustness battery complete.** Story reinforced: real but small-capacity (~$10-30M @ mid impact),
execution-dependent, short-side alpha that decayed over time. Capping = risk control, not capacity unlock.

---

## 2026-06-27 - Diagnostics: IC decay + macro/regime conditioning (IS)

(1) Rank-IC of the (pre-EWMA) sector-residual reversal signal vs forward CUMULATIVE residual returns:

| horizon | 1d | 2d | 3d | 5d | 10d |
|---------|----|----|----|----|----|
| rank-IC | +0.0098 | +0.0139 | +0.0162 | +0.0186 | +0.0165 |

Cumulative IC rises to a peak at ~5 days then plateaus/declines -> the reversal realizes over ~a week,
justifying the 5-day lookback + EWMA hl=5. IC magnitudes (~0.01-0.019) small but typical/solid for daily
equity signals; positive & consistent. (Raw t-stats omitted -- overlapping forward windows inflate them.)

(2) Macro / regime conditioning (GROSS, IS) -- supports the "fade dislocation" mechanism:
- market realized vol (21d): low Sh 0.90 | mid 0.07 | high 1.60 (ann 18.1%). High-vol dominates.
- cross-sectional dispersion: low 0.26 | mid 0.57 | high 1.45 (ann 16.8%). MONOTONIC in dispersion.
- market direction: up-days Sh 3.18 (ann 26.7%) | down-days Sh -2.10 (ann -13%).

Reads: edge concentrated in **high-vol / high-dispersion** markets (reversal = paid to provide liquidity into
dislocation). And despite dollar-neutral construction the PnL is **NOT market-state-neutral**: makes money on
up days, loses on down days. Precise framing (per review -- don't overclaim "short-vol" off a single-day
split): **liquidity-provision / crash-risk exposure -- best when dislocations mean-revert, struggles when
selloffs persist** (to be substantiated with multi-day drawdown/crash episodes in batch 2). Partly residual
net beta (+0.12) but too large to be only that -> genuine regime dependence. Honest risk caveat + macro hook.

---

## 2026-06-27 - Diagnostics 2: PnL attribution + short-side + crash episodes (IS)

(a) Concentration -- BROAD, not a few-name artifact:
- top-10 names 8.3% of gross PnL, top-50 30.5%; 2356 names net-positive vs 1484 negative.
- by year: front-loaded (2000 +0.36, 2001 +0.21 -> decay); 2008 strong (+0.16, high-vol paying off);
  2009 the only down year (-0.02, the violent rebound); 2010-2018 thin but mostly positive.
- by 2-digit SIC (point-in-time): tech-leaning (73 software +0.34 ~= 28% of total, 36 electronics +0.23,
  35, 38) -> mild tech concentration to flag; bottom sectors only slightly negative.

(b) Short-side realism: short-leg PnL by PRICE concentrates in LOW-PRICE names ($5-10 +0.55, $10-25 +0.43;
  $25-50 -0.20, $50+ -0.80); by ADV ~flat. Profitable shorting is in cheap (still-liquid, top-1000) names ->
  **borrow-cost / short-squeeze realism caveat** (low-price = costlier to borrow), not an illiquidity issue.
  Matters because the alpha is short-side.

(c) Crash / drawdown episodes -- REFINES the risk story (per the don't-overclaim caution):
- Worst drawdown -14.0% is a LONG SLOW GRIND 2002-01 -> 2008-07 while the market rose +39.5% -> worst pain is
  the CALM low-vol bull (decay + cost grind), NOT a crash.
- Worst 5 months are MOMENTUM EXTREMES in BOTH directions: 2000-02 (mkt +16.5%, dot-com blow-off) and 2009-04
  (mkt +16.4%, GFC rebound) are the two worst -- violent RALLIES; plus selloffs 2001-09 (-15.5%), 2000-11
  (-17.4%), 2002-02 (-5.0%).

**Corrected framing:** the strategy is **short momentum / long reversion (liquidity provision)** -- earns by
fading dislocations in high-vol/dispersed markets; loses when momentum dominates (strong trends EITHER
direction) and bleeds slowly in calm low-vol bulls. NOT simply "short-vol / loses in selloffs" (the two worst
months were rallies). Precise, defensible interview narrative.

---

## === FINAL STRATEGY SPECIFICATION -- FROZEN 2026-06-27 (pre-OOS) ===

Locked BEFORE looking at the 2019-2024 holdout. No further IS tuning.

**OOS alpha candidate:**
- Signal: 5-day short-horizon reversal on leave-one-out SECTOR-RESIDUAL returns.
  - sector = 2-digit SIC (point-in-time); LOO mean over eligible same-sector peers, min 5 peers.
  - reversal = -(sum of trailing 5d residual returns); signal input winsorized at +/-20%.
- Turnover control: EWMA smoothing of the signal, halflife = 5 trading days.
- Universe: top-1000 by trailing 60d dollar volume; prior-close >= $5; common shares (shrcd 10,11);
  NYSE/AMEX/NASDAQ (exchcd 1,2,3); delisting rows excluded.
- Weights: cross-sectionally dollar-neutral, per-name cap 2%, gross leverage 1.0.
- Costs (evaluation): 7 bps/turnover linear floor (headline); 2-10 bps sensitivity reported.
- Data: CRSP daily 2000-2024; missing performance-delisting return imputed -0.30 (Shumway).
- Split: IS 2000-2018 (all research/tuning); OOS 2019-2024 (run ONCE, no re-tuning).

**Reported alongside (NOT part of the OOS alpha):**
- Capacity: square-root impact, eta {0.3,0.6,1.0} -> ~$10-100M (eta-dependent).
- Position (ADV) cap: deployment risk control; bounds tail impact, doesn't add capacity.
- top-500 universe: capacity-friendly variant (edge holds).

**Decisions deliberately NOT taken (anti-p-hacking):**
- No SHORT-tilt despite short-side alpha (IR 1.37 vs 0.18) -- fitting + adds short-borrow realism.
- No switch to top-500 despite better capacity -- keep pre-declared top-1000.
- No ADV position cap inside the OOS alpha (implementation-only).
- No cherry-picked / time-varying cost schedule for the headline (flat 7 bps; sensitivity shown).
- No further IS tuning.

**IS headline (locked candidate, 7 bps):** gross Sharpe 0.90, net 0.34 (t~1.5), breakeven 11.3 bps,
turnover 0.23/day. Decayed across subperiods (breakeven 17.6 -> 8.0 -> 6.9 bps); thin & execution-
dependent by 2013-2018.

**Trials tried (for deflated Sharpe):** ~12 strategy configs -- raw; market-residual (full + eligible
proxy); sector-residual; EWMA hl {2,3,5,10}; holding-period k {2,3,5,10}. (Liquidity buckets, cost/eta/
capacity grids, and the cap are sensitivities on the fixed candidate, not separate alphas.)

**OOS expectation (pre-stated):** modest/marginal at 7 bps; likely positive only at low (<=5 bps) cost.

---

## 2026-06-27 - ONE-SHOT OOS RESULT (2019-2024) -- frozen candidate

|            | gross Sh | net@2 | net@5 | net@7 | ann@7 | maxDD  | breakeven | turn |
|------------|----------|-------|-------|-------|-------|--------|-----------|------|
| IN-SAMPLE  | 0.90     | 0.74  | 0.50  | 0.34  | +2.2% | -14.0% | 11.3 bps  | 0.23 |
| OUT-SAMPLE | 0.23     | 0.12  | -0.04 | -0.15 | -2.1% | -23.1% |  4.2 bps  | 0.23 |

Deflated Sharpe (IS net, 12 trials): P(true Sharpe>0 | selection) = **0.20**.

**Conclusion: the edge did NOT survive OOS at realistic costs.** Gross Sharpe 0.90 -> 0.23; breakeven
continued decaying 17.6 -> 8.0 -> 6.9 (IS subperiods) -> **4.2 bps (OOS)**. Net positive only at ~2 bps
(0.12), negative at 5-7. OOS maxDD -23% = the 2020 COVID crash/rebound (the violent-momentum regime the
diagnostics flagged). Deflated Sharpe 0.20 -> the IS net result is largely consistent with selection luck
once the ~12 configs are accounted for.

**Honest, on-thesis result (not a failure):** short-horizon residual reversal was a strong real edge in the
early 2000s, decayed steadily (crowding, decimalization, efficiency), and by 2019-2024 no longer clears
realistic costs -- a crowded, cost-sensitive, capacity-constrained anomaly arbitraged down. Backed by a
leak-safe pipeline, residualization ladder, cost/capacity analysis, regime + short-side diagnostics, a
frozen spec, and a true one-shot holdout. Files: reports/oos_summary.txt, reports/figures/oos_equity.png.

**Holdout now spent. No further tuning/evaluation on 2019-2024.** Next: writeup (README + research memo).

---

## Experiment ledger

| Date | Signal / variant | Params | IS Sharpe | OOS Sharpe | Notes |
|------|------------------|--------|-----------|------------|-------|
| 2026-06-27 | raw 5d reversal, $-neutral | lb=5, winsor +/-20%, prior-close $5, 7bps | 0.67 gross / -0.39 net | sealed | turnover 0.63/day; **breakeven 4.4bps**; dies on costs |
| 2026-06-27 | market-residual 5d reversal | + 60d rolling beta vs EW eligible-universe market | 1.00 gross / -0.39 net | sealed | vol→8.0%; **breakeven 5.1bps**; closer, still dies at 7bps |
| 2026-06-27 | sector-residual 5d reversal (LOO) | 2-digit SIC, eligible peers ≥5, point-in-time | 1.22 gross / -0.33 net | sealed | **breakeven 5.5bps**; gross maxDD -8.2%; turnover pinned 0.64 |
| 2026-06-27 | sector-resid + EWMA smooth hl=5 | turnover control | 0.90 gross / **+0.34 net** | sealed | **breakeven 11.3bps**; turnover 0.64→0.23; FIRST net-positive (IS, tuned) |

---

# PHASE 2 — Conditioning reversal on information proxies

## 2026-07-01 - Phase 2 pre-registration (written BEFORE any Phase 2 result)

**Phase 1 is frozen.** Its answer stands: classic residual reversal decayed below realistic costs.
Phase 2 is a new iteration motivated by course-mentor feedback (add layers: volume/news interaction,
earnings exclusion, latent-factor residualization).

**Phase 2 question:** can we identify the subset of reversal opportunities that are temporary
*liquidity dislocations* rather than *information-driven* moves? (Directly tests the Phase 1
liquidity-provision interpretation.)

**Methodology rules (pre-registered):**
1. All development on IS 2000-2018 ONLY.
2. 2019-2024 is a **spent** holdout (unsealed in Phase 1) -> may be reported only as a labeled
   "prior holdout" sanity check, never as fresh evidence.
3. A NEW holdout (2025 -> latest available CRSP) will be pulled and SEALED before any Phase 2
   result is produced. The final layered candidate is evaluated on it exactly once.
4. New experiment ledger below; every variant logged; trial count feeds the Phase 2 deflated Sharpe.
5. Layers in order: (A) volume conditioning, (B) earnings exclusion, (C) PCA/latent-factor
   residualization. News only if a clean source materializes; otherwise volume+earnings are the
   information-event proxies.

**Layer A design (for review before build) — volume-conditioned reversal:**
- Hypothesis: a residual move on abnormally LOW volume is more likely temporary (liquidity-driven)
  and should revert more; a high-volume move is more likely informed. (Lo-MacKinlay uninformed-
  trading story; also the course's "uninformed trading" guidance.)
- Abnormal volume AV_{i,t} = mean dollar volume over the 5d signal window (t-4..t, known at close t)
  / trailing 60d mean dollar volume ending t-5 (no overlap). Same timing as the return signal; no
  extra look-ahead concerns.
- Step 1 (diagnostic FIRST): tercile the cross-section by AV daily; report reversal IC and
  gross/breakeven by tercile on IS. If low-AV shows no edge advantage, the layer stops there.
- Step 2 (pre-registered variants, only if step 1 supports): (a) hard filter — trade only
  below-median-AV names; (b) continuous downweight — scale signal by (1 - cross-sectional AV rank).
- Metrics: gross/net Sharpe, breakeven, turnover vs the Phase 1 locked candidate on identical IS.

## Phase 2 experiment ledger

| Date | Layer / variant | Params | IS result | Notes |
|------|-----------------|--------|-----------|-------|
| | | | | |

## 2026-07-01 - Pre-registration amendment: fresh holdout NOT yet available

The 2025+ holdout pull returned data only through **2024-12-31** (CRSP on WRDS is on its
annual/lagged update cycle; 2025 vintages not yet posted). The p2holdout files were verified to be a
strict subset of the existing 2000-2024 pull and deleted. Status:

- **No fresh sealed holdout exists yet.** Rule 3 of the pre-registration is pending, not satisfied.
- Phase 2 development proceeds on IS 2000-2018 only. 2019-2024 may appear ONLY as a labeled
  "spent prior holdout" sanity check.
- Action item: re-run the holdout pull when CRSP posts 2025 data; seal it before any final
  Phase 2 evaluation.

## 2026-07-01 - Layer A Step 1 result: hypothesis NOT supported (IS 2000-2018)

Reversal by abnormal-volume (AV) tercile, sector-residual 5d signal, ~878 valid names/day:

| tercile | IC(1d) | t    | IC(5d) | t    | gross Sh | turnover | breakeven |
|---------|--------|------|--------|------|----------|----------|-----------|
| low AV  | +0.0074 |  4.0 | +0.0190 | 11.0 | 0.96 | 0.879 | 3.5 bps |
| mid AV  | +0.0101 |  5.4 | +0.0189 | 10.7 | 1.05 | 1.025 | 3.0 bps |
| high AV | +0.0130 |  7.6 | +0.0182 | 11.0 | 1.16 | 0.718 | 5.0 bps |

**Findings:**
1. **In this large/liquid top-1000 universe, volume alone did not isolate the low-information
   reversal opportunities we hoped for.** At the 1d horizon the gradient runs the other way:
   reversal is monotonically stronger after HIGH-volume moves (IC 0.0074 -> 0.0130), consistent
   with liquidity-demand / market-maker-inventory stories in liquid stocks (Campbell-Grossman-Wang
   1993; Llorente-Michaely-Saar-Wang 2002 predict exactly this for large, low-information-asymmetry
   names). The low-volume intuition may still hold in other settings -- small caps, genuinely
   news-filtered returns, or intraday data -- which volume alone cannot proxy here.
2. **At the 5d horizon the IC is FLAT across terciles** (~0.019 everywhere) -> the volume
   interaction lives at ~1 day, shorter than our strategy's effective holding (EWMA hl=5).
3. **No tercile beats the unconditional strategy's 5.5 bps breakeven** (3.5/3.0/5.0): restricting
   to a third of names adds tercile-membership churn (turnover 0.72-1.03 vs 0.64) and cuts breadth.

**Decision per pre-registration:** the low-AV variants are NOT built (hypothesis unsupported). A
flipped high-AV tilt would be a post-hoc, data-derived hypothesis; given the flat 5d IC and no
breakeven improvement, we do NOT build it either. Layer A closes with a real finding: in liquid
large caps at a multi-day horizon, volume conditioning does not add net value; the 1d high-volume
reversal gradient is real but not exploitable at our rebalance profile. -> Proceed to Layer B
(earnings exclusion), which targets information events directly instead of via volume.

Trial accounting: these are DIAGNOSTIC tests, recorded in the ledger for transparency but
excluded from the deflated-Sharpe candidate count -- no strategy was selected from them. Only
candidate strategy configurations enter the DSR trial count.

| Date | Layer / variant | Params | IS result | Notes |
|------|-----------------|--------|-----------|-------|
| 2026-07-01 | A: AV terciles (diagnostic) | AV=5d/60d $vol, terciles | high-AV IC(1d) 0.0130 > low 0.0074; 5d flat | hypothesis rejected; no variant built |

## 2026-07-01 - Layer B pre-registration: earnings exclusion (written BEFORE any earnings data pulled)

**Motivation (sharpened by Layer A):** volume failed to isolate information events in large caps,
so target identifiable information events directly. Earnings-announcement moves are information-
driven and tend to DRIFT (PEAD), not revert -- a reversal signal formed from an earnings-window
move is fighting momentum.

**Hypothesis:** excluding names whose signal window contains an earnings announcement raises the
mean edge per trade (breakeven) of the remaining book.

**Data:** Compustat quarterly report dates (`comp.fundq.rdq`) via WRDS, mapped gvkey->permno with
the CRSP/Compustat link table (`crsp.ccmxpf_lnkhist`), honoring link-date ranges and primary link
types (LU/LC, linkprim P/C). Coverage by year must be reported (rdq is sparse early-sample).

**Timing rule (no look-ahead):** only PAST announcements are used -- a name is flagged on day t if
an rdq falls in its signal lookback window (t-4 .. t), i.e. "the move I would fade contains an
earnings event." No pre-announcement blackout in v1 (that requires an ex-ante calendar; noted as a
possible variant using expected-next-rdq, NOT built unless pre-registered later).

**Step 1 (diagnostic FIRST):** split signal name-days into "earnings-in-window" vs "clean";
report reversal IC (1d, 5d) and gross/breakeven for each group, plus the earnings-in-window share
of names/day. If earnings-window reversal is NOT materially weaker, the layer stops there.
**Step 2 (only if step 1 supports):** the exclusion strategy -- baseline candidate weights with
earnings-in-window names ineligible for NEW weight -- vs the unconditional baseline on identical
IS. Metrics: gross/net Sharpe, breakeven, turnover.

IS 2000-2018 only; diagnostic tests excluded from the DSR candidate count as before.

**Amendment (pre-registered before any earnings data):** daily rdq imperfectly times after-close
announcements (the move can land the NEXT trading day). v1 uses the rdq trading day; a robustness
variant flagging rdq..rdq+1 is pre-registered HERE (config `signals.earnings.extend: 1`) and may be
run later without constituting a post-hoc change.

## 2026-07-01 - Layer B Step 1 result: hypothesis SUPPORTED (IS 2000-2018)

Coverage healthy: flagged share ~7.4-7.9% of eligible name-days every year 2000-2018 (close to the
~8% expected from 4 announcements x 5d windows / 252d) -> conclusions not driven by coverage gaps.
862,387 rdq rows; 33,324 link rows; point-in-time mapping.

| group               | IC(1d)  | IC(5d)  | gross Sh | breakeven |
|---------------------|---------|---------|----------|-----------|
| earnings-in-window  | -0.0105 | -0.0089 | -0.23    | -1.4 bps  |
| clean               | +0.0125 | +0.0220 |  1.48    | +6.3 bps  |

**Earnings-window moves do not revert -- they DRIFT** (negative reversal IC = PEAD-consistent
continuation), while clean moves revert better than the unconditional baseline. This is the
information-vs-liquidity split Phase 2 was designed to test, confirmed with an identifiable
information event where the volume proxy (Layer A) failed.

**Gate passed -> Step 2 (pre-registered): the exclusion strategy.** Baseline candidate weights with
earnings-in-window names ineligible for weight, vs the unconditional baseline on identical IS.
Implementation note: our vectorized engine rebuilds targets daily, so "ineligible for new weight"
= weight forced to 0 while flagged (forced exit + re-entry turnover). A path-dependent
hold-but-don't-add variant is a possible refinement, not built in v1. The exclusion strategy is a
CANDIDATE configuration -> counts in the Phase 2 DSR trial ledger.

## 2026-07-01 - Layer B Step 2 result: exclusion improves the candidate, modestly (IS 2000-2018)

| candidate            | gross Sh | gross ann | turnover | breakeven | net@2 | net@5 | net@7 |
|----------------------|----------|-----------|----------|-----------|-------|-------|-------|
| baseline (Phase 1)   | 0.90     | 6.4%      | 0.228    | 11.3 bps  | 0.74  | 0.50  | 0.34  |
| earnings-excluded    | 1.03     | 7.5%      | 0.265    | 11.2 bps  | 0.85  | 0.57  | 0.39  |

**Reads:**
1. Removing earnings-window names lifts the gross edge (Sharpe 0.90 -> 1.03; ann +1.1%) --
   consistent with the Step 1 diagnostic (that slice was actively losing).
2. The forced exit/re-entry churn materialized exactly as flagged: turnover +16% (0.228 -> 0.265).
   Mean-return gain and turnover gain offset almost exactly -> **breakeven unchanged (11.3 -> 11.2)**.
3. Net Sharpe still improves at every cost level (net@7 0.34 -> 0.39) because the strategy earns
   more per unit time at similar vol; but the improvement (+0.05 net) is well inside statistical
   noise for a 19y sample -- report as hypothesis-consistent, not as proof.
4. Phase 1's headline conclusion is NOT overturned: the strategy remains execution-dependent
   (breakeven ~11 bps, unchanged).

Possible refinement (NOT built; path-dependent): hold-but-don't-add during earnings windows could
keep the gross gain without the forced round-trips. Would be a new pre-registered candidate.

**DSR trial ledger (Phase 2 candidates): #1 earnings-excluded candidate.** (Layer A produced no
candidate; diagnostics excluded from count.)

| Date | Layer / variant | Params | IS result | Notes |
|------|-----------------|--------|-----------|-------|
| 2026-07-01 | B: earnings-in-window flag (diagnostic) | rdq PIT-linked, 5d window | flagged IC(1d) -0.0105 vs clean +0.0125 | gate PASSED |
| 2026-07-01 | B: earnings-excluded candidate | baseline + flag-ineligible | gross 1.03 / net@7 0.39 | CANDIDATE #1; breakeven flat |

## 2026-07-01 - Layer C pre-registration: PCA/latent-factor residualization (spec before code)

**Hypothesis:** statistical factors estimated from the return panel capture co-movement beyond
market + 2-digit sector (styles, hidden clusters), producing a cleaner idiosyncratic residual and
therefore a stronger reversal signal (Avellaneda & Lee 2010).

**Estimation design (pre-registered):**
- Correlation-based PCA: winsorized (signal-input) returns standardized per name by trailing
  window std, so high-vol names don't dominate the factors.
- Rolling window 252 trading days; names require >= 60% non-missing coverage in-window (missing
  standardized returns set to 0 for estimation and projection); estimation universe = eligible.
- **Re-estimated every 21 trading days** (compute tractability); loadings applied forward until the
  next estimation. Loadings at estimation date t0 use returns through t0 (same-day contemporaneous
  use, consistent with the sector-LOO convention); days t0+1..t0+21 use stale loadings (no
  look-ahead).
- Residual (eigenvectors orthonormal): resid_std = (I - Lambda Lambda') R_std, de-standardized by
  each name's window std. Feed into the same 5d reversal + baseline construction.
- **Factor count: k = 15 is THE primary candidate** (Avellaneda-Lee ballpark; expect ~50-60%
  variance explained -- reported as a sanity diagnostic). k = 5 and k = 30 are reported as
  SENSITIVITY ONLY: selection will NOT be based on them; if the primary fails but a sensitivity
  succeeds, we do NOT switch. This keeps the DSR selection count honest.

**Comparison (identical IS, baseline construction -- no earnings exclusion yet):**
sector-LOO residual (Phase 1) vs PCA(k=15) residual: gross/net Sharpe, breakeven, turnover.
**Final combined candidate** (whichever residual wins + earnings exclusion) is evaluated last and
enters the DSR ledger as its own candidate.

DSR candidate ledger additions when run: #2 PCA(k=15) candidate; (#3 final combined candidate).

**Amendment (pre-build, per review):**
1. **Explicit decision rule** (replaces "whichever residual wins"): evaluate PCA(k=15) against
   sector-LOO on the pre-specified headline metric = **net Sharpe @ 7 bps on common valid dates**
   (PCA needs a 252d warmup, so both candidates are compared only on dates where the PCA residual
   exists; breakeven and gross reported alongside). If PCA(k=15) improves it, the final combined
   candidate is PCA(k=15) + earnings exclusion; otherwise it remains sector-LOO + earnings
   exclusion. No other selection between the two.
2. **Missing-data transparency:** "missing standardized return -> 0" means missing is treated as a
   NEUTRAL (mean) return in correlation/factor estimation -- defensible matrix completion, but
   biased if missingness is nonrandom. The run must report per-estimation coverage: names retained
   per PCA window and average in-window coverage. Names failing the 60% rule get NaN residuals
   (no signal), never fabricated ones.
3. **Implementation:** economy SVD on the standardized T x N window (T=252 < N~1000) rather than
   forming the N x N correlation matrix -- cheaper and numerically more stable; right singular
   vectors = correlation eigenvectors.

## 2026-07-01 - Layer C result: PCA(k=15) beats sector-LOO on the pre-registered metric (IS, common dates)

Diagnostics healthy: 288 estimations, ~963 names/window, 99.8% avg coverage, var explained (k=15)
avg 51.5% (inside the expected 50-60%). Common window 2000-12-29..2018 (PCA warmup excludes most of
2000 -- note the baseline is weaker here than full-IS [net@7 0.14 vs 0.34] because 2000, the
strongest year, drops out; decay visible again).

| candidate (common dates) | gross Sh | ann  | turnover | breakeven | net@2 | net@5 | net@7 |
|--------------------------|----------|------|----------|-----------|-------|-------|-------|
| sector-LOO (baseline)    | 0.80     | 4.8% | 0.228    | 8.5 bps   | 0.61  | 0.33  | 0.14  |
| **PCA k=15 (candidate)** | **1.22** | 5.2% | 0.228    | 8.9 bps   | 0.94  | 0.53  | **0.26** |
| PCA k=5  (sensitivity)   | 0.97     | 4.6% | 0.227    | 8.1 bps   | 0.73  | 0.37  | 0.13  |
| PCA k=30 (sensitivity)   | 1.22     | 5.0% | 0.228    | 8.6 bps   | 0.94  | 0.51  | 0.23  |

**Decision per the pre-registered rule:** PCA(k=15) improves the headline metric (net@7 0.26 vs
0.14) -> the final combined candidate is **PCA(k=15) + earnings exclusion**.

Reads: (1) PCA's main gift is RISK control -- vol 6.0% -> 4.3% (15 statistical factors hedge far
more co-movement than one sector demean) with slightly higher return; breakeven only modestly
better (8.5 -> 8.9), so the cost frontier story is intact. (2) The k-sensitivity is reassuringly
smooth (k=5 too few; k=15~k=30 plateau) -- primary not a knife-edge, and no selection temptation
arose. (3) Turnover identical across residual methods.

DSR candidate ledger: #2 PCA(k=15) candidate. Next: #3 final combined (PCA + earnings exclusion).

| Date | Layer / variant | Params | IS result | Notes |
|------|-----------------|--------|-----------|-------|
| 2026-07-01 | C: PCA k=15 candidate | 252d, re-est 21d, corr-SVD | gross 1.22 / net@7 0.26 (common dates) | CANDIDATE #2; beats sector-LOO 0.14 |
| 2026-07-01 | C: PCA k=5 / k=30 | sensitivity only | net@7 0.13 / 0.23 | no selection from these |

## 2026-07-01 - Phase 2 final combined candidate (IS, common dates 2000-12-29..2018)

| candidate                    | gross Sh | ann  | turnover | breakeven | net@2 | net@5 | net@7 |
|------------------------------|----------|------|----------|-----------|-------|-------|-------|
| sector-LOO (Phase 1)         | 0.80     | 4.8% | 0.228    | 8.5 bps   | 0.61  | 0.33  | 0.14  |
| sector-LOO + earn-excl       | 0.92     | 5.6% | 0.266    | 8.5 bps   | 0.70  | 0.38  | 0.16  |
| PCA k=15                     | 1.22     | 5.2% | 0.228    | 8.9 bps   | 0.94  | 0.53  | 0.26  |
| **PCA k=15 + earn-excl (FINAL)** | **1.37** | 5.9% | 0.266  | 8.8 bps   | 1.06  | 0.59  | **0.28** |

**Reads:**
1. **The two layers are additive and near-independent:** earnings exclusion adds ~+0.12-0.15 gross
   Sharpe on either residual; PCA adds ~+0.42-0.45 on either exclusion state. Clean attribution.
2. **FINAL vs Phase 1 baseline (common dates): gross 0.80 -> 1.37, net@7 0.14 -> 0.28.** Phase 2
   delivered a materially better strategy on IS.
3. **The cost frontier is unchanged all the way through** (breakeven 8.5 -> 8.8 bps): Phase 2
   improved risk-adjusted quality (mostly vol reduction + removing losing trades), NOT the
   per-trade edge. Phase 1's execution-dependence conclusion stands fully.
4. Honest note: on top of PCA, the earnings layer's NET add at 7 bps is small (+0.02, inside
   noise); its contribution is clearer gross and at low costs (+0.12 at 2 bps) because the forced
   exit/re-entry churn (turnover 0.228 -> 0.266) offsets it at higher costs.

**DSR candidate ledger: #3 FINAL = PCA(k=15) + earnings exclusion.** Phase 2 development complete;
3 candidates total. Endgame: labeled spent-holdout (2019-2024) sanity check, Phase 2 deflated
Sharpe over 3 candidates, fresh 2025+ holdout when CRSP posts it, memo/README Phase 2 section.

| Date | Layer / variant | Params | IS result | Notes |
|------|-----------------|--------|-----------|-------|
| 2026-07-01 | FINAL: PCA k=15 + earn-excl | combined | gross 1.37 / net@7 0.28 (common dates) | CANDIDATE #3 |

## 2026-07-01 - Phase 2 endgame: spent-holdout sanity check + deflated Sharpe

FINAL candidate (PCA k=15 + earnings exclusion):

| period                              | gross Sh | ann   | breakeven | net@2 | net@5 | net@7 | maxDD@7 |
|-------------------------------------|----------|-------|-----------|-------|-------|-------|---------|
| IS 2000-2018 (development)          | 1.37     | 5.9%  | 8.8 bps   | 1.06  | 0.59  | 0.28  | -16.7%  |
| **2019-2024 [SPENT - sanity only]** | **-0.07** | -1.0% | -0.9 bps  | -0.24 | -0.48 | -0.64 | -31.2%  |

Phase 2 deflated Sharpe (IS net@7, 3 candidates): **P(true Sharpe>0 | selection) = 0.83**.

**Reads (the honest ones):**
1. **The decay conclusion is brutally confirmed.** On 2019-2024 the final candidate has NO gross
   edge at all (-0.07) -- worse than the Phase 1 candidate's 0.23 on the same window, though the
   difference over ~6 noisy years is itself within noise. No amount of cleaner residualization or
   event filtering resurrects an edge that is gone: Phase 2's IS gains did not transfer.
2. **A teaching moment on DSR:** the Phase 2 deflated Sharpe (0.83) is far healthier than Phase 1's
   (0.20) -- few candidates, disciplined selection -- yet the strategy still fails the recent
   period. DSR corrects for SELECTION among counted trials; it cannot correct for REGIME DECAY.
   In-sample statistical solidity is necessary, not sufficient.
3. Caveat in both directions: 2019-2024 is a spent window (unsealed in Phase 1; Phase 2 layers were
   chosen knowing how reversal behaved through it), so this is a labeled sanity check -- but its
   message is consistent with every subperiod diagnostic since Phase 1. The honest final exam is
   the 2025+ vintage, still pending CRSP's release.

**Phase 2 development is CLOSED.** Remaining: memo/README Phase 2 section; fresh-holdout one-shot
when 2025 data ships.
