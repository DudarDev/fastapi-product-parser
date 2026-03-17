from app.parsers.base import BaseParser
from app.models.response import OfferResponse
from app.models.internal.hotline import HotlineRawOffer
import httpx
import asyncio

class HotlineParser(BaseParser):
    async def parse_offers(self, url: str) -> list[OfferResponse]:
        # В реальності тут би був запит типу:
        # response = await self.client.get(f"{url}/api/some-endpoint")
        # data = response.json()
        
        # Але оскільки реальний API Hotline захищений від ботів, 
        # для демонстрації архітектури ми замок'аємо (зімітуємо) відповідь парсера, 
        # ніби ми її щойно отримали з HTML/API.
        
        # Імітуємо затримку мережі
        await asyncio.sleep(1)
        
        # Сирі дані "з джерела"
        mock_raw_data = [
            {
                "shop_name": "ELMIR.UA",
                "price_raw": 3278.0,
                "title": "Arena Рюкзак Arena Fast Urban 3.0",
                "condition": "new",
                "redirect_url": "/go/price/13841037622",
                "direct_url": "https://elmir.ua/ua/travel_backpacks/backpack.html"
            },
            {
                "shop_name": "Rozetka",
                "price_raw": 3500.0,
                "title": "Arena Рюкзак Arena Fast Urban 3.0 Б/В",
                "condition": "used",
                "redirect_url": "/go/price/999999999",
                "direct_url": None
            }
        ]
        
        offers: list[OfferResponse] = []
        
        # Ось він - правильний мапінг з поділом моделей!
        for item in mock_raw_data:
            # 1. Валідуємо сирі дані через Internal модель
            raw_offer = HotlineRawOffer(**item)
            
            # 2. Перекладаємо у Response модель
            full_url = f"https://hotline.ua{raw_offer.redirect_url}" if raw_offer.redirect_url else ""
            
            offers.append(OfferResponse(
                url=full_url,
                original_url=raw_offer.direct_url,
                title=raw_offer.title or "Без назви",
                shop=raw_offer.shop_name or "Невідомо",
                price=float(raw_offer.price_raw) if raw_offer.price_raw else 0.0,
                is_used=True if raw_offer.condition == "used" else False
            ))
            
        return offers

    async def parse_comments(self, url: str, date_to: str | None = None) -> list:
        # По завданню Hotline парсить тільки офери
        raise NotImplementedError("Hotline parser supports only offers")