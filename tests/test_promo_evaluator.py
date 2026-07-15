"""Unit tests for the promo evaluation pipeline (spec §4 edge cases).

No DB, no HTTP — pure evaluate() against in-memory DTOs.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.services.promo_dtos import CartItemDTO, PromoDTO
from src.services.promo_evaluator import cart_total, evaluate


def _item(price: str, qty: int = 1, product_id: str = "p1", name: str = "Thing") -> CartItemDTO:
    return CartItemDTO(
        product_id=product_id,
        name=name,
        unit_price=Decimal(price),
        qty=qty,
    )


def _percent(
    code: str = "SAVE10",
    value: str = "10",
    min_spend: str | None = None,
    expires_at: datetime | None = None,
    active: bool = True,
) -> PromoDTO:
    return PromoDTO(
        code=code,
        type="percent",
        value=Decimal(value),
        min_spend=Decimal(min_spend) if min_spend is not None else None,
        expires_at=expires_at,
        active=active,
    )


def _fixed(
    code: str = "FIVEOFF",
    value: str = "5.00",
    min_spend: str | None = None,
    expires_at: datetime | None = None,
    active: bool = True,
) -> PromoDTO:
    return PromoDTO(
        code=code,
        type="fixed",
        value=Decimal(value),
        min_spend=Decimal(min_spend) if min_spend is not None else None,
        expires_at=expires_at,
        active=active,
    )


# ---------------------------------------------------------------------------
# Empty cart / unknown code
# ---------------------------------------------------------------------------


def test_empty_cart_rejected_before_code_lookup():
    result = evaluate([], "SAVE10", _percent())
    assert result.ok is False
    assert result.reason == "Cart is empty"
    assert result.discount == Decimal("0")
    assert result.final_total == Decimal("0")


def test_unknown_code_rejected():
    result = evaluate([_item("50.00")], "NOPE", None)
    assert result.ok is False
    assert result.reason == "Code not recognized"


def test_empty_string_code_rejected():
    result = evaluate([_item("50.00")], "   ", None)
    assert result.ok is False
    assert result.reason == "Code not recognized"


def test_case_insensitive_code_uses_promo_when_provided():
    # Caller uppercases for lookup; promo is still applied when found.
    promo = _percent(code="SAVE10")
    result = evaluate([_item("100.00")], "save10", promo)
    assert result.ok is True
    assert result.code == "SAVE10"
    assert result.discount == Decimal("10.00")
    assert result.final_total == Decimal("90.00")


# ---------------------------------------------------------------------------
# Active / expiry
# ---------------------------------------------------------------------------


def test_inactive_code_rejected():
    promo = _percent(active=False)
    result = evaluate([_item("100.00")], "SAVE10", promo)
    assert result.ok is False
    assert result.reason == "Code no longer valid"


def test_expires_at_exactly_now_still_valid():
    boundary = datetime(2026, 7, 15, 23, 59, 59, tzinfo=timezone.utc)
    promo = _percent(expires_at=boundary)
    result = evaluate([_item("100.00")], "SAVE10", promo, now=boundary)
    assert result.ok is True
    assert result.discount == Decimal("10.00")


def test_one_second_past_expires_at_rejected():
    boundary = datetime(2026, 7, 15, 23, 59, 59, tzinfo=timezone.utc)
    promo = _percent(expires_at=boundary)
    result = evaluate(
        [_item("100.00")],
        "SAVE10",
        promo,
        now=boundary + timedelta(seconds=1),
    )
    assert result.ok is False
    assert result.reason == "Code expired"


# ---------------------------------------------------------------------------
# Min spend (inclusive boundary)
# ---------------------------------------------------------------------------


def test_cart_exactly_equals_min_spend_eligible():
    promo = _fixed(value="5.00", min_spend="50.00")
    result = evaluate([_item("50.00")], "FIVEOFF", promo)
    assert result.ok is True
    assert result.discount == Decimal("5.00")
    assert result.final_total == Decimal("45.00")


def test_cart_one_cent_under_min_spend_rejected():
    promo = _fixed(value="5.00", min_spend="50.00")
    result = evaluate([_item("49.99")], "FIVEOFF", promo)
    assert result.ok is False
    assert result.reason == "Minimum spend of $50.00 not met"
    assert result.discount == Decimal("0")
    assert result.final_total == Decimal("49.99")


# ---------------------------------------------------------------------------
# Clamp: discount never exceeds cart / total never negative
# ---------------------------------------------------------------------------


def test_fixed_discount_larger_than_cart_clamps_to_cart_total():
    # $150 off on a $100 cart (min spend met) → discount 100, final 0
    promo = _fixed(value="150.00", min_spend="100.00")
    result = evaluate([_item("100.00")], "FIVEOFF", promo)
    assert result.ok is True
    assert result.discount == Decimal("100.00")
    assert result.final_total == Decimal("0.00")


def test_percent_discount_never_negative():
    promo = _percent(value="100")
    result = evaluate([_item("33.33")], "SAVE10", promo)
    assert result.ok is True
    assert result.discount == Decimal("33.33")
    assert result.final_total == Decimal("0.00")


# ---------------------------------------------------------------------------
# Rounding (percent fractional cents)
# ---------------------------------------------------------------------------


def test_percent_off_fractional_cent_rounds_half_up():
    # 10% of 9.99 = 0.999 → ROUND_HALF_UP → 1.00
    promo = _percent(value="10")
    result = evaluate([_item("9.99")], "SAVE10", promo)
    assert result.ok is True
    assert result.discount == Decimal("1.00")
    assert result.final_total == Decimal("8.99")


def test_percent_off_standard_path():
    promo = _percent(value="10")
    items = [_item("25.00", qty=2)]  # 50.00
    result = evaluate(items, "SAVE10", promo)
    assert result.cart_total == Decimal("50.00")
    assert result.discount == Decimal("5.00")
    assert result.final_total == Decimal("45.00")


# ---------------------------------------------------------------------------
# cart_total helper
# ---------------------------------------------------------------------------


def test_cart_total_sums_line_items():
    items = [_item("12.00", qty=2), _item("3.00", qty=1, product_id="p2")]
    assert cart_total(items) == Decimal("27.00")


# ---------------------------------------------------------------------------
# Re-apply / idempotent success shape
# ---------------------------------------------------------------------------


def test_evaluate_idempotent_same_inputs():
    promo = _fixed(value="5.00", min_spend="20.00")
    items = [_item("30.00")]
    a = evaluate(items, "FIVEOFF", promo)
    b = evaluate(items, "FIVEOFF", promo)
    assert a == b
    assert a.ok is True
