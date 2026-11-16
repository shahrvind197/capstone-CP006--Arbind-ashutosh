# CP-006 PortfolioIQ: Equity Portfolio and P&L Analytics System

## How to run

```bash
cd cp006_portfolioiq
python main.py
```

Requires Python 3.7 or later. No external libraries needed.

## Features

1. Add Buy Trade
2. Add Sell Trade
3. View Holdings & Average Buy Price
4. Enter Today's Market Prices
5. View P&L (Realised + Unrealised)
6. View Sector Allocation
7. View Full Trade History
8. Trades are saved to `trades.csv` and reloaded automatically on next run

## File structure

```
cp006_portfolioiq/
  main.py       — menu loop and user interaction
  portfolio.py  — trade logic, WAC calculation, P&L, sector allocation
  display.py    — terminal formatting
  trades.csv    — auto-generated; stores all trades across sessions
```