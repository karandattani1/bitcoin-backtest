"""Indian transaction costs, 2026 schedule (STT raised from 1 Apr 2026).

The same 2026 rates are applied to the whole history. That is deliberately conservative:
it shows whether a strategy survives the costs you would pay today.
"""
from dataclasses import dataclass

NIFTY_LOT = 65  # from Jan 2026; P&L for the whole history is expressed per current lot


@dataclass(frozen=True)
class CostModel:
    brokerage_per_order: float = 20.0
    # options (charged on premium turnover)
    opt_stt_sell: float = 0.0015
    opt_exchange: float = 0.0003503
    opt_stamp_buy: float = 0.00003
    # futures (charged on notional turnover)
    fut_stt_sell: float = 0.0005
    fut_exchange: float = 0.0000173
    fut_stamp_buy: float = 0.00002
    # common
    sebi_fee: float = 10 / 1e7          # Rs 10 per crore
    gst: float = 0.18                   # on brokerage + exchange + SEBI fees
    # slippage, in index/premium points per order
    opt_slippage: float = 0.5
    opt_slippage_expiry: float = 1.0
    fut_slippage: float = 1.0
    # equity delivery (charged on turnover), brokerage assumed zero for delivery
    eq_stt: float = 0.001               # both sides
    eq_exchange: float = 0.0000297
    eq_stamp_buy: float = 0.00015
    eq_slippage: float = 0.0005         # 5 bps per side

    def option_order(self, price: float, qty: int, side: str, expiry_day: bool = False) -> float:
        """Rupee cost of one option order (excluding slippage, which is applied to the fill price)."""
        turnover = price * qty
        exch, sebi = turnover * self.opt_exchange, turnover * self.sebi_fee
        stt = turnover * self.opt_stt_sell if side == "sell" else 0.0
        stamp = turnover * self.opt_stamp_buy if side == "buy" else 0.0
        return self.brokerage_per_order + exch + sebi + stt + stamp + self.gst * (self.brokerage_per_order + exch + sebi)

    def future_order(self, price: float, qty: int, side: str) -> float:
        turnover = price * qty
        exch, sebi = turnover * self.fut_exchange, turnover * self.sebi_fee
        stt = turnover * self.fut_stt_sell if side == "sell" else 0.0
        stamp = turnover * self.fut_stamp_buy if side == "buy" else 0.0
        return self.brokerage_per_order + exch + sebi + stt + stamp + self.gst * (self.brokerage_per_order + exch + sebi)

    def equity_rate(self, side: str) -> float:
        """Cost as a fraction of turnover for an equity delivery trade, including slippage."""
        rate = self.eq_stt + self.eq_exchange * (1 + self.gst) + self.sebi_fee * (1 + self.gst) + self.eq_slippage
        return rate + (self.eq_stamp_buy if side == "buy" else 0.0)

    def slip(self, expiry_day: bool) -> float:
        return self.opt_slippage_expiry if expiry_day else self.opt_slippage


DEFAULT_COSTS = CostModel()
