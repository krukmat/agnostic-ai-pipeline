import pytest
from fastapi.testclient import TestClient
from project.backend-fastapi.app.main import app

client = TestClient(app)

def test_register_user():
    response = client.post('/auth/register', json={'username': 'testuser', 'password': 'testpass'})
    assert response.status_code == 201
    assert response.json()['message'] == 'User registered successfully'

def test_login_user():
    response = client.post('/auth/login', json={'username': 'testuser', 'password': 'testpass'})
    assert response.status_code == 200
    assert 'access_token' in response.json()