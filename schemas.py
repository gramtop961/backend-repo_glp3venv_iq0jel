"""
Database Schemas for Canteen Management

Each Pydantic model represents a MongoDB collection (collection name is the lowercase of the class name).

This app manages:
- Menu items (name, category, price, availability)
- Customers (optional basic info)
- Orders (items, totals, status)
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class Menuitem(BaseModel):
    """
    Canteen menu items
    Collection name: "menuitem"
    """
    name: str = Field(..., description="Dish name")
    category: str = Field(..., description="Category like Snacks, Beverages, Main Course")
    price: float = Field(..., ge=0, description="Unit price")
    is_available: bool = Field(True, description="Available to order")
    description: Optional[str] = Field(None, description="Short description")


class Customer(BaseModel):
    """
    Customers placing orders
    Collection name: "customer"
    """
    name: str = Field(..., description="Customer name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")


class Orderitem(BaseModel):
    """
    Embedded order item representation (not a collection)
    """
    menu_item_id: str = Field(..., description="Referenced menu item _id as string")
    name: str = Field(..., description="Menu item name at time of order")
    price: float = Field(..., ge=0, description="Unit price at time of order")
    quantity: int = Field(..., ge=1, description="Quantity ordered")
    line_total: float = Field(..., ge=0, description="Calculated line total")


class Order(BaseModel):
    """
    Orders placed in the canteen
    Collection name: "order"
    """
    customer_name: str = Field(..., description="Name provided with the order")
    table_number: Optional[str] = Field(None, description="Table or pickup reference")
    items: List[Orderitem] = Field(..., description="Items included in the order")
    subtotal: float = Field(..., ge=0, description="Sum of line totals")
    tax: float = Field(..., ge=0, description="Tax amount")
    total: float = Field(..., ge=0, description="Final amount")
    status: str = Field("pending", description="pending | preparing | ready | completed | cancelled")
