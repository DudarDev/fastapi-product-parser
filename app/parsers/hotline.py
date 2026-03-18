from bs4 import BeautifulSoup
from fastapi import HTTPException
from playwright.async_api import async_playwright
from app.parsers.base import BaseParser
# Імпортуємо обидві моделі!
from app.models.response import HotlineOfferInternal, OfferResponse
import re

class HotlineParser(BaseParser):
    # Додаємо параметри з ТЗ в аргументи функції
    async def parse_offers(self, url: str, price_sort: str = None, count_limit: int = None) -> list[OfferResponse]:
        
        # Вимога ТЗ: чистий URL без префіксів мови та слешу в кінці
        clean_url = url.replace("/ua/", "/").rstrip("/")
        
        internal_offers = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                await page.route("**/*", lambda route: route.abort() 
                    if route.request.resource_type in ["image", "font", "media", "stylesheet"] 
                    else route.continue_())

                # Використовуємо clean_url
                await page.goto(clean_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(2000)
                html_content = await page.content()
                await browser.close()

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Playwright error: {str(e)}")

        soup = BeautifulSoup(html_content, "lxml")
        if "just a moment" in soup.text.lower() or "cloudflare" in soup.text.lower():
            raise HTTPException(status_code=403, detail="Blocked by Cloudflare")

        title_elem = soup.select_one("h1.title__main, h1")
        global_title = title_elem.text.strip() if title_elem else "Невідомий товар"
        offer_blocks = soup.select(".list-body__item, .list-item, div[data-shop-id]")

        for block in offer_blocks:
            try:
                price_elem = block.select_one(".price__value, .price-value")
                if not price_elem: continue
                price = float(re.sub(r'[^\d]', '', price_elem.text))
                
                shop_elem = block.select_one(".shop__title, .shop__name, a[data-tracking-id='shop-name']")
                shop = shop_elem.get_text(strip=True) if shop_elem else "Магазин"
                
                link = block.select_one('a[href*="/go/price/"], a.btn--orange')
                full_url = f"https://hotline.ua{link['href']}" if link and link['href'].startswith('/') else clean_url
                is_used = "б/в" in block.get_text(separator=" ").lower()

                # Створюємо INTERNAL модель
                internal_offer = HotlineOfferInternal(
                    url=full_url,
                    original_url=clean_url,
                    title=global_title,
                    shop=shop,
                    price=price,
                    is_used=is_used
                )
                internal_offers.append(internal_offer)
            except:
                continue

        # Вимога ТЗ: Сортування (price_sort)
        if price_sort == "asc":
            internal_offers.sort(key=lambda x: x.price)
        elif price_sort == "desc":
            internal_offers.sort(key=lambda x: x.price, reverse=True)

        # Вимога ТЗ: Ліміт кількості (count_limit)
        if count_limit and count_limit > 0:
            internal_offers = internal_offers[:count_limit]

        # Конвертуємо Internal модель в External (OfferResponse), як вимагає ТЗ
        external_offers = [OfferResponse(**offer.model_dump()) for offer in internal_offers]

        if not external_offers:
            raise HTTPException(status_code=400, detail="Офери не знайдені")

        return external_offers

    async def parse_comments(self, url: str, date_to: str | None = None) -> list:
        return []