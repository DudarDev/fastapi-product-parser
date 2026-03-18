import re
from bs4 import BeautifulSoup
from fastapi import HTTPException
from playwright.async_api import async_playwright
from app.parsers.base import BaseParser
from app.models.response import HotlineOfferInternal, OfferResponse

class HotlineParser(BaseParser):
    async def parse_offers(self, url: str, price_sort: str = None, count_limit: int = None) -> list[OfferResponse]:
        clean_url = url.strip()
        if clean_url.endswith("/"):
            clean_url = clean_url[:-1]
            
        internal_offers = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080}
                )
                page = await context.new_page()

                # Більше НЕ блокуємо ресурси. Дозволяємо Vue/React завантажити все, щоб уникнути зависань.
                print(f"⏳ Переходимо за адресою: {clean_url}", flush=True)
                
                # Чекаємо networkidle замість domcontentloaded
                await page.goto(clean_url, wait_until="networkidle", timeout=60000)
                
                # Скролимо сторінку
                await page.evaluate("window.scrollBy(0, 500)")
                await page.wait_for_timeout(1000)
                await page.evaluate("window.scrollBy(0, 1000)")
                await page.wait_for_timeout(3000)
                
                html_content = await page.content()
                await browser.close()

        except Exception as e:
            print(f"❌ Помилка браузера: {e}", flush=True)
            raise HTTPException(status_code=500, detail="Помилка при завантаженні сторінки")

        soup = BeautifulSoup(html_content, "lxml")
        page_text = soup.text.lower()
        title = soup.title.string if soup.title else "Без заголовка"
        
        if "just a moment" in page_text or "cloudflare" in page_text or "перевірка" in page_text:
            raise HTTPException(status_code=429, detail="Too Many Requests: Cloudflare protection active.")

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
            except Exception as e:
                continue

        if not internal_offers:
            raise HTTPException(status_code=400, detail=f"Офери не знайдені. Бот побачив сторінку: {title}")

        if price_sort == "asc":
            internal_offers.sort(key=lambda x: x.price)
        elif price_sort == "desc":
            internal_offers.sort(key=lambda x: x.price, reverse=True)

        if count_limit:
            internal_offers = internal_offers[:count_limit]

        return [OfferResponse(**offer.model_dump()) for offer in internal_offers]

    async def parse_comments(self, url: str, date_to: str | None = None) -> list:
        raise NotImplementedError("Тільки офери для Hotline")