import asyncio
from fastapi import APIRouter, Query, HTTPException
from typing import Literal

from app.models.response import ProductOffersResponse
from app.parsers.hotline import HotlineParser
from app.utils.url_cleaner import clean_url
import httpx

router = APIRouter(tags=["Products"])

# Ініціалізуємо HTTP-клієнт, який будемо передавати в парсери
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
        # Обробка таймауту (Python 3.11+)
        if timeout_limit:
            async with asyncio.timeout(timeout_limit):
                offers = await parser.parse_offers(cleaned_url)
        else:
            offers = await parser.parse_offers(cleaned_url)
            
    except TimeoutError:
        # Завдання каже: "або нічого не віддаємо, або скільки встигли".
        # У випадку з Hotline краще віддати 408 (Request Timeout), бо якщо API не відповів, то оферів 0.
        raise HTTPException(status_code=408, detail="Request Timeout: Парсер не встиг обробити запит")
    except Exception as e:
        # Мапінг непередбачуваних помилок у 500
        raise HTTPException(status_code=500, detail=str(e))

    # Логіка сортування
    if price_sort == "asc":
        offers.sort(key=lambda x: x.price)
    elif price_sort == "desc":
        offers.sort(key=lambda x: x.price, reverse=True)

    # Логіка ліміту кількості
    if count_limit and count_limit > 0:
        offers = offers[:count_limit]

    # TODO: Тут ми пізніше додамо збереження в MongoDB (await mongodb.db.offers.insert_one(...))

    return ProductOffersResponse(
        url=cleaned_url,
        offers=offers
    )