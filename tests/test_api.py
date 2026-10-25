import pytest
from starlette.testclient import TestClient
from app.main import app
from app.db.mongo import get_db

client = TestClient(app)

def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "Product Parser API"
    assert "/product/offers" in data["paths"]
    assert "/product/comments" in data["paths"]

def test_offers_validation_error():
    # URL not matching hotline.ua must return 422
    response = client.get("/product/offers", params={"url": "https://invalid-site.com/item"})
    assert response.status_code == 422
    assert "hotline.ua" in response.json()["detail"]

def test_comments_validation_error():
    # URL not matching comfy or brain must return 422
    response = client.get("/product/comments", params={"url": "https://rozetka.com.ua/item"})
    assert response.status_code == 422
    assert "comfy.ua" in response.json()["detail"] or "brain.com.ua" in response.json()["detail"]
