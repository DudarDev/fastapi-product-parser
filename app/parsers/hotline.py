from bs4 import BeautifulSoup
from fastapi import HTTPException
import re
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from app.parsers.base import BaseParser
from app.models.response import OfferResponse
from app.models.internal.hotline import HotlineRawOffer

class HotlineParser(BaseParser):
    async def parse_offers(self, url: str) -> list[OfferResponse]:
        offers_data: list[OfferResponse] = []
        html_content = ""

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--window-size=1920,1080",
                    ]
                )
                
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    java_script_enabled=True
                )
                
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                """)
                
                page = await context.new_page()
                await page.route("**/*.{png,jpg,jpeg,webp,svg,gif,woff,woff2}", lambda route: route.abort())
                
                response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                if response and response.status in [403, 503]:
                    await browser.close()
                    raise HTTPException(status_code=429, detail="Hotline заблокував запит (Cloudflare).")
                elif response and response.status == 404:
                    await browser.close()
                    raise HTTPException(status_code=404, detail="Товар не знайдено на Hotline.")
                    
                # Скролимо сторінку
                await page.evaluate("window.scrollBy(0, 500)")
                await page.wait_for_timeout(1000)
                await page.evaluate("window.scrollBy(0, 1500)")
                
                # ЖОРСТКА ПАУЗА: Чекаємо 6 секунд, щоб Vue.js точно відмалював ціни на повільному сервері
                await page.wait_for_timeout(6000)
                
                # Пробуємо дочекатися хоча б якоїсь ціни
                try:
                    await page.wait_for_selector(".price__value, .price-value, [data-price]", timeout=5000)
                except Exception:
                    pass 
                
                html_content = await page.content()
                await browser.close()
                
        except PlaywrightTimeoutError:
            raise HTTPException(status_code=408, detail="Request Timeout: Playwright не встиг завантажити сторінку")
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Playwright error: {str(e)}")

        soup = BeautifulSoup(html_content, "lxml")
        
        global_title_elem = soup.select_one("h1.title__main, h1")
        global_title = global_title_elem.text.strip() if global_title_elem else "Товар без назви"
        page_title = soup.title.text.strip() if soup.title else "Без <title>"
        
        if "cf-browser-verification" in html_content.lower() or "just a moment" in page_title.lower():
            raise HTTPException(status_code=429, detail="Cloudflare капча.")

        # Максимально широкий пошук блоків з цінами
        offer_blocks = soup.select(".list-body__item, .list__item, .price__item, .list-item, div[data-shop-id], .offers-item, .price-line") 
        
        if not offer_blocks:
            # Шукаємо БУДЬ-ЯКУ кнопку з текстом "Купити" або "В магазин"
            buy_buttons = soup.find_all(lambda tag: tag.name in ["a", "button"] and any(word in tag.get_text(strip=True).lower() for word in ["купити", "в магазин", "перейти"]))
            
            for btn in buy_buttons:
                parent = btn.parent
                for _ in range(8):
                    if not parent or parent.name in ['body', 'html']:
                        break
                    block_text = parent.get_text(separator=" ", strip=True).lower()
                    if re.search(r'\d', block_text) and ('грн' in block_text or '₴' in block_text):
                        if parent not in offer_blocks:
                            offer_blocks.append(parent)
                        break
                    parent = parent.parent

        seen_shops = set()
        
        for block in offer_blocks:
            # Пошук посилання
            link_elem = block.find("a", href=re.compile(r"(/yp/|/go/price/|/goto/|/transit/|/out/)"))
            if not link_elem:
                link_elem = block.select_one("a.btn--orange, a.btn-orange, button.btn--orange")
            if not link_elem:
                # Якщо посилання немає, шукаємо просто будь-яке посилання в блоці, де є ціна
                link_elem = block.find("a")
                if not link_elem:
                    continue 
                
            redirect_url = link_elem.get("href", "")
            
            # Назва магазину
            shop_name = "Невідомий магазин"
            shop_elem = block.select_one("a[data-tracking-id='shop-name'], .shop__title, .shop-title, .shop__name")
            if shop_elem and shop_elem.get_text(strip=True):
                shop_name = shop_elem.get_text(strip=True)
            else:
                shop_link = block.find("a", href=re.compile(r"(/shop/|/sr/)"))
                if shop_link:
                    img = shop_link.find("img", alt=True)
                    if img and img.get("alt"):
                        shop_name = img.get("alt").strip()
                    else:
                        text = shop_link.get_text(strip=True)
                        if text: shop_name = text
                else:
                    for img in block.find_all("img", alt=True):
                        alt = img.get("alt").strip()
                        stop_words = ["зображення", "image", "logo", "логотип", "купити", "відгук", "акція", global_title.lower()]
                        if alt and len(alt) > 2 and not any(sw in alt.lower() for sw in stop_words):
                            shop_name = alt
                            break
            
            shop_name = re.sub(r'Магазин\s*', '', shop_name, flags=re.IGNORECASE).strip()
            if not shop_name or len(shop_name) < 2:
                shop_name = "Невідомий магазин"
                
            # Захист від дублікатів за назвою магазину
            if shop_name in seen_shops and shop_name != "Невідомий магазин":
                continue

            # Ціна
            price_raw = 0.0
            price_elem = block.select_one(".price__value, .price-value, .item-price, span.price")
            
            if price_elem:
                clean_price_str = re.sub(r'[^\d.]', '', price_elem.text.replace(',', '.'))
                try: price_raw = float(clean_price_str)
                except ValueError: pass
            
            if price_raw == 0.0:
                currency_nodes = block.find_all(string=re.compile(r'(грн|₴)', re.IGNORECASE))
                for node in currency_nodes:
                    if node.parent:
                        parent_text = node.parent.get_text(separator=" ", strip=True).replace(" ", "").replace("\xa0", "")
                        match = re.search(r'(\d+(?:[.,]\d+)?)(?:грн|₴)', parent_text, re.IGNORECASE)
                        if match:
                            clean_price_str = match.group(1).replace(',', '.')
                            try: 
                                price_raw = float(clean_price_str)
                                break  
                            except ValueError: pass

            condition = "used" if "б/в" in block.get_text(separator=" ").lower() or "уцінка" in block.get_text(separator=" ").lower() else "new"
            
            if price_raw > 0:
                seen_shops.add(shop_name)
                
                full_url = f"https://hotline.ua{redirect_url}" if redirect_url and redirect_url.startswith("/") else redirect_url
                
                offers_data.append(OfferResponse(
                    url=full_url,
                    original_url=None,
                    title=global_title,
                    shop=shop_name,
                    price=float(price_raw),
                    is_used=True if condition == "used" else False
                ))

        if not offers_data:
            # ДЕТЕКТИВ: Виводимо всі посилання зі сторінки, щоб зрозуміти, куди Hotline їх сховав!
            all_links = [a.get('href') for a in soup.find_all('a', href=True) if len(a.get('href')) > 5]
            links_snippet = ", ".join(all_links[:15]) # Перші 15 посилань
            raise HTTPException(
                status_code=400, 
                detail=f"Не знайдено оферів. <title>: '{page_title}'. Знайдені лінки на сторінці: {links_snippet}..."
            )
            
        return offers_data

    async def parse_comments(self, url: str, date_to: str | None = None) -> list:
        raise NotImplementedError("Hotline parser supports only offers")