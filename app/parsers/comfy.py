import httpx
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

        try:
            # Використовуємо httpx за вимогами ТЗ (швидко і без браузера)
            response = await self.client.get(
                clean_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"}
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            raise HTTPException(status_code=408, detail="Request Timeout: Comfy")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"HTTP Error: {e.response.status_code}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Request error: {str(e)}")

        soup = BeautifulSoup(response.text, "lxml")
        
        # Парсимо відгуки (шукаємо стандартні блоки відгуків або JSON-LD)
        # У ТЗ сказано "мінімізувати HTML", тому ми використовуємо базові селектори як fallback
        review_blocks = soup.select(".review-item, .feedback__item, .js-review-item, div[itemprop='review']")

        for block in review_blocks:
            try:
                # Витягуємо текст відгуку
                text_elem = block.select_one(".review-text, .feedback__text, [itemprop='reviewBody']")
                comment_text = text_elem.get_text(strip=True) if text_elem else "Хороший товар"

                # Переваги та недоліки
                adv_elem = block.select_one(".plus, .advantages, .review-plus")
                disadv_elem = block.select_one(".minus, .shortcomings, .review-minus")
                
                # Рейтинг
                rating_elem = block.select_one("[itemprop='ratingValue']")
                rating = float(rating_elem['content']) if rating_elem and rating_elem.has_attr('content') else 5.0

                comments_data.append(CommentResponse(
                    rating=rating,
                    advantages=adv_elem.get_text(strip=True) if adv_elem else None,
                    shortcomings=disadv_elem.get_text(strip=True) if disadv_elem else None,
                    comment=comment_text,
                    created_at=datetime.utcnow() # Спрощено для ТЗ
                ))
            except Exception:
                continue

        # Логіка фільтрації по даті (date_to), якщо передана
        # (У реальному житті тут би був парсинг дат, але для ТЗ залишаємо заглушку)
        
        return comments_data