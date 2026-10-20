"""Load the normalised market data written by scripts/market/fetch_market_data.py.

Files under data/market/ (all optional; each strategy needs only some of them):
  index_daily.csv           date, symbol (NIFTY, INDIAVIX), open, high, low, close
  options_eod_NIFTY.csv.gz  date, expiry, strike, opt_type (CE/PE), open, high, low, close, settle,
                            volume, oi, chg_oi, underlying          (NSE F&O bhavcopy, NIFTY index options)
  futures_eod_NIFTY.csv.gz  date, expiry, open, high, low, close, oi, chg_oi, volume (NIFTY index futures)
  equities_daily.csv.gz     date, symbol, open, high, low, close, adj_close, volume
  index_minute_NIFTY.csv.gz datetime, open, high, low, close[, volume]   (any 1-minute source)
  events.csv                date, event      (days with no new short-premium entries)
"""
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MARKET = ROOT / "data" / "market"


def _read(path: Path, parse=("date",)) -> pd.DataFrame | None:
    if not path.exists():
        return None
    df = pd.read_csv(path)
    for col in parse:
        if col in df:
            df[col] = pd.to_datetime(df[col])
    return df


@dataclass
class Market:
    index: pd.DataFrame | None = None          # NIFTY daily, indexed by date
    vix: pd.Series | None = None               # India VIX close, indexed by date
    options: pd.DataFrame | None = None        # NIFTY options EOD
    futures: pd.DataFrame | None = None        # NIFTY front-month futures EOD, indexed by date
    equities: pd.DataFrame | None = None       # wide: adj_close by date x symbol
    minute: pd.DataFrame | None = None         # NIFTY 1-minute
    events: set = field(default_factory=set)
    _chain_index: pd.DataFrame | None = None
    _by_date: dict = field(default_factory=dict)

    @classmethod
    def load(cls, folder: Path = MARKET) -> "Market":
        m = cls()
        idx = _read(folder / "index_daily.csv")
        if idx is not None:
            m.index = idx[idx.symbol == "NIFTY"].set_index("date").sort_index()[["open", "high", "low", "close"]]
            vix = idx[idx.symbol == "INDIAVIX"].set_index("date").sort_index()
            m.vix = vix["close"] if len(vix) else None
        opt = _read(folder / "options_eod_NIFTY.csv.gz", parse=("date", "expiry"))
        if opt is not None:
            m.set_options(opt)
        fut = _read(folder / "futures_eod_NIFTY.csv.gz", parse=("date", "expiry"))
        if fut is not None:
            fut = fut.sort_values(["date", "expiry"]).groupby("date").first()  # front month
            m.futures = fut
        eq = _read(folder / "equities_daily.csv.gz")
        if eq is not None:
            m.equities = eq.pivot_table(index="date", columns="symbol", values="adj_close").sort_index()
        mi = _read(folder / "index_minute_NIFTY.csv.gz", parse=("datetime",))
        if mi is not None:
            m.minute = mi.set_index("datetime").sort_index()
        ev = _read(folder / "events.csv")
        if ev is not None:
            m.events = set(ev["date"].dt.normalize())
        return m

    def set_options(self, opt: pd.DataFrame) -> None:
        opt = opt.copy()
        opt["opt_type"] = opt["opt_type"].astype(str).str.upper()
        opt = opt[(opt["open"] > 0) & (opt["volume"] > 0)]  # untraded contracts carry stale/zero prices
        self.options = opt.sort_values(["date", "expiry", "strike", "opt_type"]).reset_index(drop=True)
        self._chain_index = self.options.set_index(["date", "expiry", "strike", "opt_type"]).sort_index()
        self._by_date = {d: g for d, g in self.options.groupby("date")}

    # ---- option chain helpers -------------------------------------------------------------
    def trading_days(self) -> pd.DatetimeIndex:
        if self.options is not None:
            return pd.DatetimeIndex(sorted(self.options["date"].unique()))
        return self.index.index

    def chain(self, date) -> pd.DataFrame:
        return self._by_date.get(date, self.options.iloc[:0])

    def expiries_on(self, date) -> list:
        ch = self.chain(date)
        return sorted(e for e in ch["expiry"].unique() if e >= date)

    def front_expiry(self, date, min_dte: int = 0):
        """Nearest expiry with at least `min_dte` calendar days left (0 = may be today)."""
        for e in self.expiries_on(date):
            if (e - date).days >= min_dte:
                return e
        return None

    def contract(self, date, expiry, strike, opt_type) -> pd.Series | None:
        try:
            row = self._chain_index.loc[(date, expiry, float(strike), opt_type)]
        except KeyError:
            return None
        return row.iloc[0] if isinstance(row, pd.DataFrame) else row

    def strikes(self, date, expiry, opt_type=None) -> np.ndarray:
        ch = self.chain(date)
        ch = ch[ch["expiry"] == expiry]
        if opt_type:
            ch = ch[ch["opt_type"] == opt_type]
        return np.sort(ch["strike"].unique())

    def atm_strike(self, date, expiry, spot: float) -> float | None:
        """Nearest strike to `spot` for which both CE and PE traded."""
        ce, pe = set(self.strikes(date, expiry, "CE")), set(self.strikes(date, expiry, "PE"))
        both = np.array(sorted(ce & pe))
        if not len(both):
            return None
        return float(both[np.argmin(np.abs(both - spot))])

    def nearest_strike(self, date, expiry, opt_type, target: float) -> float | None:
        s = self.strikes(date, expiry, opt_type)
        return float(s[np.argmin(np.abs(s - target))]) if len(s) else None
