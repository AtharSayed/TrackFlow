# Tests for user routes
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_create_user(client):
    response = client.post('/api/users', json={"name": "John", "mobile": "1234567890"})
    assert response.status_code == 200
    assert "qrCodeUrl" in response.json