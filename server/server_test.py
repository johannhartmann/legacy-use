from fastapi.testclient import TestClient

from .server import app
from .settings import settings

client = TestClient(app)


def test_main_no_api_key():
    response = client.get('/')
    assert response.status_code == 401
    assert response.json() == {'detail': 'API key is missing'}


def test_main_wrong_api_key():
    response = client.get('/', headers={'X-API-Key': 'wrong_api_key'})
    assert response.status_code == 401
    assert response.json() == {'detail': 'Invalid API Key'}


def test_main():
    response = client.get('/', headers={'X-API-Key': settings.API_KEY})
    assert response.status_code == 200
