"""Mechanics tests on hand-built data where the right answer can be computed by hand."""
import numpy as np
import pandas as pd
import pytest

from backtest import black76, signals
from backtest.costs import DEFAULT_COSTS, NIFTY_LOT
from backtest.data import Market
from backtest.metrics import summarize_fixed_capital
from backtest.strategies import equity, intraday, options_eod
from backtest.strategies.legs import intraday_leg

D0, D1, D2, D3 = (pd.Timestamp(x) for x in ("2024-01-05", "2024-01-08", "2024-01-09", "2024-01-10"))


def bar(o, h, l, c):
    return pd.Series({"open": o, "high": h, "low": l, "close": c})


# ---------------------------------------------------------------- costs and pricing
def test_option_costs_sell_includes_stt_buy_includes_stamp():
    sell = DEFAULT_COSTS.option_order(100.0, NIFTY_LOT, "sell")
    buy = DEFAULT_COSTS.option_order(100.0, NIFTY_LOT, "buy")
    turnover = 100.0 * NIFTY_LOT
    common = 20 + turnover * (0.0003503 + 1e-6) + 0.18 * (20 + turnover * (0.0003503 + 1e-6))
    assert sell == pytest.approx(common + turnover * 0.0015)
    assert buy == pytest.approx(common + turnover * 0.00003)


def test_black76_implied_vol_round_trip():
    k = np.array([20000.0, 21000.0, 22000.0])
    px = black76.price(21000.0, k, 7 / 365, 0.15, [False, True, True])
    iv = black76.implied_vol(px, 21000.0, k, 7 / 365, [False, True, True])
    assert np.allclose(iv, 0.15, atol=1e-4)


def test_put_call_parity():
    c = black76.price(21000.0, 21100.0, 0.05, 0.2, True)
    p = black76.price(21000.0, 21100.0, 0.05, 0.2, False)
    assert c - p == pytest.approx(np.exp(-black76.RATE * 0.05) * (21000 - 21100), abs=1e-6)


# ---------------------------------------------------------------- leg simulation
def test_short_leg_stop_hit_and_not_hit():
    slip = DEFAULT_COSTS.opt_slippage
    hit = intraday_leg(bar(100, 140, 90, 95), "sell", sl_pct=0.30)
    assert hit.exit_reason == "stop" and hit.exit == pytest.approx(130 + slip) and hit.entry == pytest.approx(100 - slip)
    miss = intraday_leg(bar(100, 125, 60, 70), "sell", sl_pct=0.30)
    assert miss.exit_reason == "close" and miss.pnl_pts == pytest.approx((100 - slip) - (70 + slip))


def test_long_leg_stop_assumed_when_stop_and_target_both_touched():
    f = intraday_leg(bar(100, 200, 60, 150), "buy", sl_pct=0.30, tp_pct=0.90)
    assert f.exit_reason == "stop"
    f = intraday_leg(bar(100, 200, 80, 150), "buy", sl_pct=0.30, tp_pct=0.90)
    assert f.exit_reason == "target" and f.exit == pytest.approx(190 - DEFAULT_COSTS.opt_slippage)


# ---------------------------------------------------------------- a tiny option market
def tiny_market():
    m = Market()
    m.index = pd.DataFrame({"open": [20990, 21000, 21010, 21050], "high": [21050, 21100, 21100, 21300],
                            "low": [20950, 20900, 20950, 21000], "close": [21000, 21020, 21040, 21250]}, index=[D0, D1, D2, D3])
    rows = []
    for d, ce, pe in [(D0, (110, 115, 100, 105), (110, 115, 100, 105)), (D1, (100, 120, 80, 90), (100, 140, 85, 110)), (D2, (90, 100, 60, 70), (95, 110, 70, 80)),
                      (D3, (40, 260, 30, 250), (40, 45, 0.05, 0.05))]:
        for typ, (o, h, l, c) in (("CE", ce), ("PE", pe)):
            rows.append({"date": d, "expiry": D3, "strike": 21000.0, "opt_type": typ, "open": o, "high": h, "low": l,
                         "close": c, "settle": c, "volume": 1000, "oi": 5000, "chg_oi": 0, "underlying": np.nan})
    m.set_options(pd.DataFrame(rows))
    return m


def test_a1_straddle_pnl_matches_hand_calculation():
    m = tiny_market()
    sig = pd.DataFrame(index=m.index.index)
    tr = options_eod.a1_straddle_920(m, sig)
    assert len(tr) == 4
    tr = tr.iloc[1:]
    s = DEFAULT_COSTS.opt_slippage
    # day 1: CE 100 -> close 90 (no stop at 130); PE 100 -> high 140 hits the 130 stop
    ce = (100 - s) - (90 + s)
    pe = (100 - s) - (130 + s)
    assert tr.iloc[0]["pnl_pts"] == pytest.approx(ce + pe)
    # day 3 is expiry day: expiry slippage applies; CE stop at 52 hit
    se = DEFAULT_COSTS.opt_slippage_expiry
    assert tr.iloc[2]["pnl_pts"] == pytest.approx(((40 - se) - (52 + se)) + ((40 - se) - (0.05 + se)))
    assert (tr["pnl_rs"] == tr["pnl_pts"] * NIFTY_LOT - tr["costs_rs"]).all()


