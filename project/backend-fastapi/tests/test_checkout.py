from fastapi.testclient import TestClient
import project.backend_fastapi.app.main as main

client = TestClient(main.app)

def test_health_check():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}

def test_checkout_success():
    response = client.post('/checkout', json={'items': [{'id': 1, 'quantity': 1}]})
    assert response.status_code == 200
    assert response.json()['message'] == 'Checkout successful'
