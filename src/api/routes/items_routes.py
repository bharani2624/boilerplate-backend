# Demo CRUD routes for the Item entity. Why this file exists: it's the reference
# implementation of the model -> store -> route pattern (see database/models/item.py
# and src/store/item_store.py) — copy this file's shape when adding a new resource
# during the builder round, then delete this one once you don't need the example.

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.middleware.auth import get_current_user
from src.store.item_store import ItemStore

router = APIRouter()
item_store = ItemStore()


class ItemCreateRequest(BaseModel):
    title: str = Field(description="Item title")
    description: Optional[str] = Field(default=None, description="Item description")


class ItemUpdateRequest(BaseModel):
    # Both optional so PUT can be a partial update — omit a field to leave it unchanged
    # (see ItemStore.update, which only overwrites fields that aren't None).
    title: Optional[str] = Field(default=None, description="New title")
    description: Optional[str] = Field(default=None, description="New description")


@router.get("")
def list_items(current_user: dict = Depends(get_current_user)):
    # Scoped to current_user["user_id"] — every route below does the same, so one
    # user can never see or touch another user's items.
    items = item_store.list_for_user(current_user["user_id"])
    data = [i.to_dict() for i in items]
    return {"status": "success", "data": data, "count": len(data)}


@router.post("")
def create_item(body: ItemCreateRequest, current_user: dict = Depends(get_current_user)):
    item = item_store.create(current_user["user_id"], body.title, body.description)
    return {"status": "success", "data": item.to_dict()}


@router.get("/{item_id}")
def get_item(item_id: str, current_user: dict = Depends(get_current_user)):
    item = item_store.get_for_user(item_id, current_user["user_id"])
    if not item:
        # Also returned when the item exists but belongs to someone else — deliberately
        # indistinguishable from "doesn't exist" so we don't leak which ids are in use.
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "success", "data": item.to_dict()}


@router.put("/{item_id}")
def update_item(item_id: str, body: ItemUpdateRequest, current_user: dict = Depends(get_current_user)):
    item = item_store.update(item_id, current_user["user_id"], body.title, body.description)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "success", "data": item.to_dict()}


@router.delete("/{item_id}")
def delete_item(item_id: str, current_user: dict = Depends(get_current_user)):
    ok = item_store.delete(item_id, current_user["user_id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "success", "data": {"id": item_id}}
