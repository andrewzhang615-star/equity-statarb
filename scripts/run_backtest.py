"""End-to-end orchestration: data -> signals -> weights -> backtest -> metrics.

Run from the repo root:  python scripts/run_backtest.py

Currently wires together the pieces that exist; signal steps are stubs until the
research phase fills them in.
"""
from __future__ import annotations

from src.backtest import engine, metrics
from src.config import CONFIG
from src.data.load import load_eligible, load_returns_full


def main() -> None:
    returns_full = load_returns_full()
    eligible = load_eligible()
    print(f"returns_full: {returns_full.shape[0]:,} days x {returns_full.shape[1]:,} names")
    print(f"eligible:     {int(eligible.sum(axis=1).mean()):,} tradable on an average day")

    # TODO: build signals once implemented, e.g.:
    #   from src.signals.residual import residual_reversal_signal
    #   from src.signals.momentum import momentum_signal
    #   from src.portfolio.construct import combine_signals
    #   signal = combine_signals({...}, CONFIG["portfolio"]["combine_weights"])
    #   weights = engine.signal_to_weights(signal, ...)
    #   res = engine.run_backtest(weights, returns, cost_bps=...)
    #   print(metrics.summary(res["net"], weights))

    print("Signals not yet implemented — see src/signals/.")


if __name__ == "__main__":
    main()
