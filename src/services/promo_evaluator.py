"""Promo evaluation pipeline (spec §3). Pure functions — no I/O.

evaluate(items, code, promo) -> EvalResult following the fixed 8-step pipeline.
Lookup of PromoDTO is the caller's job (store); this only decides eligibility + math.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from src.services.promo_dtos import CartItemDTO, EvalResult, PromoDTO
from src.services.promo_rules import RULES

TWO_DP = Decimal("0.01")
ZERO = Decimal("0")


def cart_total(items: list[CartItemDTO]) -> Decimal:
    total = sum((item.unit_price * item.qty for item in items), ZERO)
    return Decimal(total).quantize(TWO_DP, rounding=ROUND_HALF_UP)


def evaluate(
    items: list[CartItemDTO],
    code: str,
    promo: Optional[PromoDTO],
    *,
    now: Optional[datetime] = None,
) -> EvalResult:
    """Run the discount pipeline.

    Args:
        items: cart lines (empty cart is rejected before code checks).
        code: raw user input (normalized to uppercase for matching).
        promo: pre-loaded promo for the uppercased code, or None if not found.
        now: injectable clock for tests; defaults to UTC now.
    """
    total = cart_total(items)

    # 0. Empty cart — before code lookup (spec §4).
    if not items:
        return EvalResult(
            ok=False,
            code=None,
            cart_total=total,
            discount=ZERO,
            final_total=total,
            reason="Cart is empty",
        )

    normalized = (code or "").strip().upper()

    # 1. Not found / empty / whitespace → not recognized
    if not normalized or promo is None:
        return EvalResult(
            ok=False,
            code=None,
            cart_total=total,
            discount=ZERO,
            final_total=total,
            reason="Code not recognized",
        )

    # 2. Inactive
    if not promo.active:
        return EvalResult(
            ok=False,
            code=promo.code,
            cart_total=total,
            discount=ZERO,
            final_total=total,
            reason="Code no longer valid",
        )

    # 3. Expiry: expires_at is last valid instant; now <= expires_at is OK (UTC).
    clock = now if now is not None else datetime.now(timezone.utc)
    if promo.expires_at is not None:
        expires = promo.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if clock.tzinfo is None:
            clock = clock.replace(tzinfo=timezone.utc)
        if clock > expires:
            return EvalResult(
                ok=False,
                code=promo.code,
                cart_total=total,
                discount=ZERO,
                final_total=total,
                reason="Code expired",
            )

    # 4. Type-specific eligibility (min_spend lives here)
    rule = RULES.get(promo.type)
    if rule is None:
        return EvalResult(
            ok=False,
            code=promo.code,
            cart_total=total,
            discount=ZERO,
            final_total=total,
            reason="Code not recognized",
        )

    ok, reason = rule.eligible(promo, total)
    if not ok:
        return EvalResult(
            ok=False,
            code=promo.code,
            cart_total=total,
            discount=ZERO,
            final_total=total,
            reason=reason,
        )

    # 5–6. Compute + clamp to [0, cart_total]
    raw = rule.compute(promo, total, items)
    discount = max(min(raw, total), ZERO)
    discount = discount.quantize(TWO_DP, rounding=ROUND_HALF_UP)

    # 7–8. Final total
    final = (total - discount).quantize(TWO_DP, rounding=ROUND_HALF_UP)
    return EvalResult(
        ok=True,
        code=promo.code,
        cart_total=total,
        discount=discount,
        final_total=final,
        reason=None,
    )
