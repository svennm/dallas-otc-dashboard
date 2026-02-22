from app.models import TradeSide


def clamp_expiry(expiry_seconds: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, expiry_seconds))


def calculate_quote(
    *,
    mid_price: float,
    side: TradeSide,
    spread_buffer_bps: float,
    inventory_skew_bps: float,
    client_markup_bps: float,
) -> float:
    total_bps = spread_buffer_bps + inventory_skew_bps + client_markup_bps
    signed_bps = total_bps if side == TradeSide.buy else -total_bps
    return round(mid_price * (1 + (signed_bps / 10_000)), 2)


def inventory_skew_bps(desk_inventory: float, side: TradeSide) -> float:
    threshold = 250.0
    max_skew = 25.0
    normalized = max(-1.0, min(1.0, desk_inventory / threshold))

    if side == TradeSide.buy:
        raw = -normalized * max_skew
    else:
        raw = normalized * max_skew

    return round(raw, 2)
