import pytest
from app.main import app

client = app.test_client()

def test_health_check():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {'status': 'ok'}