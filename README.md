# BTC race bot — mean reversion on cbBTC (make.fun btc-race-24h-20261112-1439)

A bot that trades Coinbase Wrapped BTC (cbBTC) against USDC, minute by minute,
on 1-minute on-chain bars from the Orca Whirlpool, with $1,000 of paper money
(simulation only, no real money).

## Strategy

Mean reversion against a 120-minute simple moving average of closes:

- **Buy** the whole cash when the latest close is at least 100 bps below the
  120-minute SMA (a deep dip).
- **Sell** the whole position when the latest close is at least 20 bps above
  the 120-minute SMA (the dip has reverted).
- **Trailing stop**: sell if the latest close falls 60 bps below the best
  close seen since the position opened.
- **Time stop**: sell after holding 240 bars (4 hours).

On the published 24h dev window this makes **+$4.27 net PnL after all fees**
(3 trades, $1.61 fees, -0.45% max drawdown), passing the dev gate (net PnL
above $0). Neighbouring parameters in the same family (MA 100–180, entry
-80 to -120 bps, exit +10 to +30 bps) all stay profitable, so the result is
a cluster, not one lucky parameter.

## Why this shape

The dev window is a falling market (BTC -2.3% over 24h): buy-and-hold fails
the dev gate and fast trend crossovers whipsaw into fees (a full-size round
trip costs about 26 bps in fee, slippage and price impact). A deep-dip
mean-reversion entry only trades when the price has stretched far below its
120-minute average, and the exit waits for an actual reversion; the trailing
stop and the time stop cap the loss when a dip keeps falling instead of
reverting. In a downtrend the bot spends most of its time in cash, which is
the correct long-only position.

## Layout

- `main.py` — the bot (Python 3.13, standard library only).
- `vendor/makefun_bars.py` — byte-identical copy of the kit's
  `sdk/makefun_bars.py` protocol shim (agent-fun/bars-replay/v1).
- `LICENSE` — MIT.
- `.makefun/owner.json` — claim file naming the payout wallet.
