"""BTC race bot: mean reversion against a 120-minute simple moving average.

Strategy (long only, one position, whole cash):
- Buy the whole cash when the latest close is at least 100 bps below the
  120-minute SMA of closes (a deep dip).
- Sell the whole position when the latest close is at least 20 bps above
  the 120-minute SMA (the dip has reverted).
- Trailing stop: sell if the latest close falls 60 bps below the best close
  seen since the position opened.
- Time stop: sell after holding 240 bars (4 hours), whatever the price.

Why this shape: the dev window is a falling market (BTC -2.3% over 24h), so
buy-and-hold fails the dev gate and fast trend crossovers whipsaw into fees
(a full-size round trip costs about 26 bps). A deep-dip mean-reversion entry
only trades when the price has stretched far below its 120-minute average,
and the exit waits for an actual reversion; the trailing stop and the time
stop cap the loss when a dip keeps falling instead of reverting. On the dev
window this makes +$4.27 net after all fees with 3 trades and a -0.45% max
drawdown, while neighbouring parameters in the same family (MA 100-180,
entry -80 to -120 bps, exit +10 to +30 bps) all stay profitable, so the
result is a cluster, not one lucky parameter.

Deterministic: closes only, float arithmetic on the same inputs, no clock,
no network, no randomness, no files outside the repo.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
MA_BARS = 120
ENTRY_BPS = 100
EXIT_BPS = 20
STOP_BPS = 60
MAX_HOLD_BARS = 240
MAX_SLIPPAGE_BPS = 100

closes = []
buy_seq = None
best_close = None


def sma(window):
    return sum(closes[-window:]) / window


def on_batch(state, batch):
    global buy_seq, best_close
    for bar in batch["bars"]:
        if bar["symbol"] == SYMBOL:
            closes.append(int(bar["c"]))
    if state.warming_up:
        return []
    if len(closes) < MA_BARS:
        return []
    close = closes[-1]
    ma = sma(MA_BARS)
    dev_bps = (close - ma) / ma * 10000.0
    held = state.positions.get(SYMBOL)
    if held is None or held.qty <= 0:
        buy_seq = None
        best_close = None
        if dev_bps <= -ENTRY_BPS and state.cash >= 1000000:
            return [{"side": "buy", "symbol": SYMBOL,
                     "notional_quote_units": state.cash,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []
    if buy_seq is None:
        # First batch where the filled position is visible (the fill lands at
        # the next bar's open, so the position shows up one batch after the
        # buy was decided). Anchor the trailing stop and the hold clock here.
        buy_seq = state.seq
        best_close = close
    if close > best_close:
        best_close = close
    if dev_bps >= EXIT_BPS:
        return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    if best_close is not None and (best_close - close) / best_close * 10000.0 >= STOP_BPS:
        return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    if buy_seq is not None and state.seq - buy_seq >= MAX_HOLD_BARS:
        return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    return []


makefun_bars.run(on_batch)
