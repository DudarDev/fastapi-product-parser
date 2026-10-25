import pytest
import httpx
from bs4 import BeautifulSoup
from app.parsers.comfy import ComfyParser
from app.parsers.brain import BrainParser
from app.parsers.hotline import HotlineParser
from app.utils.url_cleaner import clean_url

def test_clean_url():
    raw_url = "https://hotline.ua/product-slug/?utm_source=google&ref=123#reviews"
    cleaned = clean_url(raw_url)
    assert "utm_source" not in cleaned
    assert "ref" not in cleaned
    assert "#reviews" not in cleaned

@pytest.mark.asyncio
async def test_comfy_json_ld_parsing():
    mock_html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Product",
          "name": "Смартфон Apple iPhone 15 128GB Black",
          "review": [
            {
              "@type": "Review",
              "reviewRating": { "@type": "Rating", "ratingValue": 5 },
              "reviewBody": "Чудовий телефон, тримає батарею повний день!",
              "datePublished": "2024-01-15"
            },
            {
              "@type": "Review",
              "reviewRating": { "@type": "Rating", "ratingValue": 4 },
              "reviewBody": "Камера супер, але ціна кусається.",
              "datePublished": "2024-02-01"
            }
          ]
        }
        </script>
      </head>
      <body><div>Content</div></body>
    </html>
    """
    
    # Mock HTTP response
    res = httpx.Response(200, text=mock_html, request=httpx.Request("GET", "https://comfy.ua/test.html"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: res)) as client:
        parser = ComfyParser(client=client)
        comments = await parser.parse_comments("https://comfy.ua/test.html")
        assert len(comments) == 2
        assert comments[0].rating == 5.0
        assert "Чудовий телефон" in comments[0].comment
        assert comments[1].rating == 4.0

@pytest.mark.asyncio
async def test_brain_parsing():
    mock_html = """
    <html>
      <body>
        <div class="review-item">
          <div class="comment-date">10.05.2024</div>
          <div class="comment-text">Швидка доставка, товар якісний!</div>
        </div>
        <div class="review-item">
          <div class="comment-date">01.05.2024</div>
          <div class="comment-text">Все працює без нарікань.</div>
        </div>
      </body>
    </html>
    """
    res = httpx.Response(200, text=mock_html, request=httpx.Request("GET", "https://brain.com.ua/test.html"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: res)) as client:
        parser = BrainParser(client=client)
        comments = await parser.parse_comments("https://brain.com.ua/test.html")
        assert len(comments) == 2
        assert "Швидка доставка" in comments[0].comment

@pytest.mark.asyncio
async def test_hotline_fallback_parsing():
    mock_html = """
    <html>
      <head><title>Apple iPhone 15 128GB - Ціни на Hotline</title></head>
      <body>
        <div class="list">
          <div class="product-item line row">
            <div class="shop-title"><img alt="Rozetka" src="/logo.png"/></div>
            <div class="price-box">32 499 грн</div>
            <a href="/go/price/12345/">Купити</a>
          </div>
          <div class="product-item line row">
            <div class="shop-title"><img alt="Moyo" src="/logo2.png"/></div>
            <div class="price-box">32 999 грн</div>
            <a href="/go/price/67890/">Купити</a>
          </div>
        </div>
      </body>
    </html>
    """
    res = httpx.Response(200, text=mock_html, request=httpx.Request("GET", "https://hotline.ua/test/"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: res)) as client:
        parser = HotlineParser(client=client)
        offers = await parser.parse_offers("https://hotline.ua/mobile-phones/apple-iphone-15-128gb/")
        assert len(offers) == 2
        assert offers[0].shop == "Rozetka"
        assert offers[0].price == 32499.0
        assert offers[1].shop == "Moyo"
        assert offers[1].price == 32999.0
