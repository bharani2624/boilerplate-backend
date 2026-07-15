"""Discount rule strategies: one class per promo type, registered in RULES.

Adding a new type = implement DiscountRule + one entry in RULES + PromoType enum.
Do not add type branches to evaluate() itself.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from src.services.promo_dtos import CartItemDTO, PromoDTO

TWO_DP = Decimal("0.01")


class DiscountRule(Protocol):
    def eligible(self, promo: PromoDTO, cart_total: Decimal) -> tuple[bool, str | None]:
        """Returns (True, None) or (False, reason)."""
        ...

    def compute(self, promo: PromoDTO, cart_total: Decimal, items: list[CartItemDTO]) -> Decimal:
        """Raw discount amount BEFORE cart-total clamping."""
        ...


def _check_min_spend(promo: PromoDTO, cart_total: Decimal) -> tuple[bool, str | None]:
    # Inclusive: cart_total == min_spend is eligible (spec §4).
    if promo.min_spend is not None and cart_total < promo.min_spend:
        return False, f"Minimum spend of ${promo.min_spend} not met"
    return True, None


class PercentOffRule:
    def eligible(self, promo: PromoDTO, cart_total: Decimal) -> tuple[bool, str | None]:
        return _check_min_spend(promo, cart_total)

    def compute(self, promo: PromoDTO, cart_total: Decimal, items: list[CartItemDTO]) -> Decimal:
        raw = cart_total * (promo.value / Decimal(100))
        # Round once at end of compute, not per-item (spec §4).
        return raw.quantize(TWO_DP, rounding=ROUND_HALF_UP)


class FixedOffRule:
    def eligible(self, promo: PromoDTO, cart_total: Decimal) -> tuple[bool, str | None]:
        return _check_min_spend(promo, cart_total)

    def compute(self, promo: PromoDTO, cart_total: Decimal, items: list[CartItemDTO]) -> Decimal:
        return Decimal(promo.value).quantize(TWO_DP, rounding=ROUND_HALF_UP)


RULES: dict[str, DiscountRule] = {
    "percent": PercentOffRule(),
    "fixed": FixedOffRule(),
}
