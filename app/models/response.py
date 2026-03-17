from pydantic import BaseModel, Field
from datetime import datetime

# --- Офери (Hotline) ---

class OfferResponse(BaseModel):
    url: str
    original_url: str | None = None
    title: str = ""
    shop: str = ""
    price: float = 0.0
    is_used: bool = False

class ProductOffersResponse(BaseModel):
    url: str
    offers: list[OfferResponse] = Field(default_factory=list)

# --- Відгуки (Comfy, Brain) ---

class CommentResponse(BaseModel):
    rating: float | None = None
    advantages: str | None = None
    shortcomings: str | None = None
    comment: str | None = None
    created_at: datetime | None = None

class ProductCommentsResponse(BaseModel):
    url: str
    comments: list[CommentResponse] = Field(default_factory=list)