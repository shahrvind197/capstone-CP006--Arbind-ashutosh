"""
display.py  --  All terminal formatting for PortfolioIQ
"""

BAR_WIDTH = 30   # chars for the text bar chart
RS = "Rs."       # Rupee prefix (avoids special-char encoding issues)


def _sign(val):
    return "+" if val >= 0 else ""


def _color(val, text):
    """Green for positive, red for negative, yellow for zero."""
    if val is None:
        return text
    if val > 0:
        return "\033[92m" + text + "\033[0m"
    if val < 0:
        return "\033[91m" + text + "\033[0m"
    return "\033[93m" + text + "\033[0m"


def _rs(amount):
    """Format an amount with Rs. prefix."""
    return RS + f"{amount:,.2f}"


def header(title):
    width = 62
    print()
    print("=" * width)
    print((" " * 2 + title).center(width))
    print("=" * width)


def separator():
    print("-" * 62)


# -- Feature 2: Holdings ------------------------------------------------------

def show_holdings(active_holdings):
    header("Current Holdings & Average Buy Price")
    if not active_holdings:
        print("  No active holdings.")
        return

    print(f"  {'SYMBOL':<10} {'SECTOR':<18} {'QTY':>8} {'AVG BUY PRICE':>16}")
    separator()
    for sym, h in sorted(active_holdings.items()):
        avg_str = _rs(h['avg_price'])
        print(f"  {sym:<10} {h['sector']:<18} {h['qty']:>8.2f} {avg_str:>16}")
    separator()


# -- Features 3 & 4: P&L ------------------------------------------------------

def show_pnl(unrealised_rows, total_realised):
    header("P&L Report -- Realised + Unrealised")

    print(f"\n  {'SYMBOL':<10} {'QTY':>6} {'AVG COST':>12} {'MKT PRICE':>12} "
          f"{'UNREALISED P&L':>18} {'%':>9}")
    separator()

    total_unreal = 0.0
    total_cost   = 0.0

    for r in sorted(unrealised_rows, key=lambda x: x["symbol"]):
        sym = r["symbol"]
        qty = r["qty"]
        avg = r["avg_price"]
        mp  = r["mkt_price"]
        unr = r["unreal_pnl"]
        pct = r["pnl_pct"]
        mv  = r["mkt_value"]

        avg_str = _rs(avg)

        if mp is None:
            mp_str  = "N/A".rjust(12)
            unr_str = "N/A".rjust(18)
            pct_str = "N/A".rjust(9)
        else:
            mp_str  = _rs(mp).rjust(12)
            unr_raw = _sign(unr) + _rs(abs(unr))
            pct_raw = _sign(pct) + f"{pct:.2f}%"
            unr_str = _color(unr, unr_raw.rjust(18))
            pct_str = _color(pct, pct_raw.rjust(9))
            total_unreal += unr
            total_cost   += avg * qty

        print(f"  {sym:<10} {qty:>6.2f} {avg_str:>12} {mp_str} {unr_str} {pct_str}")

    separator()

    unr_raw      = _sign(total_unreal)   + _rs(abs(total_unreal))
    real_raw     = _sign(total_realised) + _rs(abs(total_realised))
    total_overall = total_unreal + total_realised
    ovr_raw      = _sign(total_overall)  + _rs(abs(total_overall))

    print(f"\n  Unrealised P&L (open positions) : {_color(total_unreal,   unr_raw)}")
    print(f"  Realised P&L   (closed trades)  : {_color(total_realised, real_raw)}")
    print(f"  Overall P&L                     : {_color(total_overall,  ovr_raw)}")

    if total_cost > 0:
        overall_pct = (total_unreal / total_cost) * 100
        pct_raw = _sign(overall_pct) + f"{overall_pct:.2f}%"
        print(f"  Portfolio return (unrealised)   : {_color(overall_pct, pct_raw)}")

    separator()


# -- Feature 5: Sector Allocation ---------------------------------------------

def show_sector_allocation(sector_rows):
    header("Sector Allocation")
    if not sector_rows:
        print("  No holdings to show allocation.")
        return

    total_val = sum(r["value"] for r in sector_rows)
    print(f"\n  {'SECTOR':<20} {'VALUE':>14}  {'%':>6}  BAR")
    separator()
    for r in sector_rows:
        filled   = int(round((r["pct"] / 100) * BAR_WIDTH))
        bar      = "#" * filled + "." * (BAR_WIDTH - filled)
        val_str  = _rs(r["value"]).rjust(14)
        pct_str  = f"{r['pct']:>5.1f}%"
        print(f"  {r['sector']:<20} {val_str}  {pct_str}  {bar}")

    separator()
    print(f"  {'TOTAL':<20} {_rs(total_val).rjust(14)}")
    separator()


# -- Trade History ------------------------------------------------------------

def show_trade_history(trades):
    header("Full Trade History")
    if not trades:
        print("  No trades recorded yet.")
        return

    print(f"  {'#':>4} {'DATE':<12} {'TYPE':<6} {'SYMBOL':<10} "
          f"{'SECTOR':<16} {'QTY':>8} {'PRICE':>13} {'VALUE':>14}")
    separator()

    for t in trades:
        t_type = t["type"]
        clr    = "\033[92m" if t_type == "BUY" else "\033[91m"
        rst    = "\033[0m"
        val    = t["qty"] * t["price"]
        p_str  = _rs(t["price"]).rjust(13)
        v_str  = _rs(val).rjust(14)
        print(
            f"  {t['id']:>4} {t['date']:<12} {clr}{t_type:<6}{rst} "
            f"{t['symbol']:<10} {t['sector']:<16} {t['qty']:>8.2f} {p_str} {v_str}"
        )

    separator()
    total_invested = sum(t["qty"] * t["price"] for t in trades if t["type"] == "BUY")
    total_sold     = sum(t["qty"] * t["price"] for t in trades if t["type"] == "SELL")
    print(f"  Total Invested : {_rs(total_invested)}")
    print(f"  Total Sold     : {_rs(total_sold)}")
    separator()


# -- Market Price Input -------------------------------------------------------

def prompt_market_prices(active_symbols):
    """Ask user to enter today's price for each active symbol. Returns dict."""
    header("Enter Today's Market Prices")
    if not active_symbols:
        print("  No active holdings.")
        return {}

    prices = {}
    print("  Press ENTER to skip a symbol (shows N/A in P&L report).\n")
    for sym in sorted(active_symbols):
        while True:
            raw = input(f"  {sym} current price (Rs.): ").strip()
            if raw == "":
                break
            try:
                p = float(raw)
                if p <= 0:
                    print("  Price must be positive. Try again.")
                    continue
                prices[sym] = p
                break
            except ValueError:
                print("  Invalid number. Try again.")
    return prices
