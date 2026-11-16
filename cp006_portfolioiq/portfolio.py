"""
portfolio.py  —  Core logic for PortfolioIQ
Handles trade storage, holdings computation (WAC), P&L, and sector allocation.
"""

from datetime import datetime
import csv
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), "trades.csv")

# ── In-memory stores ──────────────────────────────────────────────────────────
trades = []          # list of dicts: {id, type, symbol, sector, qty, price, date}
holdings = {}        # symbol → {qty, avg_price, sector}
realised_pnl = {}    # symbol → float  (cumulative realised gain/loss)
_trade_counter = [0] # mutable counter wrapped in list for easy mutation


# ── Helpers ───────────────────────────────────────────────────────────────────

def _next_id():
    _trade_counter[0] += 1
    return _trade_counter[0]


def _fmt_date(d: str) -> str:
    """Accept dd-mm-yyyy or yyyy-mm-dd; return yyyy-mm-dd."""
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(d, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    raise ValueError(f"Cannot parse date '{d}'. Use dd-mm-yyyy or yyyy-mm-dd.")


# ── Trade operations ──────────────────────────────────────────────────────────

def add_buy(symbol: str, sector: str, qty: float, price: float, date: str):
    symbol = symbol.upper().strip()
    sector = sector.strip().title()
    date   = _fmt_date(date)

    if qty <= 0 or price <= 0:
        raise ValueError("Quantity and price must be positive.")

    trade = {
        "id":     _next_id(),
        "type":   "BUY",
        "symbol": symbol,
        "sector": sector,
        "qty":    qty,
        "price":  price,
        "date":   date,
    }
    trades.append(trade)

    # Update holdings using weighted average cost
    if symbol in holdings:
        h = holdings[symbol]
        total_cost  = h["avg_price"] * h["qty"] + price * qty
        h["qty"]   += qty
        h["avg_price"] = total_cost / h["qty"]
        # sector may be updated if user corrects it
        h["sector"] = sector
    else:
        holdings[symbol] = {"qty": qty, "avg_price": price, "sector": sector}
        realised_pnl[symbol] = 0.0

    _save_trade(trade)


def add_sell(symbol: str, qty: float, price: float, date: str):
    symbol = symbol.upper().strip()
    date   = _fmt_date(date)

    if qty <= 0 or price <= 0:
        raise ValueError("Quantity and price must be positive.")

    if symbol not in holdings or holdings[symbol]["qty"] <= 0:
        raise ValueError(f"No holdings found for {symbol}.")

    h = holdings[symbol]
    if qty > h["qty"]:
        raise ValueError(
            f"Cannot sell {qty} shares of {symbol}. You only hold {h['qty']}."
        )

    # Realised P&L for this sell
    gain = (price - h["avg_price"]) * qty
    realised_pnl[symbol] = realised_pnl.get(symbol, 0.0) + gain

    h["qty"] -= qty
    if h["qty"] == 0:
        # Keep the record but zero out qty; avg_price preserved for display
        pass

    trade = {
        "id":     _next_id(),
        "type":   "SELL",
        "symbol": symbol,
        "sector": h["sector"],
        "qty":    qty,
        "price":  price,
        "date":   date,
    }
    trades.append(trade)
    _save_trade(trade)


# ── Holdings & P&L views ──────────────────────────────────────────────────────

def get_active_holdings():
    """Return holdings where qty > 0."""
    return {sym: h for sym, h in holdings.items() if h["qty"] > 0}


def get_unrealised_pnl(market_prices: dict):
    """
    market_prices: {symbol: current_price}
    Returns list of dicts with per-stock unrealised info.
    """
    result = []
    for sym, h in holdings.items():
        if h["qty"] <= 0:
            continue
        mp = market_prices.get(sym)
        if mp is None:
            result.append({
                "symbol":    sym,
                "sector":    h["sector"],
                "qty":       h["qty"],
                "avg_price": h["avg_price"],
                "mkt_price": None,
                "unreal_pnl": None,
                "pnl_pct":   None,
                "mkt_value": None,
            })
        else:
            unreal = (mp - h["avg_price"]) * h["qty"]
            pct    = ((mp - h["avg_price"]) / h["avg_price"]) * 100
            result.append({
                "symbol":    sym,
                "sector":    h["sector"],
                "qty":       h["qty"],
                "avg_price": h["avg_price"],
                "mkt_price": mp,
                "unreal_pnl": unreal,
                "pnl_pct":   pct,
                "mkt_value": mp * h["qty"],
            })
    return result


def get_total_realised():
    return sum(realised_pnl.values())


def get_sector_allocation(market_prices: dict):
    """
    Returns list of {sector, value, pct} sorted by value desc.
    Uses market price if available, else cost value.
    """
    sector_value = {}
    for sym, h in holdings.items():
        if h["qty"] <= 0:
            continue
        mp  = market_prices.get(sym, h["avg_price"])
        val = mp * h["qty"]
        s   = h["sector"]
        sector_value[s] = sector_value.get(s, 0.0) + val

    total = sum(sector_value.values())
    if total == 0:
        return []

    result = [
        {"sector": s, "value": v, "pct": (v / total) * 100}
        for s, v in sector_value.items()
    ]
    result.sort(key=lambda x: x["value"], reverse=True)
    return result


# ── Persistence ───────────────────────────────────────────────────────────────

def _save_trade(trade: dict):
    file_exists = os.path.isfile(DATA_FILE)
    with open(DATA_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id","type","symbol","sector","qty","price","date"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(trade)


def load_from_file():
    """Replay all trades from CSV on startup."""
    if not os.path.isfile(DATA_FILE):
        return
    with open(DATA_FILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["qty"]   = float(row["qty"])
            row["price"] = float(row["price"])
            row["id"]    = int(row["id"])
            if row["type"] == "BUY":
                # Replay directly into holdings without re-saving
                _replay_buy(row)
            else:
                _replay_sell(row)
            trades.append(row)
            if row["id"] >= _trade_counter[0]:
                _trade_counter[0] = row["id"]


def _replay_buy(row):
    sym    = row["symbol"]
    sector = row["sector"]
    qty    = row["qty"]
    price  = row["price"]
    if sym in holdings:
        h = holdings[sym]
        total_cost = h["avg_price"] * h["qty"] + price * qty
        h["qty"]  += qty
        h["avg_price"] = total_cost / h["qty"]
        h["sector"] = sector
    else:
        holdings[sym] = {"qty": qty, "avg_price": price, "sector": sector}
        realised_pnl[sym] = 0.0


def _replay_sell(row):
    sym   = row["symbol"]
    qty   = row["qty"]
    price = row["price"]
    if sym in holdings:
        h    = holdings[sym]
        gain = (price - h["avg_price"]) * qty
        realised_pnl[sym] = realised_pnl.get(sym, 0.0) + gain
        h["qty"] -= qty
