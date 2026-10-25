import httpx
import re
import json
from bs4 import BeautifulSoup
from fastapi import HTTPException
from datetime import datetime, timezone
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
        # ЕТАП 1: SEO JSON-LD СЦЕНАРІЙ (application/ld+json)
        # Оскільки Comfy - це SPA, відгуки для пошуковиків часто є в JSON-LD
        # =================================================================
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        for script in json_ld_scripts:
            if not script.string:
                continue
            try:
                ld_data = json.loads(script.string)
                items = ld_data if isinstance(ld_data, list) else [ld_data]
                for item in items:
                    reviews = item.get("review", [])
                    if isinstance(reviews, dict):
                        reviews = [reviews]
                    for rev in reviews:
                        review_body = rev.get("reviewBody") or rev.get("description")
                        if not review_body:
                            continue
                        
                        rating_val = None
                        if "reviewRating" in rev and isinstance(rev["reviewRating"], dict):
                            raw_rating = rev["reviewRating"].get("ratingValue")
                            if raw_rating is not None:
                                try:
                                    rating_val = float(raw_rating)
                                except (ValueError, TypeError):
                                    pass

                        rev_datetime = datetime.now(timezone.utc)
                        pub_date = rev.get("datePublished")
                        if pub_date:
                            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y"):
                                try:
                                    rev_datetime = datetime.strptime(str(pub_date).split("T")[0], "%Y-%m-%d")
                                    break
                                except ValueError:
                                    pass

                        if limit_date and rev_datetime < limit_date:
                            continue

                        comments_data.append(CommentResponse(
                            rating=rating_val,
                            advantages=None,
                            shortcomings=None,
                            comment=review_body.strip(),
                            created_at=rev_datetime
                        ))
            except Exception:
                continue

        # Якщо JSON-LD вже дав результати, повертаємо їх
        if comments_data:
            return comments_data

        # =================================================================
        # ЕТАП 2: FALLBACK СЦЕНАРІЙ (HTML парсинг)
        # =================================================================
        review_blocks = soup.select(".review-item, .feedback__item, .js-review-item, div[itemprop='review']")

        for block in review_blocks:
            try:
                # Читаємо дату відгуку
                date_elem = block.select_one(".date, .review-date, [itemprop='datePublished']")
                date_str = date_elem.get_text(strip=True) if date_elem else ""
                
                # Спроба розпарсити дату відгуку (формати бувають різні: "25 жовтня 2023", "25.10.2023")
                # Для прикладу реалізуємо парсинг формату DD.MM.YYYY
                review_date = datetime.now(timezone.utc) # За замовчуванням ставимо поточну
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