import httpx
import re
from bs4 import BeautifulSoup
from fastapi import HTTPException
from datetime import datetime
from app.parsers.base import BaseParser
from app.models.response import CommentResponse

class BrainParser(BaseParser):
    async def parse_offers(self, url: str) -> list:
        raise NotImplementedError("Brain parser supports only comments")

    async def parse_comments(self, url: str, date_to: str | None = None) -> list[CommentResponse]:
        clean_url = url.strip().rstrip("/")
        comments_data = []

        limit_date = None
        if date_to:
            try:
                limit_date = datetime.strptime(date_to, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Невірний формат date_to. Використовуйте YYYY-MM-DD")

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"}

        try:
            response = await self.client.get(clean_url, headers=headers, follow_redirects=True)
            response.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Request error: {str(e)}")

        soup = BeautifulSoup(response.text, "lxml")
        review_blocks = soup.select(".review-item, .comment-item, .br-review")

        for block in review_blocks:
            try:
                # Парсимо дату
                date_elem = block.select_one(".date, .comment-date")
                date_str = date_elem.get_text(strip=True) if date_elem else ""
                
                review_date = datetime.utcnow()
                # Приклад регулярки для пошуку дати (DD.MM.YYYY)
                date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', date_str)
                if date_match:
                    day, month, year = date_match.groups()
                    review_date = datetime(int(year), int(month), int(day))

                # ЛОГІКА DATE_TO (Відсікаємо старі відгуки)
                if limit_date and review_date < limit_date:
                    break

                text_elem = block.select_one(".comment-text, .text")
                comment_text = text_elem.get_text(separator=" ", strip=True) if text_elem else None
                
                if not comment_text:
                    continue

                comments_data.append(CommentResponse(
                    rating=None, # Замість фейкових 5.0 ставимо None
                    advantages=None,
                    shortcomings=None,
                    comment=comment_text,
                    created_at=review_date
                ))
            except Exception:
                continue

        return comments_data