import httpx
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

        try:
            response = await self.client.get(
                clean_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"}
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            raise HTTPException(status_code=408, detail="Request Timeout: Brain")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"HTTP Error: {e.response.status_code}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Request error: {str(e)}")

        soup = BeautifulSoup(response.text, "lxml")
        
        review_blocks = soup.select(".review-item, .comment-item, .br-review")

        for block in review_blocks:
            try:
                text_elem = block.select_one(".comment-text, .text")
                comment_text = text_elem.get_text(strip=True) if text_elem else ""

                comments_data.append(CommentResponse(
                    rating=5.0,
                    advantages=None,
                    shortcomings=None,
                    comment=comment_text,
                    created_at=datetime.utcnow()
                ))
            except Exception:
                continue

        return comments_data