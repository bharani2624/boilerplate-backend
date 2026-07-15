# Cart + promo apply routes. session = authenticated user (JWT user_id → cart FK).
# Promo rejections return HTTP 200 with EvalResult.ok=false (spec §3 Phase 3).

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.middleware.auth import get_current_user
from src.services.promo_evaluator import cart_total, evaluate
from src.services.seed_data import get_product
from src.store.cart_store import CartStore
from src.store.promo_store import PromoStore

router = APIRouter()
cart_store = CartStore()
promo_store = PromoStore()


class AddItemRequest(BaseModel):
    product_id: str = Field(description="Catalog product id")
    qty: int = Field(gt=0, description="Quantity (> 0)")


class ApplyCodeRequest(BaseModel):
    code: str = Field(description="Promo code to apply")


async def _build_cart_payload(user_id: str) -> dict:
    items = await cart_store.list_items(user_id)
    state = await cart_store.get_state(user_id)
    applied = state.applied_code if state else None
    dtos = cart_store.items_to_dtos(items)
    total = cart_total(dtos)

    evaluation = None
    if applied and dtos:
        promo = await promo_store.get_by_code(applied)
        dto = promo_store.to_dto(promo) if promo else None
        evaluation = evaluate(dtos, applied, dto).to_dict()
    elif applied and not dtos:
        # Code still stored but cart empty — surface empty-cart evaluation
        evaluation = evaluate([], applied, None).to_dict()

    return {
        "items": [i.to_dict() for i in items],
        "applied_code": applied,
        "cart_total": str(total),
        "evaluation": evaluation,
    }


@router.get("")
async def get_cart(current_user: dict = Depends(get_current_user)):
    data = await _build_cart_payload(current_user["user_id"])
    return {"status": "success", "data": data}


@router.post("/items")
async def add_or_update_item(body: AddItemRequest, current_user: dict = Depends(get_current_user)):
    product = get_product(body.product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product not found: {body.product_id}")

    item = await cart_store.upsert_item(
        user_id=current_user["user_id"],
        product_id=product["product_id"],
        name=product["name"],
        unit_price=Decimal(str(product["unit_price"])),
        qty=body.qty,
    )
    cart = await _build_cart_payload(current_user["user_id"])
    return {"status": "success", "data": {"item": item.to_dict(), "cart": cart}}


@router.delete("/items/{product_id}")
async def remove_item(product_id: str, current_user: dict = Depends(get_current_user)):
    removed = await cart_store.remove_item(current_user["user_id"], product_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Cart item not found")
    cart = await _build_cart_payload(current_user["user_id"])
    return {"status": "success", "data": cart}


@router.post("/apply-code")
async def apply_code(body: ApplyCodeRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    items = await cart_store.list_items(user_id)
    dtos = cart_store.items_to_dtos(items)

    promo_row = await promo_store.get_by_code(body.code)
    promo_dto = promo_store.to_dto(promo_row) if promo_row else None
    result = evaluate(dtos, body.code, promo_dto)

    if result.ok:
        await cart_store.set_applied_code(user_id, result.code)

    # Always 200 for clean rejections (expired / min spend / unknown); client uses ok.
    return {"status": "success", "data": result.to_dict()}


@router.delete("/apply-code")
async def clear_code(current_user: dict = Depends(get_current_user)):
    await cart_store.clear_applied_code(current_user["user_id"])
    cart = await _build_cart_payload(current_user["user_id"])
    return {"status": "success", "data": cart}
