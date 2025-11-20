import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Menuitem, Order, Orderitem, Customer

app = FastAPI(title="Canteen Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helpers
class IDModel(BaseModel):
    id: str


def object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


@app.get("/")
def read_root():
    return {"message": "Canteen Management Backend is running"}


# Menu endpoints
@app.post("/api/menu", response_model=dict)
def add_menu_item(item: Menuitem):
    inserted_id = create_document("menuitem", item)
    return {"id": inserted_id}


@app.get("/api/menu")
def list_menu():
    items = get_documents("menuitem")
    # Convert ObjectId to string
    for it in items:
        it["_id"] = str(it["_id"])
    return {"items": items}


@app.patch("/api/menu/{item_id}")
def update_menu_item(item_id: str, payload: dict):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    res = db["menuitem"].update_one({"_id": object_id(item_id)}, {"$set": payload})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"updated": True}


@app.delete("/api/menu/{item_id}")
def delete_menu_item(item_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    res = db["menuitem"].delete_one({"_id": object_id(item_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"deleted": True}


# Orders endpoints
class CreateOrder(BaseModel):
    customer_name: str
    table_number: Optional[str] = None
    items: List[dict]  # expects: [{menu_item_id, quantity}]


@app.post("/api/orders")
def create_order(payload: CreateOrder):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    order_items: List[Orderitem] = []
    subtotal = 0.0

    for i in payload.items:
        mid = i.get("menu_item_id")
        qty = int(i.get("quantity", 1))
        doc = db["menuitem"].find_one({"_id": object_id(mid), "is_available": True})
        if not doc:
            raise HTTPException(status_code=400, detail=f"Menu item {mid} unavailable")
        price = float(doc.get("price", 0))
        name = doc.get("name")
        line_total = price * qty
        subtotal += line_total
        order_items.append(Orderitem(menu_item_id=str(doc["_id"]), name=name, price=price, quantity=qty, line_total=line_total))

    tax = round(subtotal * 0.05, 2)
    total = round(subtotal + tax, 2)

    order_doc = Order(customer_name=payload.customer_name, table_number=payload.table_number, items=order_items, subtotal=round(subtotal, 2), tax=tax, total=total)
    order_id = create_document("order", order_doc)
    return {"id": order_id, "subtotal": order_doc.subtotal, "tax": order_doc.tax, "total": order_doc.total}


@app.get("/api/orders")
def list_orders():
    orders = get_documents("order")
    for o in orders:
        o["_id"] = str(o["_id"])
    return {"orders": orders}


@app.patch("/api/orders/{order_id}")
def update_order_status(order_id: str, payload: dict):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    status = payload.get("status")
    if status not in ["pending", "preparing", "ready", "completed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    res = db["order"].update_one({"_id": object_id(order_id)}, {"$set": {"status": status}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"updated": True}


# Simple dashboard metrics
@app.get("/api/metrics")
def metrics():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    total_menu = db["menuitem"].count_documents({})
    pending_orders = db["order"].count_documents({"status": {"$in": ["pending", "preparing"]}})
    completed_today = db["order"].count_documents({"status": "completed"})
    return {"total_menu": total_menu, "active_orders": pending_orders, "completed_orders": completed_today}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
