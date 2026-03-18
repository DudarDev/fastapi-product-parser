import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException
from typing import Literal

from app.models.response import ProductOffersResponse, ProductCommentsResponse
from app.parsers.hotline import HotlineParser
from app.parsers.comfy import ComfyParser
from app.parsers.brain import BrainParser
from app.utils.url_cleaner import clean_url
from app.db.mongo import db_instance
import httpx

router = APIRouter(tags=["Products"])
http_client = httpx.AsyncClient(timeout=10.0)

@router.get("/product/offers", response_model=ProductOffersResponse)
async def get_product_offers(
    url: str = Query(..., description="URL сторінки товару на Hotline"),
    timeout_limit: float | None = Query(None, description="Ліміт часу (секунди)"),
    count_limit: int | None = Query(None, description="Кількість оферів для повернення"),
    price_sort: Literal["asc", "desc"] | None = Query(None, description="Сортування за ціною")
):
    cleaned_url = clean_url(url)
    if "hotline.ua" not in cleaned_url:
        raise HTTPException(status_code=422, detail="URL повинен належати hotline.ua")

    parser = HotlineParser(client=http_client)
    offers = []
    try:
        if timeout_limit:
            async with asyncio.timeout(timeout_limit):
                offers = await parser.parse_offers(cleaned_url, price_sort, count_limit)
        else:
            offers = await parser.parse_offers(cleaned_url, price_sort, count_limit)
    except TimeoutError:
        raise HTTPException(status_code=408, detail="Request Timeout")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if offers:
        try:
            document = {
                "product_url": cleaned_url,
                "parsed_at": datetime.now(timezone.utc),
                "offers_count": len(offers),
                "offers": [offer.model_dump() for offer in offers]
            }
            await db_instance.db.hotline_products.insert_one(document)
        except Exception as e:
            print(f"Помилка запису в БД: {e}")

    return ProductOffersResponse(url=cleaned_url, offers=offers)

@router.get("/product/comments", response_model=ProductCommentsResponse)
async def get_product_comments(
    url: str = Query(..., description="URL продукту (Comfy або Brain)"),
    date_to: str | None = Query(None, description="До якої дати парсити відгуки (YYYY-MM-DD)")
):
    cleaned_url = clean_url(url)
    
    if "comfy.ua" in cleaned_url:
        parser = ComfyParser(client=http_client)
        source = "comfy"
    elif "brain.com.ua" in cleaned_url:
        parser = BrainParser(client=http_client)
        source = "brain"
    else:
        raise HTTPException(status_code=422, detail="Підтримуються тільки comfy.ua та brain.com.ua")

    try:
        comments = await parser.parse_comments(cleaned_url, date_to)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if comments or isinstance(comments, list):
        try:
            document = {
                "product_url": cleaned_url,
                "source": source,
                "parsed_at": datetime.now(timezone.utc),
                "comments_count": len(comments),
                "comments": [comment.model_dump() for comment in comments]
            }
            await db_instance.db.product_comments.insert_one(document)
        except Exception as e:
            print(f"Помилка запису в БД: {e}")

    return ProductCommentsResponse(url=cleaned_url, comments=comments)