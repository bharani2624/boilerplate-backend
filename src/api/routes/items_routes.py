# Demo CRUD routes for the Item entity. Why this file exists: it's the reference
# implementation of the model -> store -> route pattern (see database/models/item.py
# and src/store/item_store.py) — copy this file's shape when adding a new resource
# during the builder round, then delete this one once you don't need the example.

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.middleware.auth import get_current_user
from src.services.background_tasks import log_item_created
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
async def list_items(current_user: dict = Depends(get_current_user)):
    # Scoped to current_user["user_id"] — every route below does the same, so one
    # user can never see or touch another user's items.
    items = await item_store.list_for_user(current_user["user_id"])
    data = [i.to_dict() for i in items]
    return {"status": "success", "data": data, "count": len(data)}


@router.post("")
async def create_item(
    body: ItemCreateRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)
):
    item = await item_store.create(current_user["user_id"], body.title, body.description)
    # Fire-and-forget: whatever you'd do on item creation (webhook, search-index
    # update, notification) shouldn't make the caller wait for it. See
    # src/services/background_tasks.py for what this pattern is and isn't good for.
    background_tasks.add_task(log_item_created, user_id=current_user["user_id"], item_id=str(item.id))
    return {"status": "success", "data": item.to_dict()}


@router.get("/{item_id}")
async def get_item(item_id: str, current_user: dict = Depends(get_current_user)):
    item = await item_store.get_for_user(item_id, current_user["user_id"])
    if not item:
        # Also returned when the item exists but belongs to someone else — deliberately
        # indistinguishable from "doesn't exist" so we don't leak which ids are in use.
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "success", "data": item.to_dict()}


@router.put("/{item_id}")
async def update_item(item_id: str, body: ItemUpdateRequest, current_user: dict = Depends(get_current_user)):
    item = await item_store.update(item_id, current_user["user_id"], body.title, body.description)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "success", "data": item.to_dict()}


@router.delete("/{item_id}")
async def delete_item(item_id: str, current_user: dict = Depends(get_current_user)):
    ok = await item_store.delete(item_id, current_user["user_id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "success", "data": {"id": item_id}}
