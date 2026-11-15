"""
PortfolioIQ  —  CP-006
Equity Portfolio and P&L Analytics System
Terminal-based console application | Python
"""

import sys
import portfolio as pf
import display   as dp

# Session-level market prices (updated whenever user enters them)
_market_prices: dict = {}


# ── Menu helpers ──────────────────────────────────────────────────────────────

def print_menu():
    print()
    print("╔══════════════════════════════════════════╗")
    print("║          PortfolioIQ  —  CP-006          ║")
    print("║   Equity Portfolio & P&L Analytics       ║")
    print("╠══════════════════════════════════════════╣")
    print("║  1. Add Buy Trade                        ║")
    print("║  2. Add Sell Trade                       ║")
    print("║  3. View Holdings & Avg Buy Price        ║")
    print("║  4. Enter Today's Market Prices          ║")
    print("║  5. View P&L  (Realised + Unrealised)    ║")
    print("║  6. View Sector Allocation               ║")
    print("║  7. View Full Trade History              ║")
    print("║  0. Exit                                 ║")
    print("╚══════════════════════════════════════════╝")


def get_choice():
    return input("  Choose option: ").strip()


def pause():
    input("\n  Press ENTER to continue...")


# ── Option handlers ───────────────────────────────────────────────────────────

def handle_add_buy():
    dp.header("Add Buy Trade")
    try:
        symbol = input("  Stock symbol  (e.g. INFY, TCS): ").strip().upper()
        if not symbol:
            print("  Symbol cannot be empty.")
            return
        sector = input("  Sector        (e.g. IT, Banking, Auto): ").strip()
        if not sector:
            print("  Sector cannot be empty.")
            return
        qty    = float(input("  Quantity      : "))
        price  = float(input("  Buy price (₹) : "))
        date   = input("  Date          (dd-mm-yyyy): ").strip()
        pf.add_buy(symbol, sector, qty, price, date)
        print(f"\n  ✔  BUY recorded — {qty} × {symbol} @ ₹{price:,.2f}")
    except ValueError as e:
        print(f"\n  ✘  Error: {e}")


def handle_add_sell():
    dp.header("Add Sell Trade")
    active = pf.get_active_holdings()
    if not active:
        print("  No holdings to sell.")
        pause()
        return
    print("  Active holdings:", ", ".join(sorted(active.keys())))
    try:
        symbol = input("  Stock symbol  : ").strip().upper()
        qty    = float(input("  Quantity      : "))
        price  = float(input("  Sell price (₹): "))
        date   = input("  Date          (dd-mm-yyyy): ").strip()
        pf.add_sell(symbol, qty, price, date)
        gain = pf.realised_pnl.get(symbol, 0.0)
        print(f"\n  ✔  SELL recorded — {qty} × {symbol} @ ₹{price:,.2f}")
        print(f"     Cumulative realised P&L for {symbol}: "
              f"{'₹'+f'{gain:+,.2f}'}")
    except ValueError as e:
        print(f"\n  ✘  Error: {e}")


def handle_view_holdings():
    dp.show_holdings(pf.get_active_holdings())


def handle_enter_prices():
    global _market_prices
    active = pf.get_active_holdings()
    if not active:
        print("\n  No active holdings.")
        pause()
        return
    new_prices = dp.prompt_market_prices(list(active.keys()))
    # Merge — keep prices for symbols not re-entered
    _market_prices.update(new_prices)
    print(f"\n  ✔  Prices updated for: {', '.join(sorted(new_prices.keys())) or 'none'}")


def handle_view_pnl():
    rows = pf.get_unrealised_pnl(_market_prices)
    if not rows:
        print("\n  No active holdings. Add a buy trade first.")
        pause()
        return
    dp.show_pnl(rows, pf.get_total_realised())


def handle_sector_allocation():
    rows = pf.get_sector_allocation(_market_prices)
    dp.show_sector_allocation(rows)


def handle_trade_history():
    dp.show_trade_history(pf.trades)


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    # Load saved trades from CSV
    try:
        pf.load_from_file()
        saved = len(pf.trades)
        if saved:
            print(f"\n  ✔  Loaded {saved} trade(s) from previous session.")
    except Exception as e:
        print(f"\n  ⚠  Could not load saved trades: {e}")

    dispatch = {
        "1": handle_add_buy,
        "2": handle_add_sell,
        "3": handle_view_holdings,
        "4": handle_enter_prices,
        "5": handle_view_pnl,
        "6": handle_sector_allocation,
        "7": handle_trade_history,
    }

    while True:
        print_menu()
        choice = get_choice()

        if choice == "0":
            print("\n  Goodbye! Your trades are saved.\n")
            sys.exit(0)

        handler = dispatch.get(choice)
        if handler:
            handler()
        else:
            print("  Invalid option. Enter 0–7.")

        pause()


if __name__ == "__main__":
    main()
