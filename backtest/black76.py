"""Vectorised Black-76 pricing, delta and implied volatility (numpy only)."""
import numpy as np

RATE = 0.065  # annual risk-free rate used for discounting and the forward


def _ncdf(x):
    from math import sqrt
    x = np.asarray(x, dtype=float)
    return 0.5 * (1.0 + _erf(x / sqrt(2.0)))


def _erf(x):
    # Abramowitz-Stegun 7.1.26 has 1.5e-7 error: plenty for option pricing on 0.05 ticks.
    sign = np.sign(x)
    x = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * x)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * np.exp(-x * x)
    return sign * y


def price(fwd, strike, t, vol, is_call, rate=RATE):
    fwd, strike, t, vol = (np.asarray(a, dtype=float) for a in (fwd, strike, t, vol))
    is_call = np.asarray(is_call, dtype=bool)
    t = np.maximum(t, 1e-6)
    vol = np.maximum(vol, 1e-6)
    sd = vol * np.sqrt(t)
    d1 = (np.log(fwd / strike) + 0.5 * sd * sd) / sd
    d2 = d1 - sd
    df = np.exp(-rate * t)
    call = df * (fwd * _ncdf(d1) - strike * _ncdf(d2))
    put = df * (strike * _ncdf(-d2) - fwd * _ncdf(-d1))
    return np.where(is_call, call, put)


def delta(fwd, strike, t, vol, is_call, rate=RATE):
    fwd, strike, t, vol = (np.asarray(a, dtype=float) for a in (fwd, strike, t, vol))
    t = np.maximum(t, 1e-6)
    sd = np.maximum(vol, 1e-6) * np.sqrt(t)
    d1 = (np.log(fwd / strike) + 0.5 * sd * sd) / sd
    df = np.exp(-rate * t)
    return np.where(np.asarray(is_call, dtype=bool), df * _ncdf(d1), df * (_ncdf(d1) - 1.0))


def implied_vol(px, fwd, strike, t, is_call, rate=RATE, lo=0.01, hi=3.0, iters=60):
    """Bisection; returns NaN where the price is outside no-arbitrage bounds."""
    px, fwd, strike, t = (np.asarray(a, dtype=float) for a in (px, fwd, strike, t))
    is_call = np.asarray(is_call, dtype=bool)
    lo_v = np.full(px.shape, lo)
    hi_v = np.full(px.shape, hi)
    for _ in range(iters):
        mid = 0.5 * (lo_v + hi_v)
        too_high = price(fwd, strike, t, mid, is_call, rate) > px
        hi_v = np.where(too_high, mid, hi_v)
        lo_v = np.where(too_high, lo_v, mid)
    iv = 0.5 * (lo_v + hi_v)
    intrinsic = np.exp(-rate * np.maximum(t, 0)) * np.where(is_call, np.maximum(fwd - strike, 0), np.maximum(strike - fwd, 0))
    bad = (px <= intrinsic + 1e-9) | (iv >= hi * 0.999) | (iv <= lo * 1.001) | ~np.isfinite(px) | (t <= 0)
    return np.where(bad, np.nan, iv)
