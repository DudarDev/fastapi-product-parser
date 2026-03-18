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

                # Блокуємо тільки картинки і медіа для швидкості
                await page.route("**/*", lambda route: route.abort() 
                    if route.request.resource_type in ["image", "media", "font"] 
                    else route.continue_())

                print(f"⏳ Переходимо за адресою: {clean_url}", flush=True)
                await page.goto(clean_url, wait_until="load", timeout=60000)
                
                # Скролимо, щоб підвантажити ліниві елементи
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
        
        print(f"🔍 Заголовок: '{title}'", flush=True)
        
        if "just a moment" in page_text or "cloudflare" in page_text or "перевірка" in page_text:
            print("🛑 НАС ЗАБЛОКУВАВ CLOUDFLARE!", flush=True)
            raise HTTPException(
                status_code=429, 
                detail="Too Many Requests: Cloudflare protection active."
            )

        # 🚀 НОВІ СЕЛЕКТОРИ З ТВОЇХ СКРІНШОТІВ (використовуємо стабільні атрибути)
        offer_blocks = soup.select('div[offer-index], div[event-category="Pages Product Prices"]')
        
        # Якщо раптом атрибутів немає, шукаємо всі кнопки "Купити" і беремо їх батьківські блоки
        if not offer_blocks:
            buy_links = soup.select('a[href*="/go/price/"]')
            for link in buy_links:
                parent = link.parent
                # Піднімаємося на кілька рівнів вгору, щоб захопити весь рядок магазину
                for _ in range(4):
                    if parent and parent.name == 'div' and len(parent.get_text(strip=True)) > 10:
                        offer_blocks.append(parent)
                        break
                    if parent: parent = parent.parent

        print(f"📦 Знайдено блоків з товарами: {len(offer_blocks)}", flush=True)

        seen_shops = set()

        for block in offer_blocks:
            try:
                block_text = block.get_text(separator=" ", strip=True)
                
                # 1. Знаходимо URL
                link = block.select_one('a[href*="/go/price/"]')
                if not link: continue
                full_url = f"https://hotline.ua{link['href']}" if link['href'].startswith('/') else link['href']

                # 2. Витягуємо ціну БУДЬ-ЗВІДКИ з тексту блоку за допомогою Regex (найбільш безвідмовний метод)
                price_match = re.search(r'([\d\s]+)\s*[₴грн]', block_text, re.IGNORECASE)
                if not price_match: continue
                clean_price_str = re.sub(r'[^\d]', '', price_match.group(1))
                if not clean_price_str: continue
                price = float(clean_price_str)

                # 3. Витягуємо назву магазину
                shop = "Невідомий магазин"
                img = block.select_one('img[alt]')
                if img and img.get('alt'):
                    shop = img['alt']
                else:
                    # Беремо перший текстовий елемент у блоці (це майже завжди назва магазину)
                    strings = list(block.stripped_strings)
                    if strings:
                        shop = strings[0]
                        if "Акція" in shop and len(strings) > 1:
                            shop = strings[1] # Якщо перше слово "Акція", беремо наступне

                shop = re.sub(r'(?i)Магазин\s*', '', shop).strip() or "Невідомий магазин"

                # Фільтруємо дублікати
                if shop in seen_shops and shop != "Невідомий магазин": continue
                seen_shops.add(shop)

                # 4. Стан
                is_used = "б/в" in block_text.lower()

                internal_offers.append(HotlineOfferInternal(
                    url=full_url, original_url=clean_url, title=title,
                    shop=shop, price=price, is_used=is_used
                ))
            except Exception as e:
                continue

        if not internal_offers:
            print(f"⚠️ Офери не знайдені в HTML.", flush=True)
            raise HTTPException(status_code=400, detail=f"Офери не знайдені. Дизайн не розпізнано.")

        # Сортування
        if price_sort == "asc":
            internal_offers.sort(key=lambda x: x.price)
        elif price_sort == "desc":
            internal_offers.sort(key=lambda x: x.price, reverse=True)

        # Ліміт
        if count_limit:
            internal_offers = internal_offers[:count_limit]

        return [OfferResponse(**offer.model_dump()) for offer in internal_offers]

    async def parse_comments(self, url: str, date_to: str | None = None) -> list:
        raise NotImplementedError("Тільки офери для Hotline")