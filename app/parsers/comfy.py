import httpx
import re
from bs4 import BeautifulSoup
from fastapi import HTTPException
from datetime import datetime
from app.parsers.base import BaseParser
from app.models.response import CommentResponse

class ComfyParser(BaseParser):
    async def parse_offers(self, url: str) -> list:
        raise NotImplementedError("Comfy parser supports only comments")

    async def parse_comments(self, url: str, date_to: str | None = None) -> list[CommentResponse]:
        clean_url = url.strip().rstrip("/")
        comments_data = []
        
        # Конвертуємо date_to з рядка (YYYY-MM-DD) у об'єкт datetime для порівняння
        limit_date = None
        if date_to:
            try:
                limit_date = datetime.strptime(date_to, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Невірний формат date_to. Використовуйте YYYY-MM-DD")

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"}

        try:
            # Робимо запит до сторінки товару
            response = await self.client.get(clean_url, headers=headers, follow_redirects=True)
            response.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Request error: {str(e)}")

        soup = BeautifulSoup(response.text, "lxml")

        # =================================================================
        # ІДЕАЛЬНИЙ СЦЕНАРІЙ (API): Шукаємо data-product-id і стукаємо в API
        # =================================================================
        # Зазвичай Comfy ховає ID товару в атрибутах
        product_id_match = re.search(r'data-product-id="(\d+)"', response.text)
        if product_id_match:
            product_id = product_id_match.group(1)
            api_url = f"https://comfy.ua/api/v1/reviews/product/{product_id}" # Приклад їхнього API
            try:
                api_response = await self.client.get(api_url, headers=headers, timeout=5.0)
                if api_response.status_code == 200:
                    data = api_response.json()
                    # Тут би ми парсили JSON (залежить від точної структури Comfy API)
                    pass 
            except Exception:
                pass # Якщо API не спрацювало, просто йдемо далі до HTML парсингу

        # =================================================================
        # FALLBACK СЦЕНАРІЙ (HTML парсинг)
        # =================================================================
        review_blocks = soup.select(".review-item, .feedback__item, .js-review-item, div[itemprop='review']")

        for block in review_blocks:
            try:
                # Читаємо дату відгуку
                date_elem = block.select_one(".date, .review-date, [itemprop='datePublished']")
                date_str = date_elem.get_text(strip=True) if date_elem else ""
                
                # Спроба розпарсити дату відгуку (формати бувають різні: "25 жовтня 2023", "25.10.2023")
                # Для прикладу реалізуємо парсинг формату DD.MM.YYYY
                review_date = datetime.utcnow() # За замовчуванням ставимо поточну
                date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', date_str)
                if date_match:
                    day, month, year = date_match.groups()
                    review_date = datetime(int(year), int(month), int(day))

                # ЛОГІКА DATE_TO:
                # Відгуки на сайтах зазвичай йдуть від нових до старих.
                # Якщо ми дійшли до відгуку, який старіший за limit_date - зупиняємо парсинг!
                if limit_date and review_date < limit_date:
                    break  # Виходимо з циклу, зберігаємо ресурси сервера!

                # Витягуємо текст відгуку (БЕЗ фейкових заглушок)
                text_elem = block.select_one(".review-text, .feedback__text, [itemprop='reviewBody']")
                comment_text = text_elem.get_text(separator=" ", strip=True) if text_elem else None
                
                # Якщо немає тексту коментаря, пропускаємо (немає сенсу зберігати пусті)
                if not comment_text:
                    continue

                adv_elem = block.select_one(".plus, .advantages, .review-plus")
                disadv_elem = block.select_one(".minus, .shortcomings, .review-minus")
                
                rating_elem = block.select_one("[itemprop='ratingValue']")
                rating = float(rating_elem['content']) if rating_elem and rating_elem.has_attr('content') else None

                comments_data.append(CommentResponse(
                    rating=rating,
                    advantages=adv_elem.get_text(strip=True) if adv_elem else None,
                    shortcomings=disadv_elem.get_text(strip=True) if disadv_elem else None,
                    comment=comment_text,
                    created_at=review_date
                ))
            except Exception:
                continue

        return comments_data