def test_signals_for_open_entries_come_from_previous_close():
    """A4 reads yesterday's signals: changing today's signal row must not change today's decision."""
    m = tiny_market()
    sig = pd.DataFrame({"ivp": 80.0, "vrp_ratio": 1.5, "rr25_z": 0.0, "bf25_z": 0.0, "atm_iv": 12.0,
                        "event_today": False}, index=m.index.index)
    base = options_eod.a4_vrp_filtered(m, sig)
    blocked = sig.copy()
    blocked.loc[D2, "ivp"] = 0  # only affects trades on D3
    t2 = options_eod.a4_vrp_filtered(m, blocked)
    assert set(base["entry_date"]) == {D1, D2, D3}
    assert set(t2["entry_date"]) == {D1, D2}


def test_a6_settles_at_intrinsic_on_expiry():
    m = tiny_market()
    sig = pd.DataFrame({"atm_iv": 12.0}, index=m.index.index)
    # only one strike exists, so the 20-delta "strangle" sells the 21000 straddle without wings
    tr = options_eod.a6_delta_strangle(m, sig, wings=False)
    assert len(tr) == 1 and tr.iloc[0]["entry_date"] == D1 and tr.iloc[0]["exit_date"] == D3
    s = DEFAULT_COSTS.opt_slippage
    call_intrinsic = 21250 - 21000
    assert tr.iloc[0]["pnl_pts"] == pytest.approx((100 - s - call_intrinsic) + (100 - s - 0))


# ---------------------------------------------------------------- metrics
def test_fixed_capital_metrics():
    cal = pd.bdate_range("2024-01-01", periods=10)
    tr = pd.DataFrame({"exit_date": [cal[2], cal[5]], "pnl_rs": [1000.0, -500.0], "costs_rs": [10.0, 10.0]})
    out = summarize_fixed_capital(tr, cal, 100_000)
    assert out["trades"] == 2 and out["win_rate_pct"] == 50
    assert out["total_pnl_rs"] == 500
    assert out["max_drawdown_pct"] == pytest.approx(100 * (100_500 / 101_000 - 1))


# ---------------------------------------------------------------- intraday ORB
def test_orb_long_hits_target():
    m = Market()
    days = pd.bdate_range("2024-03-01", periods=12)
    frames = []
    for i, d in enumerate(days):
        ts = pd.date_range(d + pd.Timedelta(hours=9, minutes=15), periods=375, freq="1min")
        base = np.full(375, 22000.0)
        width = 40.0 if i < 11 else 20.0  # last day has a narrow opening range so the filter lets it trade
        base[:15] = 22000 + np.tile([width / 2, -width / 2, 0], 5)
        if i == 11:
            base[15:] = np.linspace(22030, 22200, 360)  # breakout up and run to the target (2 x 20 above entry)
        frames.append(pd.DataFrame({"open": base, "high": base + 1, "low": base - 1, "close": base}, index=ts))
    m.minute = pd.concat(frames)
    sig = pd.DataFrame(index=days)
    tr = intraday.d1_orb(m, sig)
    assert len(tr) == 1
    t = tr.iloc[0]
    assert t["exits"] == "target" and t["pnl_pts"] > 0


# ---------------------------------------------------------------- equity
def test_momentum_holds_the_trending_stocks():
    days = pd.bdate_range("2020-01-01", periods=400)
    rng = np.random.default_rng(0)
    px = pd.DataFrame({f"S{i}": 100 * np.exp(np.cumsum(rng.normal(0.002 if i < 3 else -0.001, 0.01, 400)))
                       for i in range(10)}, index=days)
    m = Market()
    m.equities = px
    m.index = pd.DataFrame({"close": px.mean(axis=1)})
    rets = equity.e1_momentum(m, pd.DataFrame(), top=3, buffer=4)
    assert rets.iloc[300:].mean() > px.pct_change().iloc[300:].mean(axis=1).mean()


def test_a7_sells_the_previous_close_oi_walls_on_expiry_day():
    m = Market()
    m.index = pd.DataFrame({"open": [21000, 21000], "high": [21100, 21150], "low": [20900, 20950],
                            "close": [21000, 21050]}, index=[D2, D3])
    rows = []
    for d in (D2, D3):
        for k, typ, px in ((21200.0, "CE", (12, 30, 1, 2)), (20800.0, "PE", (10, 11, 0.5, 0.6))):
            o, h, l, c = px
            rows.append({"date": d, "expiry": D3, "strike": k, "opt_type": typ, "open": o, "high": h, "low": l,
                         "close": c, "settle": c, "volume": 100, "oi": 1000, "chg_oi": 0, "underlying": np.nan})
    m.set_options(pd.DataFrame(rows))
    sig = pd.DataFrame({"front_expiry": [D3, D3], "call_wall": [21200.0, np.nan], "put_wall": [20800.0, np.nan]},
                       index=[D2, D3])
    tr = options_eod.a7_oi_wall_strangle(m, sig)
    assert len(tr) == 1 and tr.iloc[0]["entry_date"] == D3
    se = DEFAULT_COSTS.opt_slippage_expiry
    # CE: high 30 >= 2 x 12 -> stopped at 24; PE: no stop, closes at 0.6
    assert tr.iloc[0]["exits"] == "stop,close"
    assert tr.iloc[0]["pnl_pts"] == pytest.approx(((12 - se) - (24 + se)) + ((10 - se) - (0.6 + se)))
