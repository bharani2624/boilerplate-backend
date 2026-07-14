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
    title: Optional[str] = Field(default=None, description="New title")
    description: Optional[str] = Field(default=None, description="New description")


@router.get("")
def list_items(current_user: dict = Depends(get_current_user)):
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
