import re
import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException
# ВИДАЛИЛИ: from playwright.async_api import async_playwright
from app.parsers.base import BaseParser
from app.models.response import HotlineOfferInternal, OfferResponse

class HotlineParser(BaseParser):
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.graphql_url = "https://hotline.ua/svc/frontend-api/graphql"

    def _extract_path(self, url: str) -> str:
        """Дістає шлях товару з URL (напр. 'apple-iphone-15-128gb')"""
        return url.rstrip('/').split('/')[-1]

    async def parse_offers(self, url: str, price_sort: str = None, count_limit: int = None) -> list[OfferResponse]:
        clean_url = url.strip()
        if clean_url.endswith("/"):
            clean_url = clean_url[:-1]
            
        internal_offers = []
        path = self._extract_path(clean_url)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Origin": "https://hotline.ua",
            "Referer": clean_url,
        }

        # =========================================================
        # ЕТАП 1: API-FIRST ПІДХІД (Швидкий запит до GraphQL)
        # =========================================================
        payload = {
            "operationName": "getOffers", # Приблизна назва, якщо зміниться - Fallback підстрахує
            "variables": {"path": path},
            "query": "query getOffers($path: String!) { product(path: $path) { prices { edges { node { price shop { name } url } } } } }"
        }

        try:
            print(f"🚀 Спроба API-запиту для: {clean_url}", flush=True)
            api_resp = await self.client.post(self.graphql_url, headers=headers, json=payload, timeout=5.0)
            
            if api_resp.status_code == 200:
                data = api_resp.json()
                edges = data.get("data", {}).get("product", {}).get("prices", {}).get("edges", [])
                
                for edge in edges:
                    node = edge.get("node", {})
                    shop_name = node.get("shop", {}).get("name", "Невідомий магазин")
                    price = float(node.get("price", 0))
                    offer_url = node.get("url", clean_url)
                    if offer_url.startswith('/'):
                        offer_url = f"https://hotline.ua{offer_url}"

                    internal_offers.append(HotlineOfferInternal(
                        url=offer_url, original_url=clean_url, title=path,
                        shop=shop_name, price=price, is_used=False
                    ))
        except Exception as e:
            print(f"⚠️ API-запит відхилено або структура не співпадає: {e}", flush=True)

        # =========================================================
        # ЕТАП 2: FALLBACK (ТВІЙ ПАРСИНГ DOM, але через HTTPX)
        # =========================================================
        if not internal_offers:
            print(f"🔄 Запуск Fallback HTML-парсингу для: {clean_url}", flush=True)
            try:
                # Замість Playwright робимо швидкий GET запит
                html_resp = await self.client.get(clean_url, headers=headers, timeout=10.0, follow_redirects=True)
                soup = BeautifulSoup(html_resp.text, "lxml")
                
                page_text = soup.text.lower()
                title = soup.title.string if soup.title else "Без заголовка"
                
                # Обробка підводних каменів (Cloudflare)
                if "just a moment" in page_text or "cloudflare" in page_text or "перевірка" in page_text:
                    raise HTTPException(status_code=429, detail="Too Many Requests: Cloudflare protection active.")

                # ТВОЯ КРУТА ЛОГІКА ЗБОРУ:
                buy_links = soup.select('a[href*="/go/price/"]')
                seen_shops = set()

                for link in buy_links:
                    try:
                        parent = link
                        for _ in range(6):
                            if parent.parent:
                                parent = parent.parent
                        
                        block_text = parent.get_text(separator=" ", strip=True)
                        full_url = f"https://hotline.ua{link['href']}" if link['href'].startswith('/') else link['href']

                        price_match = re.search(r'([\d\s]+)\s*[₴грн]', block_text, re.IGNORECASE)
                        if not price_match: continue
                        price = float(re.sub(r'[^\d]', '', price_match.group(1)))

                        shop = "Невідомий магазин"
                        img = parent.select_one('img[alt]')
                        if img and img.get('alt'):
                            shop = img['alt']
                        else:
                            strings = list(parent.stripped_strings)
                            if strings: shop = strings[0]

                        shop = re.sub(r'(?i)Магазин\s*', '', shop).strip() or "Невідомий магазин"

                        if shop in seen_shops and shop != "Невідомий магазин": continue
                        seen_shops.add(shop)

                        is_used = "б/в" in block_text.lower()

                        internal_offers.append(HotlineOfferInternal(
                            url=full_url, original_url=clean_url, title=title,
                            shop=shop, price=price, is_used=is_used
                        ))
                    except Exception:
                        continue
                        
            except HTTPException as he:
                raise he
            except Exception as e:
                print(f"❌ Помилка Fallback HTML-парсингу: {e}", flush=True)

        # Якщо після обох спроб нічого немає:
        if not internal_offers:
            raise HTTPException(status_code=400, detail="Офери не знайдені ані через API, ані через Fallback HTML.")

        # =========================================================
        # ЕТАП 3: ФІЛЬТРАЦІЯ І ПОВЕРНЕННЯ
        # =========================================================
        if price_sort == "asc":
            internal_offers.sort(key=lambda x: x.price)
        elif price_sort == "desc":
            internal_offers.sort(key=lambda x: x.price, reverse=True)

        if count_limit:
            internal_offers = internal_offers[:count_limit]

        return [OfferResponse(**offer.model_dump()) for offer in internal_offers]

    async def parse_comments(self, url: str, date_to: str | None = None) -> list:
        raise NotImplementedError("Тільки офери для Hotline")