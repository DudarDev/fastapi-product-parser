from pydantic import BaseModel, Field
from typing import List, Optional

# --- INTERNAL MODEL (Те, що ми парсимо з Hotline) ---
class HotlineOfferInternal(BaseModel):
    url: str
    original_url: Optional[str] = None
    title: str
    shop: str
    price: float
    is_used: bool

# --- EXTERNAL MODEL (Те, що вимагає ТЗ віддавати юзеру) ---
class OfferResponse(BaseModel):
    url: str
    original_url: Optional[str] = None
    title: str
    shop: str
    price: float
    is_used: bool

class ProductOffersResponse(BaseModel):
    url: str
    offers: List[OfferResponse]