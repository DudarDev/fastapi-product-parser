from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class HotlineOfferInternal(BaseModel):
    url: str
    original_url: Optional[str] = None
    title: str
    shop: str
    price: float
    is_used: bool

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

class CommentResponse(BaseModel):
    rating: Optional[float] = None
    advantages: Optional[str] = None
    shortcomings: Optional[str] = None
    comment: Optional[str] = None
    created_at: Optional[datetime] = None

class ProductCommentsResponse(BaseModel):
    url: str
    comments: List[CommentResponse] = Field(default_factory=list)